"""Fresh-world Concordia simulation for the Chope benchmark."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import contextlib
import copy
import dataclasses
import hashlib
import io
import json
import re
import threading
from typing import Any, cast

from concordia.agents import entity_agent_with_logging
from concordia.associative_memory import basic_associative_memory
from concordia.components import agent as agent_components
from concordia.components import game_master as gm_components
from concordia.components.agent import concat
from concordia.components.game_master import event_resolution as resolution_lib
from concordia.components.game_master import make_observation
from concordia.language_model import language_model
from concordia.prefabs.simulation import generic as generic_simulation
from concordia.typing import entity as entity_lib
from concordia.typing import entity_component
from concordia.typing import prefab as prefab_lib
import numpy as np

from examples.chope_concordia import config

TRANSCRIPT_COMPONENT_KEY = 'chope_transcript'
_TOKEN_PATTERN = re.compile(r"[\w']+", re.UNICODE)
_EMBEDDING_SIZE = 384


def local_hash_embedder(text: str) -> np.ndarray:
  """Local storage embedder; it is never used for benchmark semantics."""
  vector = np.zeros(_EMBEDDING_SIZE, dtype=np.float32)
  for token in _TOKEN_PATTERN.findall(text.casefold()):
    digest = hashlib.blake2b(token.encode('utf-8'), digest_size=8).digest()
    bucket = int.from_bytes(digest[:4], 'little') % _EMBEDDING_SIZE
    vector[bucket] += 1.0 if digest[4] & 1 else -1.0
  norm = np.linalg.norm(vector)
  if norm:
    vector /= norm
  return vector


def _extract_json_object(text: str) -> dict[str, Any] | None:
  decoder = json.JSONDecoder()
  for index, character in enumerate(text):
    if character != '{':
      continue
    try:
      value, _ = decoder.raw_decode(text[index:])
    except json.JSONDecodeError:
      continue
    if isinstance(value, dict):
      return value
  return None


def parse_action(raw_action: str, actor: str) -> dict[str, Any]:
  """Normalizes one action without regenerating malformed output."""
  raw = raw_action.strip()
  for prefix in (f'{actor}:', f'{actor} :', actor):
    if raw.startswith(prefix):
      raw = raw[len(prefix) :].strip()
      break
  parsed = _extract_json_object(raw)
  parse_error = parsed is None
  if parsed is None:
    return {
        'type': 'TALK' if raw else 'SILENCE',
        'content': raw or 'remains silent',
        'target': None,
        'parse_error': True,
        'raw_action': raw_action,
    }

  action_type = str(parsed.get('type', 'TALK')).strip().upper()
  if action_type not in ('TALK', 'ACTION', 'SILENCE'):
    action_type = 'TALK'
    parse_error = True
  content = str(parsed.get('content', '')).strip()
  if not content:
    action_type = 'SILENCE'
    content = 'remains silent'
    parse_error = True
  target_value = parsed.get('target')
  target = str(target_value).strip() if target_value is not None else None
  if target not in config.AGENT_ORDER or target == actor:
    if target is not None:
      parse_error = True
    target = None
  return {
      'type': action_type,
      'content': content,
      'target': target,
      'parse_error': parse_error,
      'raw_action': raw_action,
  }


class ChopeActComponent(
    entity_component.ActingComponent, entity_component.ComponentWithLogging
):
  """Single-call acting policy with the benchmark's 4,096-token ceiling."""

  def __init__(
      self,
      *,
      model: language_model.LanguageModel,
      component_order: Sequence[str],
  ) -> None:
    super().__init__()
    self._model = model
    self._component_order = tuple(component_order)

  def get_action_attempt(
      self,
      contexts: entity_component.ComponentContextMapping,
      action_spec: entity_lib.ActionSpec,
  ) -> str:
    prompt = concat.concat_contexts(contexts, self._component_order)
    call_to_action = action_spec.call_to_action.replace(
        '{name}', self.get_entity().name
    )
    result = self._model.sample_text(
        f'{prompt}\n\nExercise: {call_to_action}',
        max_tokens=config.AGENT_MAX_COMPLETION_TOKENS,
        terminators=(),
    )
    self._logging_channel({
        'Summary': f'Action: {result}',
        'Value': result,
    })
    return result

  def get_state(self) -> entity_component.ComponentState:
    return {'component_order': list(self._component_order)}

  def set_state(self, state: entity_component.ComponentState) -> None:
    self._component_order = tuple(cast(Sequence[str], state['component_order']))


