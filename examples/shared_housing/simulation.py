"""Build and run the shared-housing simulation."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import re
from typing import Any

from concordia.language_model import language_model
from concordia.prefabs import entity as entity_prefabs
from concordia.prefabs.simulation import generic as generic_simulation
from concordia.typing import prefab as prefab_lib
from concordia.utils import structured_logging
import numpy as np

from examples.shared_housing import communication
from examples.shared_housing import config as scenario_config
from examples.shared_housing import game_master


_EMBEDDING_SIZE = 384
_TOKEN_PATTERN = re.compile(r"[\w']+", re.UNICODE)


def local_hash_embedder(text: str) -> np.ndarray:
  """Returns a deterministic local embedding without a model download.

  This is a feature-hashing bag-of-words embedder. It is deliberately simple,
  but preserves enough token overlap for this small simulation's associative
  memories and makes the example runnable without sentence-transformers.
  """
  vector = np.zeros(_EMBEDDING_SIZE, dtype=np.float32)
  for token in _TOKEN_PATTERN.findall(text.casefold()):
    digest = hashlib.blake2b(token.encode('utf-8'), digest_size=8).digest()
    bucket = int.from_bytes(digest[:4], 'little') % _EMBEDDING_SIZE
    sign = 1.0 if digest[4] & 1 else -1.0
    vector[bucket] += sign
  norm = np.linalg.norm(vector)
  if norm:
    vector /= norm
  return vector


def build_config(
    *,
    episodes: Sequence[scenario_config.Episode],
    rounds_per_episode: int,
) -> prefab_lib.Config:
  """Constructs a Concordia config for the selected episodes."""
  prefabs = {
      'minimal__Entity': entity_prefabs.minimal.Entity(),
      'shared_housing__GameMaster': game_master.GameMaster(),
  }
  instances = []
  for resident_name in scenario_config.RESIDENT_NAMES:
    profile = scenario_config.PROFILES[resident_name]
    instances.append(
        prefab_lib.InstanceConfig(
            prefab='minimal__Entity',
            role=prefab_lib.Role.ENTITY,
            params={  # pyrefly: ignore[bad-argument-type]
                'name': resident_name,
                'goal': profile.goal,
                'randomize_choices': False,
            },
        )
    )

  # Starting with Zhang Wei makes the default kitchen episode a true follow-up
  # to Wei Ling's already-sent message rather than having her speak twice.
  acting_order = (
      'Zhang Wei',
      'Ravi Krishnamurthy',
      'Maria Santos',
      'Wei Ling Chen',
  )
  instances.append(
      prefab_lib.InstanceConfig(
          prefab='shared_housing__GameMaster',
          role=prefab_lib.Role.GAME_MASTER,
          params={  # pyrefly: ignore[bad-argument-type]
              'name': 'shared housing environment',
              'episodes': tuple(episodes),
              'rounds_per_episode': rounds_per_episode,
              'acting_order': acting_order,
          },
      )
  )
  max_steps = (
      len(scenario_config.RESIDENT_NAMES)
      * rounds_per_episode
      * len(episodes)
  )
  return prefab_lib.Config(
      default_premise=(
          'This is a grounded simulation of an ordinary shared household in '
          'Clementi, Singapore. Preserve private information and route all '
          'communication through the specified channel rules.'
      ),
      default_max_steps=max_steps,
      prefabs=prefabs,
      instances=instances,
  )


def _seed_resident_context(
    simulation: generic_simulation.Simulation,
) -> None:
  """Adds exact persona facts without generating stereotyped backstories."""
  for entity in simulation.get_entities():
    profile = scenario_config.PROFILES[entity.name]
    entity.observe(
        '[PRIVATE IDENTITY AND BACKGROUND]\n'
        f'{profile.context}\n\n'
        '[SHARED HOUSEHOLD CONTEXT]\n'
        f'{scenario_config.SHARED_CONTEXT}\n\n'
        f'{scenario_config.LANGUAGE_BEHAVIOR}\n\n'
        '[SIMULATION DISCIPLINE]\n'
        'Remain this specific person, but do not mechanically repeat traits. '
        'Respond to what you actually observe. Other residents cannot read '
        'this private context.'
    )


def run_simulation(
    *,
    model: language_model.LanguageModel,
    episodes: Sequence[scenario_config.Episode],
    rounds_per_episode: int = 3,
) -> dict[str, Any]:
  """Runs the configured scenario and returns logs, transcript, and metrics."""
  config = build_config(
      episodes=episodes,
      rounds_per_episode=rounds_per_episode,
  )
  simulation = generic_simulation.Simulation(
      config=config,
      model=model,
      embedder=local_hash_embedder,
  )
  _seed_resident_context(simulation)
  structured_log = simulation.play()

  game_masters = simulation.get_game_masters()
  if len(game_masters) != 1:
    raise RuntimeError(f'Expected one game master, found {len(game_masters)}.')
  router = game_masters[0].get_component(
      communication.ROUTER_COMPONENT_KEY,
      type_=communication.CommunicationRouter,
  )
  return {
      'structured_log': structured_log,
      'transcript': router.transcript(),
      'metrics': router.metrics(),
      'simulation': simulation,
  }


def render_log_json(log: structured_logging.SimulationLog) -> str:
  """Small typed wrapper used by the command-line runner."""
  return log.to_json()
