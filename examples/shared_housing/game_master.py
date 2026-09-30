"""Game-master prefab for the shared-housing simulation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import dataclasses
from typing import Any

from concordia.agents import entity_agent_with_logging
from concordia.associative_memory import basic_associative_memory
from concordia.components import agent as agent_components
from concordia.components import game_master as gm_components
from concordia.components.game_master import event_resolution as resolution_lib
from concordia.language_model import language_model
from concordia.typing import entity as entity_lib
from concordia.typing import prefab as prefab_lib

from examples.shared_housing import communication
from examples.shared_housing import config as scenario_config


@dataclasses.dataclass
class GameMaster(prefab_lib.Prefab):
  """A deterministic channel router around generative resident agents."""

  description: str = 'Shared-housing multilingual environment.'
  params: Mapping[str, Any] = dataclasses.field(
      default_factory=lambda: {
          'name': 'shared housing environment',
          'episodes': (scenario_config.EPISODES['late_kitchen'],),
          'rounds_per_episode': 3,
          'acting_order': scenario_config.RESIDENT_NAMES,
      }
  )
  entities: Sequence[entity_agent_with_logging.EntityAgentWithLogging] = ()

  def build(
      self,
      model: language_model.LanguageModel,
      memory_bank: basic_associative_memory.AssociativeMemoryBank,
  ) -> entity_agent_with_logging.EntityAgentWithLogging:
    name = str(self.params.get('name', 'shared housing environment'))
    player_names = [entity.name for entity in self.entities]
    episodes = self.params.get('episodes', ())
    if not isinstance(episodes, Sequence):
      raise TypeError('episodes must be a sequence of Episode objects.')
    rounds_per_episode = int(self.params.get('rounds_per_episode', 3))
    acting_order = tuple(self.params.get('acting_order', player_names))
    if set(acting_order) != set(player_names):
      raise ValueError(
          'acting_order must contain every resident exactly once. '
          f'Expected {player_names}, got {acting_order}.'
      )

    instructions_key = 'instructions'
    instructions = gm_components.instructions.Instructions()

    players_key = 'player_characters'
    players = gm_components.instructions.PlayerCharacters(
        player_characters=player_names
    )

    memory_key = agent_components.memory.DEFAULT_MEMORY_COMPONENT_KEY
    memory = agent_components.memory.AssociativeMemory(memory_bank=memory_bank)

    observation_to_memory_key = 'observation_to_memory'
    observation_to_memory = agent_components.observation.ObservationToMemory()

    observation_history_key = (
        agent_components.observation.DEFAULT_OBSERVATION_COMPONENT_KEY
    )
    observation_history = agent_components.observation.LastNObservations(
        history_length=1000
    )

    make_observation_key = (
        gm_components.make_observation.DEFAULT_MAKE_OBSERVATION_COMPONENT_KEY
    )
    make_observation = gm_components.make_observation.MakeObservation(
        model=model,
        player_names=player_names,
        allow_llm_fallback=False,
    )

    next_actor_key = gm_components.next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY
    next_actor = gm_components.next_acting.NextActingInFixedOrder(
        sequence=acting_order
    )

    next_action_spec_key = (
        gm_components.next_acting.DEFAULT_NEXT_ACTION_SPEC_COMPONENT_KEY
    )
    next_action_spec = gm_components.next_acting.FixedActionSpec(
        action_spec=entity_lib.free_action_spec(
            call_to_action=communication.ACTION_CALL_TO_ACTION,
            tag='shared_housing_action',
        )
    )

    resolution_key = gm_components.switch_act.DEFAULT_RESOLUTION_COMPONENT_KEY
    remove_wrapper = resolution_lib.RemoveSpecificText(
        substring_to_remove='Putative event to resolve:  '
    )
    resolution = gm_components.event_resolution.EventResolution(
        model=model,
        event_resolution_steps=(remove_wrapper,),
        notify_observers=False,
    )

    router = communication.CommunicationRouter(
        episodes=episodes,  # pyrefly: ignore[bad-argument-type]
        rounds_per_episode=rounds_per_episode,
        player_names=player_names,
        make_observation_component_key=make_observation_key,
        event_resolution_component_key=resolution_key,
    )

    terminate_key = gm_components.terminate.DEFAULT_TERMINATE_COMPONENT_KEY
    terminate = gm_components.terminate.NeverTerminate()

    components = {
        instructions_key: instructions,
        players_key: players,
        observation_history_key: observation_history,
        observation_to_memory_key: observation_to_memory,
        memory_key: memory,
        make_observation_key: make_observation,
        next_actor_key: next_actor,
        next_action_spec_key: next_action_spec,
        resolution_key: resolution,
        communication.ROUTER_COMPONENT_KEY: router,
        terminate_key: terminate,
    }
    component_order = list(components.keys())
    act_component = gm_components.switch_act.SwitchAct(
        model=model,
        entity_names=player_names,
        component_order=component_order,
    )
    game_master = entity_agent_with_logging.EntityAgentWithLogging(
        agent_name=name,
        act_component=act_component,
        context_components=components,
        measurements=self.params.get('measurements'),
    )
    router.seed_initial_observations()
    return game_master