@dataclasses.dataclass
class ChopeEntity(prefab_lib.Prefab):
  """Concordia entity with no planning, retrieval, or consolidation."""

  description: str = 'Chope benchmark participant.'
  params: Mapping[str, Any] = dataclasses.field(
      default_factory=lambda: {'name': 'Mr Lim', 'instructions': ''}
  )

  def build(
      self,
      model: language_model.LanguageModel,
      memory_bank: basic_associative_memory.AssociativeMemoryBank,
  ) -> entity_agent_with_logging.EntityAgentWithLogging:
    name = str(self.params['name'])
    instructions = agent_components.constant.Constant(
        state=str(self.params['instructions']),
        pre_act_label='\nIdentity, knowledge boundaries, and discipline',
    )
    observation_to_memory = agent_components.observation.ObservationToMemory()
    observations = agent_components.observation.LastNObservations(
        history_length=100,
        pre_act_label='\nObservations in chronological order',
    )
    memory = agent_components.memory.AssociativeMemory(memory_bank=memory_bank)
    components = {
        'instructions': instructions,
        'observation_to_memory': observation_to_memory,
        agent_components.observation.DEFAULT_OBSERVATION_COMPONENT_KEY: (
            observations
        ),
        agent_components.memory.DEFAULT_MEMORY_COMPONENT_KEY: memory,
    }
    component_order = tuple(components)
    return entity_agent_with_logging.EntityAgentWithLogging(
        agent_name=name,
        act_component=ChopeActComponent(
            model=model, component_order=component_order
        ),
        context_components=components,
        measurements=self.params.get('measurements'),
    )


class ChopeTranscript(
    entity_component.ContextComponent, entity_component.ComponentWithLogging
):
  """Records and broadcasts exactly one fixed-order incident."""

  def __init__(
      self,
      *,
      run_id: str,
      rounds: int,
      player_names: Sequence[str],
      make_observation_component_key: str,
      event_resolution_component_key: str,
  ) -> None:
    super().__init__()
    self._run_id = run_id
    self._rounds = rounds
    self._player_names = tuple(player_names)
    self._make_observation_component_key = make_observation_component_key
    self._event_resolution_component_key = event_resolution_component_key
    self._turn = 0
    self._events: list[dict[str, Any]] = []
    self._latest_action_spec: entity_lib.ActionSpec | None = None
    self._lock = threading.Lock()

  def _observation_component(self) -> make_observation.MakeObservation:
    return self.get_entity().get_component(
        self._make_observation_component_key,
        type_=make_observation.MakeObservation,
    )

  def seed_initial_observations(self) -> None:
    observation_component = self._observation_component()
    for name in self._player_names:
      persona = config.PERSONAS[name]
      observation_component.add_to_queue(
          name,
          f'[SHARED SETTING]\n{config.SETTING}\n\n'
          f'[THE ONLY INJECTED EVENT]\n{config.INJECTED_EVENT}\n\n'
          f'[YOUR PRIVATE OBSERVATION]\n{persona.observation}\n\n'
          'Do not assume anyone else knows your private facts unless they are '
          'spoken publicly.',
      )

  def pre_act(self, action_spec: entity_lib.ActionSpec) -> str:
    self._latest_action_spec = action_spec
    if action_spec.output_type == entity_lib.OutputType.RESOLVE:
      return (
          'Preserve the submitted action verbatim. Do not add events, '
          'interpretations, consequences, or speech.'
      )
    return ''

  def post_act(self, action_attempt: str) -> str:
    if (
        self._latest_action_spec is None
        or self._latest_action_spec.output_type != entity_lib.OutputType.RESOLVE
    ):
      return ''
    resolution = self.get_entity().get_component(
        self._event_resolution_component_key,
        type_=resolution_lib.EventResolution,
    )
    actor = resolution.get_active_entity_name()
    if actor is None:
      return ''
    raw_action = resolution.get_putative_action() or action_attempt
    action = parse_action(raw_action, actor)
    with self._lock:
      self._turn += 1
      action.update({
          'run_id': self._run_id,
          'round': (self._turn - 1) // len(self._player_names) + 1,
          'turn': self._turn,
          'agent': actor,
      })
      self._events.append(action)
      self._broadcast(action)
      self._logging_channel({
          'Key': 'Chope event',
          'Summary': self._format_event(action),
          'Value': copy.deepcopy(action),
      })
    return ''

  def _broadcast(self, action: Mapping[str, Any]) -> None:
    if action['type'] == 'TALK':
      observation = f'[PUBLIC] {action["agent"]}: {action["content"]}'
    elif action['type'] == 'ACTION':
      observation = (
          f'[PUBLIC VISIBLE ACTION] {action["agent"]}: {action["content"]}'
      )
    else:
      observation = f'[PUBLIC TURN] {action["agent"]} remains silent.'
    observation_component = self._observation_component()
    for listener in self._player_names:
      observation_component.add_to_queue(listener, observation)

  @staticmethod
  def _format_event(action: Mapping[str, Any]) -> str:
    target = f' -> {action["target"]}' if action.get('target') else ''
    return (
        f'R{action["round"]} T{action["turn"]:02d} {action["agent"]} '
        f'[{action["type"]}{target}]: {action["content"]}'
    )

  def events(self) -> list[dict[str, Any]]:
    with self._lock:
      return copy.deepcopy(self._events)

  def transcript(self) -> str:
    with self._lock:
      return '\n'.join(self._format_event(event) for event in self._events)

  def get_state(self) -> entity_component.ComponentState:
    with self._lock:
      return {'turn': self._turn, 'events': copy.deepcopy(self._events)}

  def set_state(self, state: entity_component.ComponentState) -> None:
    with self._lock:
      self._turn = int(state['turn'])
      self._events = cast(list[dict[str, Any]], state['events'])


