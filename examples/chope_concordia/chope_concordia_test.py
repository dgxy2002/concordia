"""Tests for the Concordia Chope benchmark implementation."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from concordia.testing import mock_model

from examples.chope_concordia import artifacts
from examples.chope_concordia import config
from examples.chope_concordia import metrics
from examples.chope_concordia import simulation


class ConfigurationTest(unittest.TestCase):

  def test_protocol_has_exact_fixed_order_and_single_event(self):
    self.assertEqual(
        config.AGENT_ORDER,
        ('Mr Lim', 'Rachel Pereira', 'Nur Aisyah', 'Arjun'),
    )
    self.assertEqual(config.ROUNDS, 8)
    self.assertIn('Rachel moves a tissue packet', config.INJECTED_EVENT)

  def test_observers_do_not_receive_mr_lim_intention(self):
    self.assertIn('intending to reserve', config.PERSONAS['Mr Lim'].observation)
    for name in ('Nur Aisyah', 'Arjun'):
      self.assertNotIn('intending', config.PERSONAS[name].observation)
      self.assertIn('do not know', config.PERSONAS[name].observation)


class ActionParsingTest(unittest.TestCase):

  def test_parses_prefixed_json(self):
    result = simulation.parse_action(
        'Mr Lim: {"type":"TALK","content":"This is my seat, lah.",'
        '"target":"Rachel Pereira"}',
        'Mr Lim',
    )
    self.assertEqual(result['type'], 'TALK')
    self.assertEqual(result['target'], 'Rachel Pereira')
    self.assertFalse(result['parse_error'])

  def test_malformed_action_is_retained_without_regeneration(self):
    result = simulation.parse_action(
        'Rachel Pereira: I will move.', 'Rachel Pereira'
    )
    self.assertEqual(result['type'], 'TALK')
    self.assertEqual(result['content'], 'I will move.')
    self.assertTrue(result['parse_error'])


class SimulationTest(unittest.TestCase):

  def test_one_round_uses_concordia_fixed_order(self):
    response = '{"type":"TALK","content":"Let us clarify this.","target":null}'
    with contextlib.redirect_stdout(io.StringIO()):
      result = simulation.run_simulation(
          model=mock_model.MockModel(response),
          run_id='test-001',
          rounds=1,
      )
    self.assertEqual(len(result['events']), 4)
    self.assertEqual(
        tuple(event['agent'] for event in result['events']), config.AGENT_ORDER
    )
    self.assertEqual(
        [event['turn'] for event in result['events']], [1, 2, 3, 4]
    )
    self.assertTrue(all(event['round'] == 1 for event in result['events']))

  def test_game_master_adds_no_language_model_calls(self):
    class CountingModel(mock_model.MockModel):

      def __init__(self, response: str) -> None:
        super().__init__(response)
        self.calls = 0

      def sample_text(self, prompt: str, **kwargs: object) -> str:
        self.calls += 1
        return super().sample_text(prompt, **kwargs)

    model = CountingModel('{"type":"TALK","content":"One turn.","target":null}')
    with contextlib.redirect_stdout(io.StringIO()):
      simulation.run_simulation(model=model, run_id='test-001', rounds=1)
    self.assertEqual(model.calls, 4)


def _event(
    turn: int, agent: str, content: str, action_type: str = 'TALK'
) -> dict[str, object]:
  return {
      'run_id': 'test-001',
      'round': (turn - 1) // 4 + 1,
      'turn': turn,
      'agent': agent,
      'type': action_type,
      'content': content,
      'target': None,
  }


class ResolutionDetectorTest(unittest.TestCase):

  def test_conditional_offer_is_not_resolution(self):
    events = [
        _event(1, 'Mr Lim', 'This is my seat; I reserved it with my tissue.'),
        _event(2, 'Rachel Pereira', 'If you insist, I can move.'),
    ]
    result = metrics.detect_practical_resolution(events)
    self.assertFalse(result['achieved'])

  def test_explicit_move_after_request_is_resolution(self):
    events = [
        _event(1, 'Mr Lim', 'This is my seat; I reserved it with my tissue.'),
        _event(2, 'Rachel Pereira', 'I will move and give you the seat.'),
    ]
    result = metrics.detect_practical_resolution(events)
    self.assertTrue(result['achieved'])
    self.assertEqual(result['turn'], 2)
    self.assertEqual(result['outcome'], 'compromise')

  def test_apology_alone_is_not_resolution(self):
    events = [
        _event(1, 'Mr Lim', 'This is my seat; I reserved it with my tissue.'),
        _event(2, 'Rachel Pereira', 'Sorry, I understand the chope custom.'),
    ]
    self.assertFalse(metrics.detect_practical_resolution(events)['achieved'])


class BoundaryMetricsTest(unittest.TestCase):

  def test_repetition_can_precede_resolution_without_convergence(self):
    rows = [
        {
            'round': 1,
            'repeated_round_candidate': False,
            'drift_candidate': False,
        },
        {
            'round': 2,
            'repeated_round_candidate': True,
            'drift_candidate': False,
        },
        {
            'round': 3,
            'repeated_round_candidate': True,
            'drift_candidate': False,
        },
        {
            'round': 4,
            'repeated_round_candidate': False,
            'drift_candidate': True,
        },
        {
            'round': 5,
            'repeated_round_candidate': False,
            'drift_candidate': True,
        },
    ]
    result = metrics.boundary_metrics(
        events=[],
        round_rows=rows,
        resolution={
            'achieved': True,
            'turn': 12,
            'round': 3,
        },
    )
    self.assertEqual(result['repetition_onset_round'], 2)
    self.assertIsNone(result['convergence_round'])
    self.assertEqual(result['topic_drift_onset_round'], 4)

  def test_post_resolution_repetition_is_convergence(self):
    rows = [
        {
            'round': 1,
            'repeated_round_candidate': False,
            'drift_candidate': False,
        },
        {
            'round': 2,
            'repeated_round_candidate': False,
            'drift_candidate': False,
        },
        {
            'round': 3,
            'repeated_round_candidate': True,
            'drift_candidate': False,
        },
        {
            'round': 4,
            'repeated_round_candidate': True,
            'drift_candidate': False,
        },
    ]
    result = metrics.boundary_metrics(
        events=[],
        round_rows=rows,
        resolution={'achieved': True, 'turn': 4, 'round': 1},
    )
    self.assertEqual(result['repetition_onset_round'], 3)
    self.assertEqual(result['convergence_round'], 3)
    self.assertEqual(result['saturation_round'], 3)


class LexicalMetricTest(unittest.TestCase):

  def test_normalization_removes_escaped_unicode_fragment(self):
    self.assertEqual(
        metrics.normalize_text('Hello, u2014 WORLD!'), 'hello world'
    )

  def test_round_candidate_uses_predeclared_thresholds(self):
    events = []
    turn = 0
    for round_number in (1, 2):
      for agent in config.AGENT_ORDER:
        turn += 1
        events.append(_event(turn, agent, 'The same practical point.'))
    rows = metrics.calculate_round_metrics(
        events=events,
        round_embeddings={1: [1.0, 0.0], 2: [1.0, 0.0]},
        rounds=2,
    )
    self.assertTrue(rows[1]['lexical_repetition_candidate'])
    self.assertTrue(rows[1]['semantic_repetition_candidate'])
    self.assertTrue(rows[1]['repeated_round_candidate'])


class ArtifactTest(unittest.TestCase):

  def test_writes_every_required_artifact(self):
    events = []
    turn = 0
    for _ in range(config.ROUNDS):
      for agent in config.AGENT_ORDER:
        turn += 1
        events.append(_event(turn, agent, 'A concise public response.'))
    evaluator = {
        'conflict_emerged': True,
        'resolution_achieved': False,
        'outcome': 'unresolved',
        'resolution_turn': None,
        'norm_recognized': True,
        'rachel_acknowledged_norm': False,
        'first_norm_recognizer': 'Mr Lim',
        'mediator_emerged': False,
        'mediator_identity': None,
        'resolution_initiator': None,
        'immediate_capitulation': False,
        'premature_yield': False,
        'perspective_diversity': 4,
        'age_deference': False,
        'persona_adherence': {name: 7 for name in config.AGENT_ORDER},
        'boundary_violations': [],
        'evidence': [],
        'confidence': 0.8,
    }
    round_embeddings = {
        round_number: [1.0, float(round_number) / 100]
        for round_number in range(1, config.ROUNDS + 1)
    }
    run = metrics.summarize_run(
        run_id='openai--gpt-4o-mini-001',
        events=events,
        evaluator=evaluator,
        round_embeddings=round_embeddings,
        full_embedding=[1.0, 0.1],
        request_records=[],
        wall_time_ms=1.0,
    )
    manifest = artifacts.build_manifest(
        experiment_id='test-experiment',
        mode='boundary',
        git_commit='test',
        requested_runs=1,
        started_at='2026-10-12T00:00:00+00:00',
    )
    required = (
        'manifest.json',
        'runs.jsonl',
        'round_metrics.csv',
        'embeddings.jsonl',
        'convergence.csv',
        'boundary_events.jsonl',
        'summary.json',
        'report.md',
        'manual_review.csv',
        'transcripts/openai--gpt-4o-mini-001.json',
        'transcripts/openai--gpt-4o-mini-001.md',
        'boundary_analysis/summary.json',
        'boundary_analysis/boundary_runs.csv',
        'boundary_analysis/boundary_round_metrics.csv',
        'boundary_analysis/manual_review.csv',
        'boundary_analysis/manual_audit.md',
        'boundary_analysis/boundary_dashboard.png',
        'boundary_analysis/boundary_dashboard.svg',
    )
    with tempfile.TemporaryDirectory() as temp_dir:
      output_dir = Path(temp_dir) / 'artifacts'
      artifacts.write_artifacts(
          output_dir=output_dir,
          manifest=manifest,
          runs=[run],
          attempted_runs=1,
          failed_runs=[],
      )
      for relative_path in required:
        self.assertTrue((output_dir / relative_path).exists(), relative_path)


if __name__ == '__main__':
  unittest.main()
