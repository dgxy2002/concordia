"""Command-line runner for the Concordia Chope benchmark."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any

from examples.chope_concordia import artifacts
from examples.chope_concordia import config
from examples.chope_concordia import metrics
from examples.chope_concordia import model as model_lib
from examples.chope_concordia import simulation


def _configure_utf8_stdio() -> None:
  for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, 'reconfigure', None)
    if callable(reconfigure):
      reconfigure(encoding='utf-8', errors='backslashreplace')


def _load_dotenv(path: Path) -> None:
  """Loads simple environment entries without printing or returning secrets."""
  if not path.exists():
    return
  for raw_line in path.read_text(encoding='utf-8').splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#') or '=' not in line:
      continue
    key, value = line.split('=', 1)
    key = key.strip()
    if key and key not in os.environ:
      os.environ[key] = value.strip().strip('"').strip("'")


def _git_commit() -> str:
  try:
    return subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
  except (OSError, subprocess.CalledProcessError):
    return 'unknown'


def _parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
      description='Run the Chope cross-framework benchmark in Concordia.'
  )
  parser.add_argument(
      '--mode',
      choices=('boundary', 'adaptive'),
      default='boundary',
      help=(
          'boundary runs the fixed 15-run cohort; adaptive separately checks '
          'across-run convergence from n=10 to n=30.'
      ),
  )
  parser.add_argument(
      '--runs',
      type=int,
      default=15,
      help='Boundary-mode run count. Use 15 for the like-for-like cohort.',
  )
  parser.add_argument(
      '--experiment-id',
      default=None,
      help='Output identifier; defaults to a dated Concordia identifier.',
  )
  parser.add_argument(
      '--output-root',
      type=Path,
      default=Path('data/chope_experiments'),
  )
  parser.add_argument(
      '--api-key-env',
      default='OPENROUTER_API_KEY',
      help='Environment variable containing the key; the value is never saved.',
  )
  parser.add_argument(
      '--base-url',
      default=config.OPENROUTER_BASE_URL,
      help='OpenAI-compatible OpenRouter endpoint.',
  )
  parser.add_argument('--max-api-attempts', type=int, default=3)
  parser.add_argument('--timeout-seconds', type=float, default=120.0)
  parser.add_argument(
      '--show-framework-output',
      action='store_true',
      help='Show Concordia engine turn logs in addition to compact progress.',
  )
  return parser


def _embed_transcripts(
    *,
    gateway: model_lib.OpenRouterGateway,
    run_id: str,
    events: list[dict[str, Any]],
) -> tuple[dict[int, list[float]], list[float]]:
  round_embeddings = {}
  for round_number in range(1, config.ROUNDS + 1):
    vector, _ = gateway.embed(
        context=model_lib.RequestContext(
            phase='embedding',
            run_id=run_id,
            round=round_number,
            scope='round',
        ),
        model=config.EMBEDDING_MODEL,
        text=metrics.transcript_text(events, round_number=round_number),
    )
    round_embeddings[round_number] = vector
  full_embedding, _ = gateway.embed(
      context=model_lib.RequestContext(
          phase='embedding', run_id=run_id, scope='full'
      ),
      model=config.EMBEDDING_MODEL,
      text=metrics.transcript_text(events),
  )
  return round_embeddings, full_embedding


def _protocol_deviations(args: argparse.Namespace) -> list[str]:
  deviations = []
  if args.mode == 'boundary' and args.runs != 15:
    deviations.append(
        f'Boundary cohort run count changed from 15 to {args.runs}.'
    )
  if args.base_url != config.OPENROUTER_BASE_URL:
    deviations.append(f'API base URL changed to {args.base_url}.')
  return deviations


def _initial_manifest(path: Path, manifest: dict[str, Any]) -> None:
  path.mkdir(parents=True, exist_ok=False)
  (path / 'manifest.json').write_text(
      json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
      encoding='utf-8',
  )


def main() -> None:
  _configure_utf8_stdio()
  _load_dotenv(Path('.env'))
  args = _parser().parse_args()
  if args.runs < 1:
    raise SystemExit('--runs must be at least 1.')
  if args.max_api_attempts < 1:
    raise SystemExit('--max-api-attempts must be at least 1.')
  api_key = os.environ.get(args.api_key_env)
  if not api_key:
    raise SystemExit(
        f'{args.api_key_env} is not set. Put it in the environment or .env; '
        'never place it in source or benchmark artifacts.'
    )

  now = dt.datetime.now(dt.timezone.utc)
  experiment_id = args.experiment_id or (
      'chope-concordia-gpt4o-mini-' + now.strftime('%Y%m%d-%H%M%S')
  )
  output_dir = args.output_root / experiment_id
  target_runs = 30 if args.mode == 'adaptive' else args.runs
  manifest = artifacts.build_manifest(
      experiment_id=experiment_id,
      mode=args.mode,
      git_commit=_git_commit(),
      requested_runs=target_runs,
      started_at=now.isoformat(),
  )
  manifest['protocol_deviations'] = _protocol_deviations(args)
  if args.mode == 'adaptive':
    manifest['adaptive_protocol'] = {
        'minimum_runs': 10,
        'batch_size': 5,
        'maximum_runs': 30,
        'two_consecutive_checkpoints_required': True,
        'earliest_declaration_n': 20,
    }
  _initial_manifest(output_dir, manifest)

  recorder = model_lib.TelemetryRecorder()
  gateway = model_lib.OpenRouterGateway(
      api_key=api_key,
      recorder=recorder,
      base_url=args.base_url,
      max_attempts=args.max_api_attempts,
      timeout_seconds=args.timeout_seconds,
  )
  runs: list[dict[str, Any]] = []
  failed_runs: list[dict[str, Any]] = []
  print(
      f'Experiment {experiment_id}: {args.mode} mode, up to {target_runs} '
      'fresh runs.'
  )

  try:
    for run_number in range(1, target_runs + 1):
      run_id = f'openai--gpt-4o-mini-{run_number:03d}'
      before_request = len(recorder.records())
      started = time.perf_counter()
      events: list[dict[str, Any]] = []
      try:
        generation_model = model_lib.ConcordiaOpenRouterModel(
            gateway=gateway, run_id=run_id
        )
        result = simulation.run_simulation(
            model=generation_model,
            run_id=run_id,
            rounds=config.ROUNDS,
            suppress_framework_output=not args.show_framework_output,
        )
        events = result['events']
        # Exactly one logical evaluator call follows each completed simulation.
        evaluator, _ = model_lib.evaluate_run(
            gateway=gateway, run_id=run_id, events=events
        )
        round_embeddings, full_embedding = _embed_transcripts(
            gateway=gateway, run_id=run_id, events=events
        )
        records = recorder.records()[before_request:]
        run = metrics.summarize_run(
            run_id=run_id,
            events=events,
            evaluator=evaluator,
            round_embeddings=round_embeddings,
            full_embedding=full_embedding,
            request_records=records,
            wall_time_ms=round((time.perf_counter() - started) * 1000, 3),
        )
        runs.append(run)
        print(
            f'[{run_number:02d}/{target_runs:02d}] {run_id}: complete; '
            f'resolution={run["deterministic_resolution"]["outcome"]}, '
            f'boundary={run["boundary"]["first_boundary_round"]}'
        )
      except KeyboardInterrupt:
        raise
      except Exception as error:  # Preserve operational evidence and continue.
        records = recorder.records()[before_request:]
        failed_runs.append({
            'run_id': run_id,
            'status': 'failed',
            'completed_turn_slots': len(events),
            'error_type': type(error).__name__,
            'error': str(error),
            'wall_time_ms': round((time.perf_counter() - started) * 1000, 3),
            'request_records': records,
            'traceback': traceback.format_exc(),
        })
        print(
            f'[{run_number:02d}/{target_runs:02d}] {run_id}: FAILED'
            f' ({type(error).__name__})'
        )

      # Across-run convergence is checked only at cumulative batches of five.
      if args.mode == 'adaptive' and len(runs) >= 20 and len(runs) % 5 == 0:
        convergence = metrics.cohort_convergence_rows(runs)
        if convergence and convergence[-1]['declared_converged']:
          print(f'Across-run cohort convergence declared at n={len(runs)}.')
          break
  except KeyboardInterrupt:
    print('\nInterrupted; writing all completed and failed-run artifacts.')
  finally:
    summary = artifacts.write_artifacts(
        output_dir=output_dir,
        manifest=manifest,
        runs=runs,
        attempted_runs=len(runs) + len(failed_runs),
        failed_runs=failed_runs,
    )
    print(
        f'Artifacts written to {output_dir.resolve()} '
        f'({summary["completed_runs"]} completed, '
        f'{summary["failed_runs"]} failed).'
    )


if __name__ == '__main__':
  main()
