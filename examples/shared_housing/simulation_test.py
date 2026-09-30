"""End-to-end smoke tests for the shared-housing simulation."""

import contextlib
import io
import unittest

from concordia.testing import mock_model
import numpy as np

from examples.shared_housing import config
from examples.shared_housing import simulation


class SimulationTest(unittest.TestCase):

  def test_local_embedder_is_deterministic_and_normalized(self):
    first = simulation.local_hash_embedder('clean the kitchen')
    second = simulation.local_hash_embedder('clean the kitchen')

    np.testing.assert_array_equal(first, second)
    self.assertAlmostEqual(float(np.linalg.norm(first)), 1.0, places=6)

  def test_one_round_runs_end_to_end_without_api(self):
    response = (
        '{"channel":"whatsapp_group","languages":["English"],'
        '"recipients":[],"intent":"clarify",'
        '"content":"Can we clarify what happened?"}'
    )
    with contextlib.redirect_stdout(io.StringIO()):
      results = simulation.run_simulation(
          model=mock_model.MockModel(response),
          episodes=(config.EPISODES['late_kitchen'],),
          rounds_per_episode=1,
      )

    metrics = results['metrics']
    self.assertEqual(metrics['summary']['action_count'], 4)
    self.assertEqual(metrics['summary']['episode_count'], 1)
    self.assertEqual(metrics['summary']['parse_errors'], 0)
    self.assertEqual(
        metrics['summary']['channel_counts'], {'whatsapp_group': 4}
    )
    self.assertEqual(len(metrics['deliveries']), 16)
    self.assertIn('[late_kitchen]', results['transcript'])


if __name__ == '__main__':
  unittest.main()