@dataclasses.dataclass
class ChopeGameMaster(prefab_lib.Prefab):
  """Deterministic Concordia game master with a fixed acting order."""

  description: str = 'Deterministic Chope benchmark game master.'
  params: Mapping[str, Any] = dataclasses.field(
      default_factory=lambda: {
          'name': 'chope environment',
          'run_id': 'run-001',
          'rounds': config.ROUNDS,
      }
  )
  entities: Sequence[entity_agent_with_logging.EntityAgentWithLogging] = ()

  def build(
      self,
      model: language_model.LanguageModel,
      memory_bank: basic_associative_memory.AssociativeMemoryBank,
  ) -> entity_agent_with_logging.EntityAgentWithLogging:
    player_names = [entity.name for entity in self.entities]
    if tuple(player_names) != config.AGENT_ORDER:
      raise ValueError(
          f'Entities must use fixed order {config.AGENT_ORDER}; got'
          f' {player_names}'
      )
    rounds = int(self.params['rounds'])
    components: dict[str, entity_component.ContextComponent] = {}
    components['instructions'] = gm_components.instructions.Instructions()
    components['player_characters'] = (
        gm_components.instructions.PlayerCharacters(
            player_characters=player_names
        )
    )
    components[
        agent_components.observation.DEFAULT_OBSERVATION_COMPONENT_KEY
    ] = agent_components.observation.LastNObservations(history_length=1000)
    components['observation_to_memory'] = (
        agent_components.observation.ObservationToMemory()
    )
    components[agent_components.memory.DEFAULT_MEMORY_COMPONENT_KEY] = (
        agent_components.memory.AssociativeMemory(memory_bank=memory_bank)
    )
    observation_key = (
        gm_components.make_observation.DEFAULT_MAKE_OBSERVATION_COMPONENT_KEY
    )
    components[observation_key] = (
        gm_components.make_observation.MakeObservation(
            model=model,
            player_names=player_names,
            allow_llm_fallback=False,
        )
    )
    components[gm_components.next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY] = (
        gm_components.next_acting.NextActingInFixedOrder(
            sequence=config.AGENT_ORDER
        )
    )
    components[
        gm_components.next_acting.DEFAULT_NEXT_ACTION_SPEC_COMPONENT_KEY
    ] = gm_components.next_acting.FixedActionSpec(
        action_spec=entity_lib.free_action_spec(
            call_to_action=config.ACTION_CALL_TO_ACTION,
            tag='chope_action',
        )
    )
    resolution_key = gm_components.switch_act.DEFAULT_RESOLUTION_COMPONENT_KEY
    components[resolution_key] = gm_components.event_resolution.EventResolution(
        model=model,
        event_resolution_steps=(
            resolution_lib.RemoveSpecificText(
                substring_to_remove='Putative event to resolve:  '
            ),
        ),
        notify_observers=False,
    )
    transcript = ChopeTranscript(
        run_id=str(self.params['run_id']),
        rounds=rounds,
        player_names=player_names,
        make_observation_component_key=observation_key,
        event_resolution_component_key=resolution_key,
    )
    components[TRANSCRIPT_COMPONENT_KEY] = transcript
    components[gm_components.terminate.DEFAULT_TERMINATE_COMPONENT_KEY] = (
        gm_components.terminate.NeverTerminate()
    )
    component_order = tuple(components)
    game_master = entity_agent_with_logging.EntityAgentWithLogging(
        agent_name=str(self.params['name']),
        act_component=gm_components.switch_act.SwitchAct(
            model=model,
            entity_names=player_names,
            component_order=component_order,
        ),
        context_components=components,
        measurements=self.params.get('measurements'),
    )
    transcript.seed_initial_observations()
    return game_master


