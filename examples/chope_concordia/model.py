"""OpenRouter model adapter with request-level benchmark telemetry."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
import copy
import dataclasses
import json
import threading
import time
from typing import Any

from concordia.language_model import language_model
import numpy as np
import openai

from examples.chope_concordia import config


@dataclasses.dataclass
class RequestContext:
  """Attribution attached to one logical API call."""

  phase: str
  run_id: str
  round: int | None = None
  agent: str | None = None
  scope: str | None = None


class TelemetryRecorder:
  """Thread-safe request recorder; no prompt or secret is persisted."""

  def __init__(self) -> None:
    self._records: list[dict[str, Any]] = []
    self._lock = threading.Lock()
    self._request_number = 0

  def next_request_number(self) -> int:
    with self._lock:
      self._request_number += 1
      return self._request_number

  def append(self, record: Mapping[str, Any]) -> None:
    with self._lock:
      self._records.append(copy.deepcopy(dict(record)))

  def records(self) -> list[dict[str, Any]]:
    with self._lock:
      return copy.deepcopy(self._records)


def _model_dump(value: Any) -> dict[str, Any]:
  if value is None:
    return {}
  if isinstance(value, dict):
    return dict(value)
  dumper = getattr(value, 'model_dump', None)
  if callable(dumper):
    dumped = dumper()
    return dict(dumped) if isinstance(dumped, dict) else {}
  return {}


def _nested(data: Mapping[str, Any], *path: str) -> Any:
  current: Any = data
  for key in path:
    if not isinstance(current, Mapping):
      return None
    current = current.get(key)
  return current


def _provider(
    response_data: Mapping[str, Any], headers: Mapping[str, str]
) -> str | None:
  provider = response_data.get('provider')
  if provider:
    return str(provider)
  for key in ('x-openrouter-provider', 'x-provider'):
    if headers.get(key):
      return str(headers[key])
  return None


def _usage_fields(response_data: Mapping[str, Any]) -> dict[str, Any]:
  usage = response_data.get('usage')
  usage = usage if isinstance(usage, Mapping) else {}
  reasoning = _nested(usage, 'completion_tokens_details', 'reasoning_tokens')
  if reasoning is None:
    reasoning = usage.get('reasoning_tokens')
  cost = usage.get('cost')
  return {
      'input_tokens': usage.get('prompt_tokens'),
      'output_tokens': usage.get('completion_tokens'),
      'reasoning_tokens': reasoning,
      'total_tokens': usage.get('total_tokens'),
      'cost_usd': cost,
      'exact_cost_available': cost is not None,
  }


def _error_status(error: Exception) -> int | None:
  status = getattr(error, 'status_code', None)
  return int(status) if isinstance(status, int) else None


def _retryable(error: Exception) -> bool:
  status = _error_status(error)
  if status is not None:
    return status in (408, 409, 429) or status >= 500
  return isinstance(
      error,
      (
          openai.APITimeoutError,
          openai.APIConnectionError,
          TimeoutError,
          ConnectionError,
      ),
  )


class OpenRouterGateway:
  """Makes Chat Completions and embeddings calls with explicit retries."""

  def __init__(
      self,
      *,
      api_key: str,
      recorder: TelemetryRecorder,
      base_url: str = config.OPENROUTER_BASE_URL,
      max_attempts: int = 3,
      timeout_seconds: float = 120.0,
  ) -> None:
    if not api_key:
      raise ValueError('An OpenRouter API key is required.')
    if max_attempts < 1:
      raise ValueError('max_attempts must be at least one.')
    self._recorder = recorder
    self._max_attempts = max_attempts
    self._client = openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
        max_retries=0,
        timeout=timeout_seconds,
        default_headers={
            'HTTP-Referer': 'https://github.com/google-deepmind/concordia',
            'X-Title': 'Concordia Chope benchmark',
        },
    )

  def chat(
      self,
      *,
      context: RequestContext,
      model: str,
      messages: Sequence[Mapping[str, str]],
      max_completion_tokens: int,
      temperature: float | None,
      response_format: Mapping[str, Any] | None = None,
  ) -> tuple[str, dict[str, Any]]:
    """Performs one logical chat call, recording every physical attempt."""
    request: dict[str, Any] = {
        'model': model,
        'messages': list(messages),
        'max_completion_tokens': max_completion_tokens,
    }
    if temperature is not None:
      request['temperature'] = temperature
    if response_format is not None:
      request['response_format'] = dict(response_format)

    for attempt in range(1, self._max_attempts + 1):
      request_number = self._recorder.next_request_number()
      started = time.perf_counter()
      try:
        raw = self._client.chat.completions.with_raw_response.create(**request)
        response = raw.parse()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        data = _model_dump(response)
        headers = {str(k).lower(): str(v) for k, v in raw.headers.items()}
        choice = response.choices[0]
        content = choice.message.content or ''
        finish_reason = getattr(choice, 'finish_reason', None)
        status = 'success' if finish_reason != 'length' else 'truncated'
        record = {
            'request_number': request_number,
            **dataclasses.asdict(context),
            'attempt': attempt,
            'model': model,
            'actual_provider': _provider(data, headers),
            'request_status': status,
            'error_type': (
                'completion_length' if finish_reason == 'length' else None
            ),
            'finish_reason': finish_reason,
            'latency_ms': elapsed_ms,
            **_usage_fields(data),
        }
        self._recorder.append(record)
        return content, record
      except Exception as error:  # API exception types vary by SDK release.
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        record = {
            'request_number': request_number,
            **dataclasses.asdict(context),
            'attempt': attempt,
            'model': model,
            'actual_provider': None,
            'request_status': 'failed',
            'error_type': type(error).__name__,
            'http_status': _error_status(error),
            'latency_ms': elapsed_ms,
            'input_tokens': None,
            'output_tokens': None,
            'reasoning_tokens': None,
            'total_tokens': None,
            'cost_usd': None,
            'exact_cost_available': False,
        }
        self._recorder.append(record)
        if attempt >= self._max_attempts or not _retryable(error):
          raise
        time.sleep(min(2 ** (attempt - 1), 4))
    raise AssertionError('unreachable')

  def embed(
      self,
      *,
      context: RequestContext,
      model: str,
      text: str,
  ) -> tuple[list[float], dict[str, Any]]:
    """Embeds one transcript and records every physical attempt."""
    for attempt in range(1, self._max_attempts + 1):
      request_number = self._recorder.next_request_number()
      started = time.perf_counter()
      try:
        raw = self._client.embeddings.with_raw_response.create(
            model=model, input=text or '[no public talk]'
        )
        response = raw.parse()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        data = _model_dump(response)
        headers = {str(k).lower(): str(v) for k, v in raw.headers.items()}
        vector = list(response.data[0].embedding)
        record = {
            'request_number': request_number,
            **dataclasses.asdict(context),
            'attempt': attempt,
            'model': model,
            'actual_provider': _provider(data, headers),
            'request_status': 'success',
            'error_type': None,
            'finish_reason': None,
            'latency_ms': elapsed_ms,
            **_usage_fields(data),
        }
        self._recorder.append(record)
        return vector, record
      except Exception as error:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        self._recorder.append({
            'request_number': request_number,
            **dataclasses.asdict(context),
            'attempt': attempt,
            'model': model,
            'actual_provider': None,
            'request_status': 'failed',
            'error_type': type(error).__name__,
            'http_status': _error_status(error),
            'latency_ms': elapsed_ms,
            'input_tokens': None,
            'output_tokens': None,
            'reasoning_tokens': None,
            'total_tokens': None,
            'cost_usd': None,
            'exact_cost_available': False,
        })
        if attempt >= self._max_attempts or not _retryable(error):
          raise
        time.sleep(min(2 ** (attempt - 1), 4))
    raise AssertionError('unreachable')


class ConcordiaOpenRouterModel(language_model.LanguageModel):
  """Concordia LanguageModel that fixes call attribution by turn order."""

  def __init__(
      self,
      *,
      gateway: OpenRouterGateway,
      run_id: str,
      model_name: str = config.GENERATION_MODEL,
  ) -> None:
    self._gateway = gateway
    self._run_id = run_id
    self._model_name = model_name
    self._logical_call = 0
    self._lock = threading.Lock()

  def _next_context(self) -> RequestContext:
    with self._lock:
      turn_index = self._logical_call
      self._logical_call += 1
    return RequestContext(
        phase='simulation',
        run_id=self._run_id,
        round=turn_index // len(config.AGENT_ORDER) + 1,
        agent=config.AGENT_ORDER[turn_index % len(config.AGENT_ORDER)],
    )

  def sample_text(
      self,
      prompt: str,
      *,
      max_tokens: int = language_model.DEFAULT_MAX_TOKENS,
      terminators: Collection[str] = language_model.DEFAULT_TERMINATORS,
      temperature: float = language_model.DEFAULT_TEMPERATURE,
      top_p: float = language_model.DEFAULT_TOP_P,
      top_k: int = language_model.DEFAULT_TOP_K,
      timeout: float = language_model.DEFAULT_TIMEOUT_SECONDS,
      seed: int | None = None,
  ) -> str:
    del terminators, temperature, top_p, top_k, timeout, seed
    content, _ = self._gateway.chat(
        context=self._next_context(),
        model=self._model_name,
        messages=(
            {
                'role': 'system',
                'content': (
                    'Follow the simulation context exactly. Return only the '
                    'requested JSON action and never reveal chain-of-thought.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ),
        max_completion_tokens=min(
            max_tokens, config.AGENT_MAX_COMPLETION_TOKENS
        ),
        # The benchmark requires provider default generation temperature.
        temperature=None,
    )
    return content

  def sample_choice(
      self,
      prompt: str,
      responses: Sequence[str],
      *,
      seed: int | None = None,
  ) -> tuple[int, str, Mapping[str, Any]]:
    del seed
    answer = self.sample_text(
        prompt
        + '\nReturn exactly one of these options:\n'
        + '\n'.join(responses),
        max_tokens=64,
    ).strip()
    try:
      index = list(responses).index(answer)
    except ValueError as error:
      raise language_model.InvalidResponseError(answer) from error
    return index, responses[index], {}


def evaluate_run(
    *,
    gateway: OpenRouterGateway,
    run_id: str,
    events: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
  """Makes the one allowed final evaluator call for a completed run."""
  content, record = gateway.chat(
      context=RequestContext(phase='evaluation', run_id=run_id),
      model=config.EVALUATOR_MODEL,
      messages=(
          {'role': 'system', 'content': config.EVALUATOR_SYSTEM_PROMPT},
          {'role': 'user', 'content': config.evaluator_user_prompt(events)},
      ),
      max_completion_tokens=config.EVALUATOR_MAX_COMPLETION_TOKENS,
      temperature=config.EVALUATOR_TEMPERATURE,
      response_format={
          'type': 'json_schema',
          'json_schema': config.EVALUATOR_SCHEMA,
      },
  )
  try:
    return json.loads(content), record
  except json.JSONDecodeError as error:
    raise ValueError('Evaluator returned invalid JSON.') from error


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
  """Returns cosine similarity, treating an empty vector as zero."""
  left_array = np.asarray(left, dtype=np.float64)
  right_array = np.asarray(right, dtype=np.float64)
  denominator = float(np.linalg.norm(left_array) * np.linalg.norm(right_array))
  if not denominator:
    return 0.0
  return float(np.dot(left_array, right_array) / denominator)
