"""Deterministic Chope transcript, boundary, and cohort metrics."""

from __future__ import annotations

from collections import Counter
from collections import defaultdict
from collections.abc import Mapping, Sequence
import difflib
import math
import re
import statistics
from typing import Any

import numpy as np

from examples.chope_concordia import config
from examples.chope_concordia import model as model_lib

_ESCAPED_UNICODE = re.compile(r'u[0-9a-fA-F]{4,6}')
_NON_LEXICAL = re.compile(r"[^a-z0-9']+")
_APOLOGY = re.compile(r'\b(sorry|apolog(?:y|ise|ize)|paiseh)\b', re.I)
_NORM = re.compile(
    r'\b(chope|reserve[ds]?|reservation|tissue(?: packet)?|save[ds]? '
    r'(?:a |the |this )?(?:seat|table))\b',
    re.I,
)
_DISAGREEMENT = re.compile(
    r"\b(no|but|however|disagree|not fair|cannot|can't|don't agree|my seat|"
    r'i was here|you moved)\b',
    re.I,
)
_MITIGATION = re.compile(
    r'\b(please|perhaps|maybe|could we|can we|no offence|understand|'
    r'no hard feelings|let us|let\'s|how about)\b',
    re.I,
)
_CODE_SWITCH = re.compile(
    r'\b(lah|leh|lor|paiseh|aiyo|alamak|can or not|already|this one)\b',
    re.I,
)


def normalize_text(text: str) -> str:
  """Applies the predeclared lexical normalization."""
  normalized = _ESCAPED_UNICODE.sub(' ', text.lower())
  normalized = _NON_LEXICAL.sub(' ', normalized)
  return ' '.join(normalized.split())


def sequence_similarity(left: str, right: str) -> float:
  return difflib.SequenceMatcher(
      None, normalize_text(left), normalize_text(right)
  ).ratio()


