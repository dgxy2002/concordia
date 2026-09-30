"""Command-line runner for the shared-housing simulation."""

from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import sys

from concordia.contrib import language_models

from examples.shared_housing import config as scenario_config
from examples.shared_housing import simulation


def _configure_utf8_stdio() -> None:
  """Allows multilingual scenarios to print safely on Windows consoles."""
  for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, 'reconfigure', None)
    if callable(reconfigure):
      reconfigure(encoding='utf-8', errors='backslashreplace')


def _load_dotenv(path: Path) -> None:
  """Loads simple KEY=VALUE entries without requiring another dependency."""
  if not path.exists():
    return
  for raw_line in path.read_text(encoding='utf-8').splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#') or '=' not in line:
      continue
    key, value = line.split('=', 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if key and key not in os.environ:
      os.environ[key] = value


def _parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
      description='Run the multilingual shared-housing simulation.'
  )
  parser.add_argument(
      '--episode',
      default='late_kitchen',
      choices=(*scenario_config.EPISODES.keys(), 'all'),
      help='Episode to run, or "all" for a longitudinal sequence.',
  )
  parser.add_argument(
      '--rounds',
      type=int,
      default=3,
      help='Number of complete four-resident rounds per episode.',
  )
  parser.add_argument(
      '--api_type',
      default='openai',
      help='A provider supported by concordia.contrib.language_models.',
  )
  parser.add_argument(
      '--model_name',
      default='gpt-4o',
      help='Provider model name.',
  )
  parser.add_argument(
      '--api_key',
      default=None,
      help='Optional API key; normally read from .env instead.',
  )
  parser.add_argument(
      '--disable_language_model',
      action='store_true',
      help='Use Concordia\'s empty mock model for a no-cost smoke test.',
  )
  parser.add_argument(
      '--output_dir',
      type=Path,
      default=Path('outputs/shared_housing'),
      help='Directory under which a timestamped result folder is created.',
  )
  return parser


def main() -> None:
  _configure_utf8_stdio()
  _load_dotenv(Path('.env'))
  args = _parser().parse_args()
  if args.rounds < 1:
    raise SystemExit('--rounds must be at least 1.')

  model = language_models.language_model_setup(
      api_type=args.api_type,
      model_name=args.model_name,
      api_key=args.api_key,
      disable_language_model=args.disable_language_model,
  )
  episodes = scenario_config.select_episodes(args.episode)
  action_count = len(episodes) * args.rounds * len(
      scenario_config.RESIDENT_NAMES
  )
  print(
      f'Running {args.episode!r}: {len(episodes)} episode(s), '
      f'{action_count} resident actions.'
  )
  results = simulation.run_simulation(
      model=model,
      episodes=episodes,
      rounds_per_episode=args.rounds,
  )

  timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
  output_dir = args.output_dir / f'{args.episode}_{timestamp}'
  output_dir.mkdir(parents=True, exist_ok=False)
  structured_log = results['structured_log']
  (output_dir / 'simulation_log.html').write_text(
      structured_log.to_html(), encoding='utf-8'
  )
  (output_dir / 'simulation_log.json').write_text(
      simulation.render_log_json(structured_log), encoding='utf-8'
  )
  (output_dir / 'transcript.txt').write_text(
      results['transcript'] + '\n', encoding='utf-8'
  )
  (output_dir / 'metrics.json').write_text(
      json.dumps(results['metrics'], ensure_ascii=False, indent=2) + '\n',
      encoding='utf-8',
  )

  print('\nTranscript:\n')
  print(results['transcript'] or '(No parseable actions were generated.)')
  print(f'\nResults written to: {output_dir.resolve()}')


if __name__ == '__main__':
  main()
