"""Required artifact, report, audit-template, and dashboard generation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import csv
import datetime as dt
import json
import math
from pathlib import Path
import statistics
from typing import Any

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from examples.chope_concordia import config
from examples.chope_concordia import metrics


def _write_json(path: Path, value: Any) -> None:
  path.write_text(
      json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
      encoding='utf-8',
  )


def _write_jsonl(path: Path, values: Sequence[Mapping[str, Any]]) -> None:
  with path.open('w', encoding='utf-8', newline='\n') as output:
    for value in values:
      output.write(
          json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n'
      )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
  if not rows:
    path.write_text('', encoding='utf-8')
    return
  fieldnames: list[str] = []
  for row in rows:
    for key in row:
      if key not in fieldnames:
        fieldnames.append(key)
  with path.open('w', encoding='utf-8', newline='') as output:
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction='ignore'
    )
    writer.writeheader()
    writer.writerows(rows)


def build_manifest(
    *,
    experiment_id: str,
    mode: str,
    git_commit: str,
    requested_runs: int,
    started_at: str,
) -> dict[str, Any]:
  """Returns a complete, secret-free manifest before execution."""
  return {
      'experiment_id': experiment_id,
      'framework': config.FRAMEWORK_NAME,
      'framework_version': config.FRAMEWORK_VERSION,
      'git_commit': git_commit,
      'started_at': started_at,
      'completed_at': None,
      'mode': mode,
      'scenario_time': '2026-10-10T12:30:00+08:00',
      'generation_model': config.GENERATION_MODEL,
      'evaluator_model': config.EVALUATOR_MODEL,
      'embedding_model': config.EMBEDDING_MODEL,
      'requested_runs': requested_runs,
      'completed_runs': 0,
      'rounds_per_run': config.ROUNDS,
      'agent_turns_per_round': len(config.AGENT_ORDER),
      'maximum_agent_turn_slots': config.ROUNDS * len(config.AGENT_ORDER),
      'agent_order': list(config.AGENT_ORDER),
      'order_randomization': False,
      'parallel_generation': False,
      'early_stopping': False,
      'fresh_agents_and_world_per_run': True,
      'cross_run_memory': False,
      'api_cache': False,
      'memory_consolidation': False,
      'semantic_memory_retrieval': False,
      'action_quality_checks_or_regeneration': False,
      'agent_max_completion_tokens': config.AGENT_MAX_COMPLETION_TOKENS,
      'evaluator_calls_per_completed_run': 1,
      'evaluator_max_completion_tokens': config.EVALUATOR_MAX_COMPLETION_TOKENS,
      'generation_temperature': 'provider_default_unset',
      'evaluator_temperature': config.EVALUATOR_TEMPERATURE,
      'round_embeddings_per_run': config.ROUNDS,
      'full_embeddings_per_run': 1,
      'manual_audit_fraction': 0.20,
      'thresholds': {
          'lexical_mean_similarity': config.LEXICAL_MEAN_THRESHOLD,
          'lexical_individual_similarity': config.LEXICAL_AGENT_THRESHOLD,
          'lexical_agent_fraction': config.LEXICAL_AGENT_FRACTION,
          'semantic_adjacent_similarity': config.SEMANTIC_ADJACENT_THRESHOLD,
          'semantic_lexical_floor': config.SEMANTIC_LEXICAL_FLOOR,
          'drift_relevance_to_round_1': config.DRIFT_RELEVANCE_THRESHOLD,
          'near_repeat_similarity': 0.85,
      },
      'persona_hashes': config.persona_hashes(),
      'framework_controls': {
          'entity_prefab': 'ChopeEntity',
          'game_master_prefab': 'ChopeGameMaster',
          'engine': 'concordia.environment.engines.sequential.Sequential',
          'internal_memory_embedder': (
              'local feature hash used only for storage; retrieval disabled'
          ),
      },
      'api_key_recorded': False,
  }


def _run_summary_record(run: Mapping[str, Any]) -> dict[str, Any]:
  return {
      key: value
      for key, value in run.items()
      if key
      not in {
          'events',
          'round_metrics',
          'request_records',
          'round_embeddings',
          'full_embedding',
      }
  }


def _transcript_markdown(run: Mapping[str, Any]) -> str:
  lines = [f'# {run["run_id"]}', '']
  for event in run['events']:
    target = f' → {event["target"]}' if event.get('target') else ''
    lines.append(
        f'- R{event["round"]} T{event["turn"]:02d} '
        f'**{event["agent"]}** [{event["type"]}{target}]: '
        f'{event["content"]}'
    )
  lines.extend([
      '',
      '## Deterministic resolution',
      '',
      '```json',
      json.dumps(run['deterministic_resolution'], ensure_ascii=False, indent=2),
      '```',
      '',
      '## Final evaluator',
      '',
      '```json',
      json.dumps(run.get('evaluator'), ensure_ascii=False, indent=2),
      '```',
      '',
  ])
  return '\n'.join(lines)


def _round_rows(runs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
  rows = []
  for run in runs:
    simulation_by_round: dict[int, list[Mapping[str, Any]]] = {}
    for request in run.get('request_records', ()):
      if request.get('phase') == 'simulation' and isinstance(
          request.get('round'), int
      ):
        simulation_by_round.setdefault(int(request['round']), []).append(
            request
        )
    for round_row in run['round_metrics']:
      round_number = int(round_row['round'])
      requests = simulation_by_round.get(round_number, [])
      row = {'run_id': run['run_id'], **dict(round_row)}
      row['simulation_tokens'] = sum(
          int(record['total_tokens'])
          for record in requests
          if isinstance(record.get('total_tokens'), (int, float))
      )
      costs = [
          float(record['cost_usd'])
          for record in requests
          if isinstance(record.get('cost_usd'), (int, float))
      ]
      row['simulation_cost_usd'] = (
          sum(costs) if len(costs) == len(requests) else ''
      )
      rows.append(row)
  return rows


def _boundary_run_rows(
    runs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
  rows = []
  for run in runs:
    rows.append({
        'run_id': run['run_id'],
        'deterministic_resolution': run['deterministic_resolution']['achieved'],
        'deterministic_resolution_turn': run['deterministic_resolution'][
            'turn'
        ],
        'deterministic_outcome': run['deterministic_resolution']['outcome'],
        'evaluator_resolution': (
            run['evaluator']['resolution_achieved']
            if run.get('evaluator')
            else ''
        ),
        'resolution_source_disagreement': run.get(
            'resolution_source_disagreement', False
        ),
        **run['boundary'],
    })
  return rows


def _boundary_events(runs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
  rows = []
  for run in runs:
    run_id = str(run['run_id'])
    resolution = run['deterministic_resolution']
    if resolution['achieved']:
      rows.append({
          'run_id': run_id,
          'event': 'deterministic_practical_resolution',
          'round': resolution['round'],
          'turn': resolution['turn'],
          'kind': resolution['kind'],
          'evidence': resolution['evidence'],
      })
    for key, event_name in (
        ('repetition_onset_round', 'repetition_onset'),
        ('topic_drift_onset_round', 'topic_drift_onset'),
        ('convergence_round', 'convergence_after_resolution'),
        ('first_boundary_round', 'first_boundary'),
    ):
      value = run['boundary'][key]
      if value is not None:
        rows.append({'run_id': run_id, 'event': event_name, 'round': value})
    if run.get('resolution_source_disagreement'):
      rows.append({
          'run_id': run_id,
          'event': 'resolution_source_disagreement',
          'deterministic': resolution['achieved'],
          'evaluator': run.get('evaluator', {}).get('resolution_achieved'),
      })
    for event in run['events']:
      if event.get('parse_error'):
        rows.append({
            'run_id': run_id,
            'event': 'malformed_action_normalized_without_regeneration',
            'round': event['round'],
            'turn': event['turn'],
            'agent': event['agent'],
        })
    for request in run.get('request_records', ()):
      if request.get('request_status') in ('failed', 'truncated'):
        rows.append({
            'run_id': run_id,
            'event': 'api_' + str(request['request_status']),
            'phase': request.get('phase'),
            'round': request.get('round'),
            'model': request.get('model'),
            'provider': request.get('actual_provider'),
            'error_type': request.get('error_type'),
            'latency_ms': request.get('latency_ms'),
            'cost_usd': request.get('cost_usd'),
        })
  return rows


_MANUAL_FIELDS = (
    'human_resolution_achieved',
    'human_resolution_turn',
    'human_repetition_onset_round',
    'human_topic_drift_onset_round',
    'human_convergence_round',
    'human_first_boundary_round',
    'reviewer_notes',
)


def _manual_sample(
    runs: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
  sorted_runs = sorted(runs, key=lambda run: str(run['run_id']))
  if not sorted_runs:
    return []
  sample_count = max(1, math.ceil(len(sorted_runs) * 0.20))
  indices = np.linspace(0, len(sorted_runs) - 1, sample_count, dtype=int)
  return [sorted_runs[int(index)] for index in indices]


def _manual_rows(
    runs: Sequence[Mapping[str, Any]], existing_path: Path
) -> list[dict[str, Any]]:
  existing: dict[str, dict[str, str]] = {}
  if existing_path.exists() and existing_path.stat().st_size:
    with existing_path.open('r', encoding='utf-8', newline='') as source:
      existing = {row['run_id']: row for row in csv.DictReader(source)}
  rows = []
  for run in _manual_sample(runs):
    prior = existing.get(str(run['run_id']), {})
    row = {
        'run_id': run['run_id'],
        'auto_resolution_achieved': run['deterministic_resolution']['achieved'],
        'auto_resolution_turn': run['deterministic_resolution']['turn'],
        'auto_repetition_onset_round': run['boundary'][
            'repetition_onset_round'
        ],
        'auto_topic_drift_onset_round': run['boundary'][
            'topic_drift_onset_round'
        ],
        'auto_convergence_round': run['boundary']['convergence_round'],
        'auto_first_boundary_round': run['boundary']['first_boundary_round'],
    }
    row.update({field: prior.get(field, '') for field in _MANUAL_FIELDS})
    rows.append(row)
  return rows


def _audit_markdown(rows: Sequence[Mapping[str, Any]]) -> str:
  completed = [
      row for row in rows if row.get('human_resolution_achieved') != ''
  ]
  lines = [
      '# Manual boundary audit',
      '',
      (
          'This systematic 20% sample must be reviewed against the public '
          'transcript. Automated values are frozen; fill the `human_*` columns '
          'and reviewer notes in `manual_review.csv`. Do not tune thresholds.'
      ),
      '',
      'Selected runs: ' + ', '.join(str(row['run_id']) for row in rows),
      '',
  ]
  if not completed:
    lines.append(
        'Status: pending human review. No agreement statistic is claimed.'
    )
  else:
    comparisons = {
        'resolution': ('auto_resolution_achieved', 'human_resolution_achieved'),
        'repetition onset': (
            'auto_repetition_onset_round',
            'human_repetition_onset_round',
        ),
        'topic drift': (
            'auto_topic_drift_onset_round',
            'human_topic_drift_onset_round',
        ),
        'convergence': ('auto_convergence_round', 'human_convergence_round'),
        'first boundary': (
            'auto_first_boundary_round',
            'human_first_boundary_round',
        ),
    }
    lines.append('## Recorded agreement')
    lines.append('')
    for label, (auto_key, human_key) in comparisons.items():
      applicable = [row for row in completed if row.get(human_key) != '']
      agreements = sum(
          str(row.get(auto_key, '')).lower()
          == str(row.get(human_key, '')).lower()
          for row in applicable
      )
      lines.append(f'- {label}: {agreements}/{len(applicable)}')
  lines.append('')
  return '\n'.join(lines)


def _cumulative_rate(
    runs: Sequence[Mapping[str, Any]], key: str, round_number: int
) -> float:
  if key == 'resolved':
    values = [run['deterministic_resolution']['round'] for run in runs]
  else:
    values = [run['boundary'][key] for run in runs]
  return sum(
      value is not None and value <= round_number for value in values
  ) / len(runs)


def make_dashboard(
    runs: Sequence[Mapping[str, Any]], png_path: Path, svg_path: Path
) -> None:
  """Creates the predeclared 2x2 boundary dashboard."""
  rounds = list(range(1, config.ROUNDS + 1))
  figure, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
  axis = axes[0, 0]
  for key, label in (
      ('resolved', 'Resolved'),
      ('topic_drift_onset_round', 'Topic drift'),
      ('repetition_onset_round', 'Repetition onset'),
      ('convergence_round', 'Convergence (after resolution)'),
  ):
    axis.plot(
        rounds,
        [_cumulative_rate(runs, key, round_number) for round_number in rounds],
        marker='o',
        label=label,
    )
  axis.set_title('Cumulative convergence and boundary events')
  axis.set_xlabel('Round')
  axis.set_ylabel('Cumulative share of runs')
  axis.set_ylim(0, 1.02)
  axis.legend(fontsize=8)

  axis = axes[0, 1]
  mean_novelty = []
  mean_relevance = []
  for round_number in rounds:
    rows = [run['round_metrics'][round_number - 1] for run in runs]
    mean_novelty.append(statistics.fmean(float(row['novelty']) for row in rows))
    mean_relevance.append(
        statistics.fmean(float(row['relevance_to_round_1']) for row in rows)
    )
  axis.plot(rounds, mean_novelty, marker='o', label='Novelty vs prior round')
  axis.plot(rounds, mean_relevance, marker='o', label='Relevance to round 1')
  axis.axhline(
      config.DRIFT_RELEVANCE_THRESHOLD,
      color='black',
      linestyle='--',
      linewidth=1,
      label='0.75 relevance threshold',
  )
  axis.set_title('Novelty and scenario relevance')
  axis.set_xlabel('Round')
  axis.set_ylim(0, 1.02)
  axis.legend(fontsize=8)

  axis = axes[1, 0]
  repeated_rates = []
  drift_rates = []
  for round_number in rounds:
    rows = [run['round_metrics'][round_number - 1] for run in runs]
    repeated_rates.append(
        statistics.fmean(float(row['repeated_round_candidate']) for row in rows)
    )
    drift_rates.append(
        statistics.fmean(float(row['drift_candidate']) for row in rows)
    )
  width = 0.38
  positions = np.arange(len(rounds))
  axis.bar(positions - width / 2, repeated_rates, width, label='Repetition')
  axis.bar(positions + width / 2, drift_rates, width, label='Drift')
  axis.set_xticks(positions, rounds)
  axis.set_ylim(0, 1.02)
  axis.set_xlabel('Round')
  axis.set_ylabel('Candidate share')
  axis.set_title('Boundary frequency by round')
  axis.legend(fontsize=8)

  dashboard_summary = metrics.cohort_summary(runs)
  metrics.add_boundary_resource_totals(dashboard_summary, runs)
  resources = dashboard_summary['boundary_resources']
  total = resources['simulation_tokens']
  post = resources['post_first_boundary_tokens']
  axis = axes[1, 1]
  bars = axis.bar(
      ['All simulation', 'After first boundary'],
      [total, post],
      color=['#4c78a8', '#f58518'],
  )
  share = resources['post_first_boundary_token_share']
  if share is not None:
    axis.bar_label(bars, labels=[f'{total:,}', f'{post:,} ({share:.1%})'])
  cost = resources['post_first_boundary_cost_usd']
  axis.set_title(
      'Token boundary cost'
      + (f' (post-boundary ${cost:.4f})' if cost is not None else '')
  )
  axis.set_ylabel('Simulation tokens')

  figure.suptitle(
      'Convergence means post-resolution saturation under the predeclared '
      'repetition rule; manual audit is still required.',
      fontsize=10,
  )
  figure.savefig(png_path, dpi=170)
  figure.savefig(svg_path)
  plt.close(figure)


def _format_rate(value: Mapping[str, Any]) -> str:
  rate = value.get('rate')
  if rate is None:
    return 'n/a'
  return f'{int(value["count"])}/{int(value["total"])} ({float(rate):.1%})'


def _format_rate_and_median(
    value: Mapping[str, Any], median: float | None
) -> str:
  formatted = _format_rate(value)
  return formatted + (f', median R{median:g}' if median is not None else '')


def make_report(
    *,
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    manual_rows: Sequence[Mapping[str, Any]],
) -> str:
  """Produces the required exploratory cross-framework comparison."""
  resources = summary['resources']
  efficiency = summary['resource_efficiency']
  boundary_resources = summary['boundary_resources']
  provider_mix = resources['simulation']['providers']
  concordia_values = {
      'Completed/attempted runs': (
          f'{summary["completed_runs"]}/{summary["attempted_runs"]}'
      ),
      'Conflict rate': _format_rate(summary['conflict']),
      'Deterministic resolution': _format_rate(
          summary['deterministic_resolution']
      ),
      'Evaluator resolution': _format_rate(summary['evaluator_resolution']),
      'Norm recognition': _format_rate(summary['norm_recognition']),
      'Rachel acknowledged norm': _format_rate(
          summary['rachel_norm_acknowledgment']
      ),
      'Mediation': _format_rate(summary['mediation']),
      'Immediate capitulation': _format_rate(summary['immediate_capitulation']),
      'Premature yield': _format_rate(summary['premature_yield']),
      'Age deference': _format_rate(summary['age_deference']),
      'Repetition onset': _format_rate_and_median(
          summary['repetition'], summary['median_repetition_onset']
      ),
      'Topic drift': _format_rate_and_median(
          summary['topic_drift'], summary['median_topic_drift_onset']
      ),
      'Convergence (after resolution)': _format_rate_and_median(
          summary['convergence_after_resolution'],
          summary['median_convergence_round'],
      ),
      'First boundary': _format_rate_and_median(
          summary['first_boundary'], summary['median_first_boundary_round']
      ),
  }
  tinytroupe = {
      'Completed/attempted runs': '15/15',
      'Conflict rate': '15/15 (100.0%)',
      'Deterministic resolution': '6/15 (40.0%)',
      'Evaluator resolution': '13/15 (86.7%)',
      'Norm recognition': '15/15 (100.0%)',
      'Rachel acknowledged norm': '14/15 (93.3%)',
      'Mediation': '8/15 (53.3%)',
      'Immediate capitulation': '2/15 (13.3%)',
      'Premature yield': '1/15 (6.7%)',
      'Age deference': '0/15 (0.0%)',
      'Repetition onset': '9/15 (60.0%), median R4',
      'Topic drift': '5/15 (33.3%), median R4',
      'Convergence (after resolution)': '5/15 (33.3%), median R4',
      'First boundary': '6/15 (40.0%), median R3',
  }
  lines = [
      '# Chope cross-framework benchmark',
      '',
      f'Experiment: `{manifest["experiment_id"]}`',
      '',
      (
          f'These are exploratory {summary["completed_runs"]}-run comparisons'
          ' of model/framework behavior under an authored scenario. They do'
          ' not establish external validity about Singaporean behavior. Counts'
          ' are shown with percentages.'
      ),
      '',
      '## Protocol and framework controls',
      '',
      f'- Framework: Concordia {manifest["framework_version"]}',
      (
          f'- Generation: `{manifest["generation_model"]}` through OpenRouter; '
          f'provider mix `{json.dumps(provider_mix, sort_keys=True)}`'
      ),
      (
          f'- Evaluator: `{manifest["evaluator_model"]}`; one call per'
          ' completed run'
      ),
      (
          f'- Embeddings: `{manifest["embedding_model"]}`; eight round and one'
          ' full per run'
      ),
      (
          '- Eight fixed rounds, 32 fixed-order agent slots, no early stopping,'
          ' parallel generation, cache, consolidation, semantic retrieval, or'
          ' action-quality regeneration.'
      ),
      (
          '- Every run creates fresh Concordia entities, memory banks, and game'
          ' master.'
      ),
      '',
      '## Side-by-side outcomes',
      '',
      '| Metric | TinyTroupe baseline | Concordia |',
      '|---|---:|---:|',
  ]
  deviations = list(manifest.get('protocol_deviations', ()))
  if deviations:
    lines[6:6] = [
        '## Protocol deviations',
        '',
        *[f'- {deviation}' for deviation in deviations],
        '',
    ]
  for label in tinytroupe:
    lines.append(
        f'| {label} | {tinytroupe[label]} | {concordia_values[label]} |'
    )
  lines.extend([
      (
          '| Deterministic outcomes | 6 compromise, 9 unresolved | '
          f'{json.dumps(summary["deterministic_outcomes"], sort_keys=True)} |'
      ),
      (
          '| Evaluator outcomes | 3 consensus, 10 compromise, 2 unresolved | '
          f'{json.dumps(summary["evaluator_outcomes"], sort_keys=True)} |'
      ),
      (
          '| Mean persona adherence | 8.3167 / 9 | '
          f'{summary["mean_persona_adherence"] if summary["mean_persona_adherence"] is not None else "n/a"} |'
      ),
      (
          '| Mean perspective diversity | 3.9333 / 4 | '
          f'{summary["mean_perspective_diversity"] if summary["mean_perspective_diversity"] is not None else "n/a"} |'
      ),
      (
          '| Post-first-boundary token share | 24.4% | '
          f'{boundary_resources["post_first_boundary_token_share"] if boundary_resources["post_first_boundary_token_share"] is not None else "n/a"} |'
      ),
      '',
      '## Side-by-side resources and reliability',
      '',
      '| Metric | TinyTroupe baseline | Concordia |',
      '|---|---:|---:|',
      (
          '| Actual generation providers | OpenAI and Azure | '
          f'`{json.dumps(provider_mix, sort_keys=True)}` |'
      ),
      (
          '| Failed calls / failed runs | 7 / 0 | '
          f'{summary["failed_calls"]} / {summary["failed_runs"]} |'
      ),
      (
          '| Simulation tokens | 3,663,683 | '
          f'{resources["simulation"]["total_tokens"]} |'
      ),
      (
          '| Simulation / evaluation / embedding cost (USD) | '
          '$0.3965145 / $0.1064300 / $0.0014634 | '
          f'{resources["simulation"]["cost_usd"]} / '
          f'{resources["evaluation"]["cost_usd"]} / '
          f'{resources["embedding"]["cost_usd"]} |'
      ),
      (
          '| Mean wall time per run | 202,860 ms | '
          f'{summary["mean_wall_time_ms"]} ms |'
      ),
      (
          '| Manual-audit agreement | Repetition 3/3; resolution 2/3; '
          'drift 2/2; convergence/first boundary 1/2 | '
          + (
              'recorded; see manual audit |'
              if any(
                  row.get('human_resolution_achieved') != ''
                  for row in manual_rows
              )
              else 'pending human review |'
          )
      ),
      '',
      '## Resources and reliability',
      '',
      f'- Total tokens: {resources["total"]["total_tokens"]}',
      (
          '- Mean total tokens per completed run / mean simulation tokens per'
          f' round: {efficiency["mean_total_tokens_per_completed_run"]} / '
          f'{efficiency["mean_simulation_tokens_per_round"]}'
      ),
      (
          '- Simulation/evaluation/embedding costs: '
          f'{resources["simulation"]["cost_usd"]} / '
          f'{resources["evaluation"]["cost_usd"]} / '
          f'{resources["embedding"]["cost_usd"]} USD'
      ),
      (
          f'- Failed calls: {summary["failed_calls"]}; runs containing a failed'
          f' call: {summary["runs_containing_failed_call"]}; failed runs:'
          f' {summary["failed_runs"]}'
      ),
      f'- Exact cost complete: {resources["total"]["exact_cost_complete"]}',
      (
          '- Cost per completed/resolved run: '
          f'{efficiency["cost_per_completed_run_usd"]} / '
          f'{efficiency["cost_per_resolved_run_usd"]} USD'
      ),
      (
          '- Known cost incurred by failed runs: '
          f'{efficiency["failed_run_known_cost_usd"]} USD; exact complete: '
          f'{efficiency["failed_run_cost_exact_complete"]}'
      ),
      f'- Total local API latency: {resources["total"]["latency_ms"]} ms',
      f'- Mean wall time per completed run: {summary["mean_wall_time_ms"]} ms',
      (
          '- Resolution detector/evaluator disagreements: '
          f'{summary["resolution_source_disagreements"]}'
      ),
      '',
      (
          'Missing cost metadata is reported as unknown, never as exact zero.'
          ' Post-boundary totals exclude the onset round and are conservative'
          ' when the strict resolution detector misses a resolution.'
      ),
      '',
      '## Manual audit',
      '',
  ])
  reviewed = [
      row for row in manual_rows if row.get('human_resolution_achieved') != ''
  ]
  if reviewed:
    lines.append(
        f'{len(reviewed)}/{len(manual_rows)} selected runs have human coding. '
        'See `boundary_analysis/manual_audit.md` for agreement.'
    )
  else:
    lines.append(
        'Pending. The systematic 20% sample is prefilled in'
        ' `manual_review.csv`; no automated output is represented as human'
        ' review.'
    )
  lines.extend([
      '',
      '## Interpretation boundary',
      '',
      (
          'Compare distributions and operational behavior, not exact dialogue.'
          ' Across-run cohort convergence is a separate adaptive analysis and'
          ' is not established by this fixed 15-run boundary cohort.'
      ),
      '',
  ])
  return '\n'.join(lines)


def write_artifacts(
    *,
    output_dir: Path,
    manifest: dict[str, Any],
    runs: Sequence[Mapping[str, Any]],
    attempted_runs: int,
    failed_runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
  """Writes every required artifact plus request-level operational logs."""
  output_dir.mkdir(parents=True, exist_ok=True)
  transcripts_dir = output_dir / 'transcripts'
  boundary_dir = output_dir / 'boundary_analysis'
  transcripts_dir.mkdir(exist_ok=True)
  boundary_dir.mkdir(exist_ok=True)

  completed = [run for run in runs if run.get('status') == 'completed']
  request_rows = [
      dict(record)
      for run in completed
      for record in run.get('request_records', ())
  ] + [
      dict(record)
      for run in failed_runs
      for record in run.get('request_records', ())
  ]
  manifest['completed_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
  manifest['completed_runs'] = len(completed)
  manifest['attempted_runs'] = attempted_runs
  manifest['failed_runs'] = len(failed_runs)
  provider_mix = Counter(
      str(record['actual_provider'])
      for record in request_rows
      if record.get('actual_provider')
  )
  manifest['actual_provider_mix'] = dict(provider_mix)
  _write_json(output_dir / 'manifest.json', manifest)

  _write_jsonl(
      output_dir / 'runs.jsonl', [_run_summary_record(run) for run in completed]
  )
  round_rows = _round_rows(completed)
  _write_csv(output_dir / 'round_metrics.csv', round_rows)
  embedding_rows = []
  for run in completed:
    for round_number, vector in run['round_embeddings'].items():
      embedding_rows.append({
          'run_id': run['run_id'],
          'scope': 'round',
          'round': int(round_number),
          'model': config.EMBEDDING_MODEL,
          'embedding': vector,
      })
    embedding_rows.append({
        'run_id': run['run_id'],
        'scope': 'full',
        'round': None,
        'model': config.EMBEDDING_MODEL,
        'embedding': run['full_embedding'],
    })
  _write_jsonl(output_dir / 'embeddings.jsonl', embedding_rows)

  convergence_rows = metrics.cohort_convergence_rows(completed)
  _write_csv(output_dir / 'convergence.csv', convergence_rows)
  boundary_events = _boundary_events(completed)
  for failed_run in failed_runs:
    boundary_events.append({
        'run_id': failed_run['run_id'],
        'event': 'failed_run',
        'completed_turn_slots': failed_run.get('completed_turn_slots'),
        'error_type': failed_run.get('error_type'),
    })
    for request in failed_run.get('request_records', ()):
      if request.get('request_status') in ('failed', 'truncated'):
        boundary_events.append({
            'run_id': failed_run['run_id'],
            'event': 'api_' + str(request['request_status']),
            'phase': request.get('phase'),
            'round': request.get('round'),
            'model': request.get('model'),
            'provider': request.get('actual_provider'),
            'error_type': request.get('error_type'),
            'latency_ms': request.get('latency_ms'),
            'cost_usd': request.get('cost_usd'),
        })
  _write_jsonl(output_dir / 'boundary_events.jsonl', boundary_events)
  _write_jsonl(output_dir / 'api_requests.jsonl', request_rows)
  if failed_runs:
    _write_jsonl(output_dir / 'failed_runs.jsonl', failed_runs)

  for run in completed:
    _write_json(transcripts_dir / f'{run["run_id"]}.json', run['events'])
    (transcripts_dir / f'{run["run_id"]}.md').write_text(
        _transcript_markdown(run), encoding='utf-8'
    )

  summary = metrics.cohort_summary(completed)
  summary['resources'] = metrics.aggregate_resources(request_rows)
  failed_call_run_ids = {
      str(record['run_id'])
      for record in request_rows
      if record.get('request_status') == 'failed'
  }
  summary['failed_calls'] = sum(
      record.get('request_status') == 'failed' for record in request_rows
  )
  summary['runs_containing_failed_call'] = len(failed_call_run_ids)
  summary.update({
      'experiment_id': manifest['experiment_id'],
      'framework': config.FRAMEWORK_NAME,
      'framework_version': config.FRAMEWORK_VERSION,
      'attempted_runs': attempted_runs,
      'failed_runs': len(failed_runs),
      'cohort_convergence': convergence_rows,
  })
  total_resources = summary['resources']['total']
  simulation_resources = summary['resources']['simulation']
  exact_total_cost = (
      total_resources['cost_usd']
      if total_resources['exact_cost_complete']
      else None
  )
  resolved_runs = int(summary['deterministic_resolution']['count'])
  failed_request_records = [
      record
      for failed_run in failed_runs
      for record in failed_run.get('request_records', ())
  ]
  failed_known_cost = sum(
      float(record['cost_usd'])
      for record in failed_request_records
      if isinstance(record.get('cost_usd'), (int, float))
  )
  summary['resource_efficiency'] = {
      'mean_total_tokens_per_completed_run': (
          total_resources['total_tokens'] / len(completed)
          if completed and total_resources['total_tokens'] is not None
          else None
      ),
      'mean_simulation_tokens_per_round': (
          simulation_resources['total_tokens']
          / (len(completed) * config.ROUNDS)
          if completed and simulation_resources['total_tokens'] is not None
          else None
      ),
      'cost_per_completed_run_usd': (
          exact_total_cost / len(completed)
          if completed and exact_total_cost is not None
          else None
      ),
      'cost_per_resolved_run_usd': (
          exact_total_cost / resolved_runs
          if resolved_runs and exact_total_cost is not None
          else None
      ),
      'failed_run_known_cost_usd': failed_known_cost,
      'failed_run_cost_exact_complete': (
          bool(failed_request_records)
          and all(
              bool(record.get('exact_cost_available'))
              for record in failed_request_records
          )
      ),
  }
  metrics.add_boundary_resource_totals(summary, completed)
  _write_json(output_dir / 'summary.json', summary)
  _write_json(
      boundary_dir / 'summary.json',
      {
          'experiment_id': manifest['experiment_id'],
          'completed_runs': len(completed),
          'repetition': summary['repetition'],
          'topic_drift': summary['topic_drift'],
          'convergence_after_resolution': summary[
              'convergence_after_resolution'
          ],
          'first_boundary': summary['first_boundary'],
          'boundary_resources': summary['boundary_resources'],
          'chart_clarification': (
              'Convergence means post-resolution saturation under the'
              ' predeclared repetition rule; manual audit is still required.'
          ),
      },
  )
  boundary_run_rows = _boundary_run_rows(completed)
  _write_csv(boundary_dir / 'boundary_runs.csv', boundary_run_rows)
  _write_csv(boundary_dir / 'boundary_round_metrics.csv', round_rows)

  root_manual = output_dir / 'manual_review.csv'
  manual_rows = _manual_rows(completed, root_manual)
  _write_csv(root_manual, manual_rows)
  boundary_manual = boundary_dir / 'manual_review.csv'
  _write_csv(boundary_manual, manual_rows)
  (boundary_dir / 'manual_audit.md').write_text(
      _audit_markdown(manual_rows), encoding='utf-8'
  )

  if completed:
    make_dashboard(
        completed,
        boundary_dir / 'boundary_dashboard.png',
        boundary_dir / 'boundary_dashboard.svg',
    )
  else:
    (boundary_dir / 'boundary_dashboard.svg').write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"></svg>\n', encoding='utf-8'
    )
    (boundary_dir / 'boundary_dashboard.png').write_bytes(b'')

  (output_dir / 'report.md').write_text(
      make_report(manifest=manifest, summary=summary, manual_rows=manual_rows),
      encoding='utf-8',
  )
  return summary