def _public_talk(
    events: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
  return [event for event in events if event.get('type') == 'TALK']


def transcript_text(
    events: Sequence[Mapping[str, Any]], *, round_number: int | None = None
) -> str:
  """Returns public TALK text only, as used for benchmark embeddings."""
  lines = []
  for event in events:
    if event.get('type') != 'TALK':
      continue
    if round_number is not None and event.get('round') != round_number:
      continue
    lines.append(f'{event["agent"]}: {event["content"]}')
  return '\n'.join(lines)


def observable_metrics(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
  """Computes counts that do not depend on an LLM judge."""
  public = [event for event in events if event.get('type') != 'SILENCE']
  talks = _public_talk(events)
  by_type = Counter(str(event['type']) for event in events)
  by_agent: dict[str, list[str]] = defaultdict(list)
  for event in talks:
    by_agent[str(event['agent'])].append(str(event['content']))

  exact_pairs = 0
  near_pairs = 0
  maximum_similarity = 0.0
  for utterances in by_agent.values():
    for left_index, left in enumerate(utterances):
      for right in utterances[left_index + 1 :]:
        similarity = sequence_similarity(left, right)
        maximum_similarity = max(maximum_similarity, similarity)
        if normalize_text(left) == normalize_text(right):
          exact_pairs += 1
        if similarity >= 0.85:
          near_pairs += 1

  marker_counts = {
      marker: sum(
          len(
              re.findall(
                  rf'\b{re.escape(marker)}\b', str(event['content']), re.I
              )
          )
          for event in talks
      )
      for marker in ('lah', 'leh', 'lor', 'paiseh', 'already', 'this one')
  }
  marker_counts['can or not'] = sum(
      len(re.findall(r'\bcan or not\b', str(event['content']), re.I))
      for event in talks
  )
  return {
      'public_action_count': len(public),
      'action_type_counts': dict(by_type),
      'speaking_agents': len({event['agent'] for event in talks}),
      'singlish_markers': marker_counts,
      'apology_count': sum(
          bool(_APOLOGY.search(str(e['content']))) for e in talks
      ),
      'norm_reference_count': sum(
          bool(_NORM.search(str(e['content']))) for e in talks
      ),
      'direct_disagreement_count': sum(
          bool(_DISAGREEMENT.search(str(e['content']))) for e in talks
      ),
      'mitigation_count': sum(
          bool(_MITIGATION.search(str(e['content']))) for e in talks
      ),
      'code_switch_count': sum(
          bool(_CODE_SWITCH.search(str(e['content']))) for e in talks
      ),
      'exact_repeated_same_agent_pairs': exact_pairs,
      'near_repeated_same_agent_pairs': near_pairs,
      'maximum_same_agent_similarity': maximum_similarity,
      'parse_error_count': sum(bool(e.get('parse_error')) for e in events),
      'completed_rounds': max((int(e['round']) for e in events), default=0),
      'agent_turn_slots': len(events),
  }


def _has(text: str, patterns: Sequence[str]) -> bool:
  return any(re.search(pattern, text, re.I) for pattern in patterns)


def detect_practical_resolution(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
  """Conservative deterministic resolution detector with exact evidence."""
  talks = [event for event in events if event.get('type') == 'TALK']
  mr_lim_requested = False
  share_offer: tuple[str, int] | None = None
  rearrange_offer: tuple[str, int] | None = None
  mr_lim_took_seat: Mapping[str, Any] | None = None

  for event in events:
    agent = str(event['agent'])
    text = normalize_text(str(event['content']))
    turn = int(event['turn'])
    if agent == 'Mr Lim' and event.get('type') == 'TALK':
      if _has(
          text,
          (
              r'\bmy (?:seat|table)\b',
              r'\bi (?:chope|reserved|saved)\b',
              r'\bgive (?:me )?(?:my|the) seat back\b',
              r'\bi (?:need|want) (?:my|the) seat\b',
              r'\bthat tissue .{0,20}(?:reserve|chope|seat|table)\b',
          ),
      ):
        mr_lim_requested = True

    # A conditional offer alone is deliberately excluded.
    conditional = bool(re.match(r'^(?:well )?if\b', text))
    if (
        agent == 'Rachel Pereira'
        and mr_lim_requested
        and not conditional
        and event.get('type') in ('TALK', 'ACTION')
        and _has(
            text,
            (
                r"\bi(?:'ll| will| can| am going to) (?:move|stand|leave|"
                r'give (?:you )?(?:the|your) seat|take another seat)',
                r'\bplease (?:take|have) (?:the|your) seat\b',
                r'\byou can (?:take|have) (?:the|your) seat\b',
                r'\bthe seat is yours\b',
                r'\bgets? up\b',
            ),
        )
    ):
      return {
          'achieved': True,
          'kind': 'rachel_returns_seat',
          'turn': turn,
          'round': int(event['round']),
          'outcome': 'compromise',
          'evidence': str(event['content']),
          'agent': agent,
      }

    if (
        agent == 'Mr Lim'
        and not conditional
        and event.get('type') in ('TALK', 'ACTION')
        and _has(
            text,
            (
                r"\bi(?:'ll| will| can) (?:find|look for|take) another seat\b",
                r'\bi will sit elsewhere\b',
            ),
        )
    ):
      return {
          'achieved': True,
          'kind': 'mr_lim_finds_another_seat',
          'turn': turn,
          'round': int(event['round']),
          'outcome': 'avoidance',
          'evidence': str(event['content']),
          'agent': agent,
      }

    if (
        agent == 'Mr Lim'
        and event.get('type') == 'ACTION'
        and _has(text, (r'\b(?:sits|sit|takes|take) (?:down|the seat)\b',))
    ):
      mr_lim_took_seat = event
    if (
        agent == 'Rachel Pereira'
        and mr_lim_took_seat is not None
        and event.get('type') == 'TALK'
        and _has(
            text,
            (
                r'\b(?:okay|ok|fine|agreed|no problem|that works)\b',
                r'\b(?:take|have) (?:the|your) seat\b',
            ),
        )
    ):
      return {
          'achieved': True,
          'kind': 'mr_lim_takes_rachel_accepts',
          'turn': turn,
          'round': int(event['round']),
          'outcome': 'compromise',
          'evidence': f'{mr_lim_took_seat["content"]} / {event["content"]}',
          'agent': agent,
      }

    if event.get('type') == 'TALK' and _has(
        text,
        (
            r'\bshare (?:the )?(?:seat|table)\b',
            r'\bsit together\b',
        ),
    ):
      if share_offer is None:
        share_offer = (agent, turn)
      elif agent in ('Mr Lim', 'Rachel Pereira') and agent != share_offer[0]:
        if _has(text, (r'\b(?:agree|okay|ok|yes|can|works|share)\b',)):
          return {
              'achieved': True,
              'kind': 'mutual_share',
              'turn': turn,
              'round': int(event['round']),
              'outcome': 'compromise',
              'evidence': str(event['content']),
              'agent': agent,
          }

    if event.get('type') == 'TALK' and _has(
        text,
        (
            r'\brearrang(?:e|ing) (?:the )?(?:chair|chairs|seats)\b',
            r'\bmake (?:some )?space\b',
            r'\bmove (?:a |the )?chair\b',
        ),
    ):
      if rearrange_offer is None:
        rearrange_offer = (agent, turn)
      elif (
          agent in ('Mr Lim', 'Rachel Pereira') and agent != rearrange_offer[0]
      ):
        if _has(text, (r'\b(?:agree|okay|ok|yes|can|works|do that)\b',)):
          return {
              'achieved': True,
              'kind': 'mutual_rearrangement',
              'turn': turn,
              'round': int(event['round']),
              'outcome': 'compromise',
              'evidence': str(event['content']),
              'agent': agent,
          }

  del talks
  return {
      'achieved': False,
      'kind': None,
      'turn': None,
      'round': None,
      'outcome': 'unresolved',
      'evidence': None,
      'agent': None,
  }


def calculate_round_metrics(
    *,
    events: Sequence[Mapping[str, Any]],
    round_embeddings: Mapping[int, Sequence[float]],
    rounds: int = config.ROUNDS,
) -> list[dict[str, Any]]:
  """Computes adjacent lexical/semantic repetition and relevance."""
  per_round_agent: dict[int, dict[str, str]] = {}
  for round_number in range(1, rounds + 1):
    per_agent: dict[str, list[str]] = defaultdict(list)
    for event in events:
      if event.get('round') == round_number and event.get('type') == 'TALK':
        per_agent[str(event['agent'])].append(str(event['content']))
    per_round_agent[round_number] = {
        agent: ' '.join(per_agent.get(agent, ()))
        for agent in config.AGENT_ORDER
    }

  rows = []
  for round_number in range(1, rounds + 1):
    lexical_values: dict[str, float] = {}
    if round_number > 1:
      for agent in config.AGENT_ORDER:
        previous = per_round_agent[round_number - 1][agent]
        current = per_round_agent[round_number][agent]
        if previous and current:
          lexical_values[agent] = sequence_similarity(previous, current)
    mean_lexical = (
        statistics.fmean(lexical_values.values()) if lexical_values else None
    )
    high_fraction = (
        sum(
            value >= config.LEXICAL_AGENT_THRESHOLD
            for value in lexical_values.values()
        )
        / len(lexical_values)
        if lexical_values
        else None
    )
    adjacent = None
    if round_number > 1:
      adjacent = model_lib.cosine_similarity(
          round_embeddings[round_number - 1], round_embeddings[round_number]
      )
    relevance = model_lib.cosine_similarity(
        round_embeddings[1], round_embeddings[round_number]
    )
    lexical_candidate = bool(
        mean_lexical is not None
        and high_fraction is not None
        and mean_lexical >= config.LEXICAL_MEAN_THRESHOLD
        and high_fraction >= config.LEXICAL_AGENT_FRACTION
    )
    semantic_candidate = bool(
        adjacent is not None
        and mean_lexical is not None
        and adjacent >= config.SEMANTIC_ADJACENT_THRESHOLD
        and mean_lexical >= config.SEMANTIC_LEXICAL_FLOOR
    )
    rows.append({
        'round': round_number,
        'mean_same_agent_similarity': mean_lexical,
        'fraction_agents_similarity_ge_0_80': high_fraction,
        'adjacent_embedding_similarity': adjacent,
        'novelty': 1.0 if adjacent is None else 1.0 - adjacent,
        'relevance_to_round_1': relevance,
        'lexical_repetition_candidate': lexical_candidate,
        'semantic_repetition_candidate': semantic_candidate,
        'repeated_round_candidate': lexical_candidate or semantic_candidate,
        'drift_candidate': relevance < config.DRIFT_RELEVANCE_THRESHOLD,
        **{
            f'{agent}_lexical_similarity': lexical_values.get(agent)
            for agent in config.AGENT_ORDER
        },
    })
  return rows


def _first_two_consecutive(
    rows: Sequence[Mapping[str, Any]],
    key: str,
    *,
    strictly_after_round: int | None = None,
) -> int | None:
  for left, right in zip(rows, rows[1:]):
    left_round = int(left['round'])
    if strictly_after_round is not None and left_round <= strictly_after_round:
      continue
    if (
        strictly_after_round is not None
        and int(right['round']) <= strictly_after_round
    ):
      continue
    if bool(left[key]) and bool(right[key]):
      return left_round
  return None


def boundary_metrics(
    *,
    events: Sequence[Mapping[str, Any]],
    round_rows: Sequence[Mapping[str, Any]],
    resolution: Mapping[str, Any],
) -> dict[str, Any]:
  """Separates repetition, drift, and post-resolution convergence."""
  repetition = _first_two_consecutive(round_rows, 'repeated_round_candidate')
  resolution_round = resolution.get('round')
  drift = None
  convergence = None
  if isinstance(resolution_round, int):
    drift = _first_two_consecutive(
        round_rows,
        'drift_candidate',
        strictly_after_round=resolution_round,
    )
    convergence = _first_two_consecutive(
        round_rows,
        'repeated_round_candidate',
        strictly_after_round=resolution_round,
    )
  present = [value for value in (drift, convergence) if value is not None]
  first_boundary = min(present) if present else None
  resolution_turn = resolution.get('turn')
  post_resolution_talk = 0
  if isinstance(resolution_turn, int):
    post_resolution_talk = sum(
        event.get('type') == 'TALK' and int(event['turn']) > resolution_turn
        for event in events
    )
  return {
      'repetition_onset_round': repetition,
      'topic_drift_onset_round': drift,
      'convergence_round': convergence,
      # Retain the technical compatibility name without using it in charts.
      'saturation_round': convergence,
      'first_boundary_round': first_boundary,
      'post_resolution_public_talk_count': post_resolution_talk,
      'forced_continuation_rounds': (
          config.ROUNDS - int(resolution_round)
          if isinstance(resolution_round, int)
          else 0
      ),
  }


def summarize_run(
    *,
    run_id: str,
    events: list[dict[str, Any]],
    evaluator: Mapping[str, Any] | None,
    round_embeddings: Mapping[int, Sequence[float]],
    full_embedding: Sequence[float],
    request_records: Sequence[Mapping[str, Any]],
    wall_time_ms: float,
) -> dict[str, Any]:
  """Builds one JSON-serializable run record."""
  resolution = detect_practical_resolution(events)
  observable = observable_metrics(events)
  round_rows = calculate_round_metrics(
      events=events, round_embeddings=round_embeddings
  )
  boundary = boundary_metrics(
      events=events, round_rows=round_rows, resolution=resolution
  )
  evaluator_resolution = (
      bool(evaluator.get('resolution_achieved')) if evaluator else None
  )
  resource = aggregate_resources(request_records)
  return {
      'run_id': run_id,
      'status': 'completed',
      'wall_time_ms': wall_time_ms,
      'events': events,
      'observable': observable,
      'deterministic_resolution': resolution,
      'evaluator': dict(evaluator) if evaluator else None,
      'resolution_source_disagreement': (
          evaluator_resolution is not None
          and bool(resolution['achieved']) != evaluator_resolution
      ),
      'round_metrics': round_rows,
      'boundary': boundary,
      'resources': resource,
      'request_records': [dict(record) for record in request_records],
      'round_embeddings': {
          str(key): list(value) for key, value in round_embeddings.items()
      },
      'full_embedding': list(full_embedding),
  }


def _sum_known(values: Sequence[Any]) -> int | float | None:
  known = [value for value in values if isinstance(value, (int, float))]
  return sum(known) if known else None


def aggregate_resources(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
  """Aggregates telemetry without turning unknown cost into exact zero."""
  result: dict[str, Any] = {}
  for phase in ('simulation', 'evaluation', 'embedding', 'total'):
    selected = (
        list(records)
        if phase == 'total'
        else [record for record in records if record.get('phase') == phase]
    )
    result[phase] = {
        'requests': len(selected),
        'failed_calls': sum(
            record.get('request_status') == 'failed' for record in selected
        ),
        'truncated_calls': sum(
            record.get('request_status') == 'truncated' for record in selected
        ),
        'input_tokens': _sum_known([r.get('input_tokens') for r in selected]),
        'output_tokens': _sum_known([r.get('output_tokens') for r in selected]),
        'reasoning_tokens': _sum_known(
            [r.get('reasoning_tokens') for r in selected]
        ),
        'total_tokens': _sum_known([r.get('total_tokens') for r in selected]),
        'cost_usd': _sum_known([r.get('cost_usd') for r in selected]),
        'exact_cost_complete': (
            bool(selected)
            and all(bool(r.get('exact_cost_available')) for r in selected)
        ),
        'latency_ms': _sum_known([r.get('latency_ms') for r in selected]),
        'providers': dict(
            Counter(
                str(r['actual_provider'])
                for r in selected
                if r.get('actual_provider')
            )
        ),
        'error_types': dict(
            Counter(
                str(r['error_type']) for r in selected if r.get('error_type')
            )
        ),
    }
  return result


def _rate(runs: Sequence[Mapping[str, Any]], getter: Any) -> float:
  return (
      statistics.fmean(float(bool(getter(run))) for run in runs)
      if runs
      else 0.0
  )


def _median_present(values: Sequence[Any]) -> float | None:
  present = [
      float(value) for value in values if isinstance(value, (int, float))
  ]
  return statistics.median(present) if present else None


def cohort_summary(runs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
  """Aggregates completed runs while retaining counts beside percentages."""
  completed = [run for run in runs if run.get('status') == 'completed']
  count = len(completed)

  def count_rate(predicate: Any) -> dict[str, Any]:
    numerator = sum(bool(predicate(run)) for run in completed)
    return {
        'count': numerator,
        'total': count,
        'rate': numerator / count if count else None,
    }

  evaluator_runs = [run for run in completed if run.get('evaluator')]
  deterministic_outcomes = Counter(
      run['deterministic_resolution']['outcome'] for run in completed
  )
  evaluator_outcomes = Counter(
      run['evaluator']['outcome'] for run in evaluator_runs
  )
  adherence_values = [
      score
      for run in evaluator_runs
      for score in run['evaluator']['persona_adherence'].values()
  ]
  all_records = [
      record for run in completed for record in run.get('request_records', ())
  ]
  failed_run_ids = {
      record.get('run_id')
      for record in all_records
      if record.get('request_status') == 'failed'
  }
  return {
      'completed_runs': count,
      'deterministic_resolution': count_rate(
          lambda run: run['deterministic_resolution']['achieved']
      ),
      'evaluator_resolution': count_rate(
          lambda run: bool(run.get('evaluator', {}).get('resolution_achieved'))
      ),
      'deterministic_outcomes': dict(deterministic_outcomes),
      'evaluator_outcomes': dict(evaluator_outcomes),
      'conflict': count_rate(
          lambda run: bool(run.get('evaluator', {}).get('conflict_emerged'))
      ),
      'norm_recognition': count_rate(
          lambda run: bool(run.get('evaluator', {}).get('norm_recognized'))
      ),
      'rachel_norm_acknowledgment': count_rate(
          lambda run: bool(
              run.get('evaluator', {}).get('rachel_acknowledged_norm')
          )
      ),
      'mediation': count_rate(
          lambda run: bool(run.get('evaluator', {}).get('mediator_emerged'))
      ),
      'immediate_capitulation': count_rate(
          lambda run: bool(
              run.get('evaluator', {}).get('immediate_capitulation')
          )
      ),
      'premature_yield': count_rate(
          lambda run: bool(run.get('evaluator', {}).get('premature_yield'))
      ),
      'age_deference': count_rate(
          lambda run: bool(run.get('evaluator', {}).get('age_deference'))
      ),
      'mean_persona_adherence': (
          statistics.fmean(adherence_values) if adherence_values else None
      ),
      'mean_perspective_diversity': (
          statistics.fmean(
              float(run['evaluator']['perspective_diversity'])
              for run in evaluator_runs
          )
          if evaluator_runs
          else None
      ),
      'repetition': count_rate(
          lambda run: run['boundary']['repetition_onset_round'] is not None
      ),
      'median_repetition_onset': _median_present(
          [run['boundary']['repetition_onset_round'] for run in completed]
      ),
      'topic_drift': count_rate(
          lambda run: run['boundary']['topic_drift_onset_round'] is not None
      ),
      'median_topic_drift_onset': _median_present(
          [run['boundary']['topic_drift_onset_round'] for run in completed]
      ),
      'convergence_after_resolution': count_rate(
          lambda run: run['boundary']['convergence_round'] is not None
      ),
      'median_convergence_round': _median_present(
          [run['boundary']['convergence_round'] for run in completed]
      ),
      'first_boundary': count_rate(
          lambda run: run['boundary']['first_boundary_round'] is not None
      ),
      'median_first_boundary_round': _median_present(
          [run['boundary']['first_boundary_round'] for run in completed]
      ),
      'resolution_source_disagreements': sum(
          bool(run.get('resolution_source_disagreement')) for run in completed
      ),
      'resources': aggregate_resources(all_records),
      'failed_calls': sum(
          record.get('request_status') == 'failed' for record in all_records
      ),
      'runs_containing_failed_call': len(failed_run_ids),
      'mean_wall_time_ms': (
          statistics.fmean(float(run['wall_time_ms']) for run in completed)
          if completed
          else None
      ),
  }


def add_boundary_resource_totals(
    summary: dict[str, Any], runs: Sequence[Mapping[str, Any]]
) -> None:
  """Adds conservative post-boundary/convergence simulation totals in place."""
  total_tokens = 0
  total_cost = 0.0
  cost_complete = True
  post_boundary_tokens = 0
  post_boundary_cost = 0.0
  post_convergence_tokens = 0
  post_convergence_cost = 0.0
  for run in runs:
    for record in run.get('request_records', ()):
      if record.get('phase') != 'simulation':
        continue
      tokens = record.get('total_tokens')
      cost = record.get('cost_usd')
      if isinstance(tokens, (int, float)):
        total_tokens += int(tokens)
      if isinstance(cost, (int, float)):
        total_cost += float(cost)
      else:
        cost_complete = False
      round_number = record.get('round')
      first_boundary = run['boundary']['first_boundary_round']
      convergence = run['boundary']['convergence_round']
      if isinstance(round_number, int) and isinstance(first_boundary, int):
        if round_number > first_boundary:
          if isinstance(tokens, (int, float)):
            post_boundary_tokens += int(tokens)
          if isinstance(cost, (int, float)):
            post_boundary_cost += float(cost)
      if isinstance(round_number, int) and isinstance(convergence, int):
        if round_number > convergence:
          if isinstance(tokens, (int, float)):
            post_convergence_tokens += int(tokens)
          if isinstance(cost, (int, float)):
            post_convergence_cost += float(cost)
  summary['boundary_resources'] = {
      'simulation_tokens': total_tokens,
      'simulation_cost_usd': total_cost if cost_complete else None,
      'post_first_boundary_tokens': post_boundary_tokens,
      'post_first_boundary_token_share': (
          post_boundary_tokens / total_tokens if total_tokens else None
      ),
      'post_first_boundary_cost_usd': (
          post_boundary_cost if cost_complete else None
      ),
      'post_first_boundary_cost_share': (
          post_boundary_cost / total_cost
          if cost_complete and total_cost
          else None
      ),
      'post_convergence_tokens': post_convergence_tokens,
      'post_convergence_token_share': (
          post_convergence_tokens / total_tokens if total_tokens else None
      ),
      'post_convergence_cost_usd': (
          post_convergence_cost if cost_complete else None
      ),
      'post_convergence_cost_share': (
          post_convergence_cost / total_cost
          if cost_complete and total_cost
          else None
      ),
      'exact_cost_complete': cost_complete,
  }


def _outcome_tvd(
    left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]]
) -> float:
  labels = ('consensus', 'compromise', 'avoidance', 'escalation', 'unresolved')
  left_counts = Counter(
      run['deterministic_resolution']['outcome'] for run in left
  )
  right_counts = Counter(
      run['deterministic_resolution']['outcome'] for run in right
  )
  return 0.5 * sum(
      abs(left_counts[label] / len(left) - right_counts[label] / len(right))
      for label in labels
  )


def _standardized_mean_difference(
    left: Sequence[float], right: Sequence[float]
) -> float:
  left_mean = statistics.fmean(left)
  right_mean = statistics.fmean(right)
  left_var = statistics.variance(left) if len(left) > 1 else 0.0
  right_var = statistics.variance(right) if len(right) > 1 else 0.0
  pooled = math.sqrt((left_var + right_var) / 2.0)
  if pooled == 0:
    return 0.0 if left_mean == right_mean else math.inf
  return abs(left_mean - right_mean) / pooled


def cohort_convergence_rows(
    runs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
  """Applies the separate cumulative n versus n-5 stability protocol."""
  completed = sorted(
      (run for run in runs if run.get('status') == 'completed'),
      key=lambda run: str(run['run_id']),
  )
  rows: list[dict[str, Any]] = []
  binary_getters = (
      lambda run: run.get('evaluator', {}).get('conflict_emerged', False),
      lambda run: run['deterministic_resolution']['achieved'],
      lambda run: run.get('evaluator', {}).get('norm_recognized', False),
      lambda run: run.get('evaluator', {}).get(
          'rachel_acknowledged_norm', False
      ),
      lambda run: run.get('evaluator', {}).get('mediator_emerged', False),
      lambda run: run.get('evaluator', {}).get('immediate_capitulation', False),
      lambda run: run.get('evaluator', {}).get('premature_yield', False),
      lambda run: run.get('evaluator', {}).get('age_deference', False),
  )

  for n in range(10, len(completed) + 1, 5):
    current = completed[:n]
    row: dict[str, Any] = {'checkpoint_n': n}
    if n == 10:
      row.update({
          'outcome_tvd': None,
          'largest_binary_rate_change': None,
          'largest_continuous_smd': None,
          'centroid_cosine_distance': None,
          'criteria_pass': False,
          'declared_converged': False,
      })
      rows.append(row)
      continue
    previous = completed[: n - 5]
    tvd = _outcome_tvd(current, previous)
    binary_change = max(
        abs(_rate(current, getter) - _rate(previous, getter))
        for getter in binary_getters
    )

    def continuous(
        group: Sequence[Mapping[str, Any]],
    ) -> tuple[list[float], ...]:
      resolution_turn = [
          float(run['deterministic_resolution']['turn'] or 33) for run in group
      ]
      adherence = [
          statistics.fmean(run['evaluator']['persona_adherence'].values())
          if run.get('evaluator')
          else 5.0
          for run in group
      ]
      diversity = [
          float(run['evaluator']['perspective_diversity'])
          if run.get('evaluator')
          else 1.0
          for run in group
      ]
      return resolution_turn, adherence, diversity

    current_continuous = continuous(current)
    previous_continuous = continuous(previous)
    largest_smd = max(
        _standardized_mean_difference(left, right)
        for left, right in zip(current_continuous, previous_continuous)
    )
    current_centroid = np.mean(
        np.asarray([run['full_embedding'] for run in current]), axis=0
    )
    previous_centroid = np.mean(
        np.asarray([run['full_embedding'] for run in previous]), axis=0
    )
    centroid_distance = 1.0 - model_lib.cosine_similarity(
        current_centroid, previous_centroid
    )
    passed = (
        tvd <= 0.10
        and binary_change <= 0.10
        and largest_smd <= 0.20
        and centroid_distance <= 0.05
    )
    previous_passed = bool(rows[-1].get('criteria_pass'))
    row.update({
        'outcome_tvd': tvd,
        'largest_binary_rate_change': binary_change,
        'largest_continuous_smd': largest_smd,
        'centroid_cosine_distance': centroid_distance,
        'criteria_pass': passed,
        'declared_converged': n >= 20 and passed and previous_passed,
    })
    rows.append(row)
  return rows