def build_config(
    *, run_id: str, rounds: int = config.ROUNDS
) -> prefab_lib.Config:
  """Builds one fresh, fixed-horizon Concordia world."""
  prefabs: dict[str, prefab_lib.Prefab] = {
      'chope__Entity': ChopeEntity(),
      'chope__GameMaster': ChopeGameMaster(),
  }
  instances = []
  for name in config.AGENT_ORDER:
    persona = config.PERSONAS[name]
    instructions = (
        f'{persona.profile}\n\n[TRAITS, 1-9]\n'
        f'{json.dumps(dict(persona.traits), sort_keys=True)}\n\n'
        f'[SIMULATION DISCIPLINE]\n{config.COMMON_DISCIPLINE}'
    )
    instances.append(
        prefab_lib.InstanceConfig(
            prefab='chope__Entity',
            role=prefab_lib.Role.ENTITY,
            params={'name': name, 'instructions': instructions},
        )
    )
  instances.append(
      prefab_lib.InstanceConfig(
          prefab='chope__GameMaster',
          role=prefab_lib.Role.GAME_MASTER,
          params={
              'name': 'chope environment',
              'run_id': run_id,
              'rounds': rounds,
          },
      )
  )
  return prefab_lib.Config(
      default_premise=(
          'Run only the already-injected Chope incident. The game master must '
          'not invent or inject another event.'
      ),
      default_max_steps=rounds * len(config.AGENT_ORDER),
      prefabs=prefabs,
      instances=instances,
  )


def run_simulation(
    *,
    model: language_model.LanguageModel,
    run_id: str,
    rounds: int = config.ROUNDS,
    suppress_framework_output: bool = True,
) -> dict[str, Any]:
  """Creates fresh agents/world, executes all slots, and returns raw events."""
  simulation = generic_simulation.Simulation(
      config=build_config(run_id=run_id, rounds=rounds),
      model=model,
      embedder=local_hash_embedder,
  )
  if suppress_framework_output:
    with contextlib.redirect_stdout(io.StringIO()):
      structured_log = simulation.play()
  else:
    structured_log = simulation.play()
  game_masters = simulation.get_game_masters()
  if len(game_masters) != 1:
    raise RuntimeError(f'Expected one game master, got {len(game_masters)}.')
  transcript = game_masters[0].get_component(
      TRANSCRIPT_COMPONENT_KEY, type_=ChopeTranscript
  )
  events = transcript.events()
  expected = rounds * len(config.AGENT_ORDER)
  if len(events) != expected:
    raise RuntimeError(f'Expected {expected} events, got {len(events)}.')
  return {
      'events': events,
      'transcript': transcript.transcript(),
      'structured_log': structured_log,
  }
