"""Structured communication, comprehension, and metrics components."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import copy
import json
import re
import threading
from typing import Any, cast

from concordia.components.game_master import event_resolution
from concordia.components.game_master import make_observation
from concordia.typing import entity as entity_lib
from concordia.typing import entity_component

from examples.shared_housing import config as scenario_config


ROUTER_COMPONENT_KEY = 'communication_router'

CHANNELS = (
    'whatsapp_group',
    'direct_message',
    'in_person',
    'private_action',
)
LANGUAGES = (
    'English',
    'Singlish',
    'Mandarin',
    'Tamil',
    'Tagalog',
    'Hindi',
    'Hokkien',
    'Cantonese',
)
INTENTS = (
    'message',
    'clarify',
    'translate',
    'apologize',
    'acknowledge',
    'clean',
    'offer_help',
    'make_request',
    'set_boundary',
    'contact_landlord',
    'pay',
    'invite',
    'leave',
    'wait',
)


ACTION_CALL_TO_ACTION = """Decide what {name} does next. Respond with one JSON
object and no prose or Markdown. Use this schema:
{"channel":"whatsapp_group|direct_message|in_person|private_action",
 "languages":["English"],
 "recipients":["exact resident name"],
 "intent":"message|clarify|translate|apologize|acknowledge|clean|offer_help|make_request|set_boundary|contact_landlord|pay|invite|leave|wait",
 "content":"the exact message spoken/written, or a concrete action"}

Use only the listed channel and intent values. `private_action` is a channel,
not an intent. To contact the landlord, use channel `private_action`, intent
`contact_landlord`, and no recipients; update the household separately later.

The content must actually use the named language or languages. If non-English
language is used, include its real words or script in content and list every
language used; do not write an English description of speaking it. Recipients are
ignored for whatsapp_group, which reaches the whole household. For an
in-person statement or direct message, list the intended recipients. Use
private_action for an action nobody else can currently observe. You may wait,
avoid the issue, misunderstand, or change the subject when that fits the
character. Do not narrate another resident's thoughts or actions."""


_SCRIPT_LANGUAGES = (
    (re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]'), 'Mandarin'),
    (re.compile(r'[\u0b80-\u0bff]'), 'Tamil'),
)


def _extract_json_object(raw_action: str) -> dict[str, Any] | None:
  """Extracts the first valid JSON object from a model action."""
  decoder = json.JSONDecoder()
  for index, character in enumerate(raw_action):
    if character != '{':
      continue
    try:
      value, _ = decoder.raw_decode(raw_action[index:])
    except json.JSONDecodeError:
      continue
    if isinstance(value, dict):
      return value
  return None


def parse_action(
    raw_action: str,
    actor: str,
    resident_names: Sequence[str] = scenario_config.RESIDENT_NAMES,
) -> dict[str, Any]:
  """Normalizes a possibly imperfect model response into an action record."""
  parsed = _extract_json_object(raw_action)
  parse_error = parsed is None
  repaired_fields: list[str] = []
  if parsed is None:
    content = raw_action.strip()
    for prefix in (f'{actor}:', actor):
      if content.startswith(prefix):
        content = content[len(prefix) :].strip()
        break
    parsed = {
        'channel': 'private_action',
        'languages': ['English'],
        'recipients': [],
        'intent': 'wait',
        'content': content or 'waits and says nothing',
    }

  channel = str(parsed.get('channel', 'private_action')).strip().lower()
  if channel not in CHANNELS:
    if channel == 'contact_landlord':
      channel = 'private_action'
      parsed['intent'] = 'contact_landlord'
      repaired_fields.append('channel:contact_landlord->private_action')
    else:
      channel = 'private_action'
      parse_error = True

  raw_languages = parsed.get('languages', parsed.get('language', ['English']))
  if isinstance(raw_languages, str):
    raw_languages = [raw_languages]
  if not isinstance(raw_languages, Sequence):
    raw_languages = ['English']
    parse_error = True
  language_lookup = {language.lower(): language for language in LANGUAGES}
  languages = []
  for language in raw_languages:
    canonical = language_lookup.get(str(language).strip().lower())
    if canonical and canonical not in languages:
      languages.append(canonical)
    elif canonical is None:
      parse_error = True
  if not languages:
    languages = ['English']

  raw_recipients = parsed.get('recipients', [])
  if isinstance(raw_recipients, str):
    raw_recipients = [raw_recipients]
  name_lookup = {name.lower(): name for name in resident_names}
  recipients = []
  if isinstance(raw_recipients, Sequence):
    for recipient in raw_recipients:
      canonical = name_lookup.get(str(recipient).strip().lower())
      if canonical and canonical not in recipients:
        recipients.append(canonical)
  else:
    parse_error = True

  intent = str(parsed.get('intent', 'message')).strip().lower()
  if intent == 'private_action':
    intent = 'message'
    repaired_fields.append('intent:private_action->message')
  elif intent not in INTENTS:
    intent = 'message'
    parse_error = True

  content = str(parsed.get('content', '')).strip()
  if not content:
    content = 'waits and says nothing'
    intent = 'wait'
    channel = 'private_action'
    parse_error = True

  for pattern, detected_language in _SCRIPT_LANGUAGES:
    if pattern.search(content) and detected_language not in languages:
      languages.append(detected_language)
      repaired_fields.append(f'languages:+{detected_language}')

  return {
      'actor': actor,
      'channel': channel,
      'languages': languages,
      'recipients': recipients,
      'intent': intent,
      'content': content,
      'parse_error': parse_error,
      'repaired_fields': repaired_fields,
      'raw_action': raw_action,
  }


def comprehension_score(
    *,
    listener: str,
    actor: str,
    languages: Sequence[str],
    written: bool,
) -> float:
  """Returns deterministic comprehension from the explicit profile data."""
  if listener == actor:
    return 1.0
  profile = scenario_config.PROFILES[listener]
  proficiency = (
      profile.written_comprehension
      if written
      else profile.spoken_comprehension
  )
  scores = [float(proficiency.get(language, 0.0)) for language in languages]
  score = sum(scores) / len(scores) if scores else 0.0

  # The scenario explicitly says Ravi's rapid accented English is especially
  # difficult for Zhang Wei. This is an individual dyadic fact, not a rule
  # inferred from either resident's nationality.
  if (
      not written
      and listener == 'Zhang Wei'
      and actor == 'Ravi Krishnamurthy'
      and 'English' in languages
  ):
    score -= 0.12
  return max(0.0, min(1.0, score))


def comprehension_band(score: float) -> str:
  if score >= 0.70:
    return 'full'
  if score >= 0.40:
    return 'partial'
  return 'none'


class CommunicationRouter(
    entity_component.ContextComponent,
    entity_component.ComponentWithLogging,
):
  """Routes events by channel and filters them by language comprehension."""

  def __init__(
      self,
      *,
      episodes: Sequence[scenario_config.Episode],
      rounds_per_episode: int,
      player_names: Sequence[str],
      make_observation_component_key: str,
      event_resolution_component_key: str,
  ):
    super().__init__()
    if not episodes:
      raise ValueError('At least one episode is required.')
    if rounds_per_episode < 1:
      raise ValueError('rounds_per_episode must be at least one.')
    self._episodes = tuple(episodes)
    self._rounds_per_episode = rounds_per_episode
    self._player_names = tuple(player_names)
    self._make_observation_component_key = make_observation_component_key
    self._event_resolution_component_key = event_resolution_component_key
    self._episode_index = 0
    self._actions_in_episode = 0
    self._turn = 0
    self._latest_action_spec: entity_lib.ActionSpec | None = None
    self._events: list[dict[str, Any]] = []
    self._deliveries: list[dict[str, Any]] = []
    self._household_state: dict[str, str] = dict(
        self._episodes[0].initial_state
    )
    self._lock = threading.Lock()

  @property
  def current_episode(self) -> scenario_config.Episode:
    return self._episodes[self._episode_index]

  def seed_initial_observations(self) -> None:
    """Queues the opening trigger after this component has an owning GM."""
    self._queue_episode_trigger(self.current_episode)

  def _observation_component(self) -> make_observation.MakeObservation:
    return self.get_entity().get_component(
        self._make_observation_component_key,
        type_=make_observation.MakeObservation,
    )

  def _queue_episode_trigger(
      self, episode: scenario_config.Episode
  ) -> None:
    observation_component = self._observation_component()
    for player_name in self._player_names:
      message = (
          f'[EPISODE: {episode.title}]\n{episode.public_trigger}\n'
          'Act only on what your character knows and perceives.'
      )
      private = episode.private_observations.get(player_name)
      if private:
        message += f'\n[PRIVATE CONTEXT] {private}'
      observation_component.add_to_queue(player_name, message)

  def pre_act(self, action_spec: entity_lib.ActionSpec) -> str:
    self._latest_action_spec = action_spec
    if action_spec.output_type != entity_lib.OutputType.RESOLVE:
      return ''
    with self._lock:
      state = ', '.join(
          f'{key}={value}' for key, value in self._household_state.items()
      )
      return (
          f'Active episode: {self.current_episode.title}. '
          f'Authoritative household state: {state}'
      )

  def post_act(self, action_attempt: str) -> str:
    if (
        self._latest_action_spec is None
        or self._latest_action_spec.output_type != entity_lib.OutputType.RESOLVE
    ):
      return ''

    resolution = self.get_entity().get_component(
        self._event_resolution_component_key,
        type_=event_resolution.EventResolution,
    )
    actor = resolution.get_active_entity_name()
    if actor is None:
      return ''
    raw_action = resolution.get_putative_action() or action_attempt
    action = parse_action(raw_action, actor, self._player_names)

    with self._lock:
      self._turn += 1
      action['turn'] = self._turn
      action['episode'] = self.current_episode.key
      self._apply_state_change(action)
      action['household_state_after'] = copy.deepcopy(self._household_state)
      self._events.append(action)
      self._route_action(action)
      self._actions_in_episode += 1
      episode_length = self._rounds_per_episode * len(self._player_names)
      if (
          self._actions_in_episode >= episode_length
          and self._episode_index + 1 < len(self._episodes)
      ):
        self._episode_index += 1
        self._actions_in_episode = 0
        next_episode = self.current_episode
        self._household_state.update(next_episode.initial_state)
        self._queue_episode_trigger(next_episode)

      self._logging_channel({
          'Key': 'Communication event',
          'Summary': self._format_transcript_line(action),
          'Value': copy.deepcopy(action),
      })
    return ''

  def _recipients_for(self, action: Mapping[str, Any]) -> Sequence[str]:
    actor = str(action['actor'])
    channel = action['channel']
    if channel == 'whatsapp_group':
      return self._player_names
    if channel == 'private_action':
      return (actor,)
    requested = cast(Sequence[str], action['recipients'])
    recipients = [name for name in requested if name in self._player_names]
    if actor not in recipients:
      recipients.append(actor)
    return tuple(recipients)

  def _route_action(self, action: Mapping[str, Any]) -> None:
    observation_component = self._observation_component()
    written = action['channel'] in ('whatsapp_group', 'direct_message')
    channel_label = {
        'whatsapp_group': 'Household WhatsApp',
        'direct_message': 'Private message',
        'in_person': 'In person',
        'private_action': 'Private action',
    }[str(action['channel'])]
    languages = cast(Sequence[str], action['languages'])
    actor = str(action['actor'])

    for listener in self._recipients_for(action):
      score = comprehension_score(
          listener=listener,
          actor=actor,
          languages=languages,
          written=written,
      )
      band = comprehension_band(score)
      if listener == actor or band == 'full':
        observation = (
            f'[{channel_label} | {" + ".join(languages)}] '
            f'{actor}: {action["content"]}'
        )
      elif band == 'partial':
        observation = (
            f'[{channel_label} | {" + ".join(languages)}] {actor} '
            'communicated, but you understood only fragments and cannot '
            'safely infer the full meaning. You can ask for clarification.'
        )
      else:
        observation = (
            f'[{channel_label} | {" + ".join(languages)}] You noticed that '
            f'{actor} communicated, but you did not understand the '
            'substantive content.'
        )
      observation_component.add_to_queue(listener, observation)
      self._deliveries.append({
          'turn': action['turn'],
          'episode': action['episode'],
          'actor': actor,
          'listener': listener,
          'channel': action['channel'],
          'languages': list(languages),
          'comprehension_score': round(score, 2),
          'comprehension': band,
      })

  def _apply_state_change(self, action: Mapping[str, Any]) -> None:
    intent = action['intent']
    actor = str(action['actor'])
    if intent == 'clean':
      if self.current_episode.key == 'late_kitchen':
        self._household_state['stove'] = 'clean'
      elif self.current_episode.key == 'night_shift_return':
        self._household_state['dining_table'] = 'cleared'
      else:
        self._household_state['shared_space'] = 'cleaned'
      self._household_state['last_cleaned_by'] = actor
    elif intent in ('acknowledge', 'apologize'):
      self._household_state['issue_status'] = 'acknowledged'
      self._household_state['acknowledged_by'] = actor
    elif intent == 'contact_landlord':
      self._household_state['landlord_contacted'] = 'yes'
      self._household_state['landlord_contacted_by'] = actor
    elif intent == 'pay':
      self._household_state['latest_payment_by'] = actor
    elif intent == 'leave':
      self._household_state[f'{actor}_location'] = 'away from common area'

  @staticmethod
  def _format_transcript_line(action: Mapping[str, Any]) -> str:
    languages = '+'.join(cast(Sequence[str], action['languages']))
    return (
        f'{int(action["turn"]):02d} [{action["episode"]}] '
        f'{action["actor"]} ({action["channel"]}, {languages}, '
        f'{action["intent"]}): {action["content"]}'
    )

  def transcript(self) -> str:
    with self._lock:
      return '\n'.join(self._format_transcript_line(event)
                       for event in self._events)

  def metrics(self) -> dict[str, Any]:
    with self._lock:
      channel_counts = Counter(event['channel'] for event in self._events)
      intent_counts = Counter(event['intent'] for event in self._events)
      language_counts = Counter(
          language
          for event in self._events
          for language in event['languages']
      )
      comprehension_counts = Counter(
          delivery['comprehension'] for delivery in self._deliveries
      )
      non_english_actions = sum(
          any(language != 'English' for language in event['languages'])
          for event in self._events
      )
      code_switching_actions = sum(
          len(event['languages']) > 1 for event in self._events
      )
      translation_actions = intent_counts.get('translate', 0)
      clarification_actions = intent_counts.get('clarify', 0)
      return {
          'actions': copy.deepcopy(self._events),
          'deliveries': copy.deepcopy(self._deliveries),
          'summary': {
              'action_count': len(self._events),
              'episode_count': len({e['episode'] for e in self._events}),
              'channel_counts': dict(channel_counts),
              'intent_counts': dict(intent_counts),
              'language_counts': dict(language_counts),
              'comprehension_counts': dict(comprehension_counts),
              'non_english_actions': non_english_actions,
              'code_switching_actions': code_switching_actions,
              'translation_actions': translation_actions,
              'clarification_actions': clarification_actions,
              'parse_errors': sum(
                  bool(event['parse_error']) for event in self._events
              ),
              'repaired_actions': sum(
                  bool(event['repaired_fields']) for event in self._events
              ),
              'behavioral_targets': {
                  'non_english_actions': {
                      'observed': non_english_actions,
                      'target': 6,
                      'met': non_english_actions >= 6,
                  },
                  'code_switching_actions': {
                      'observed': code_switching_actions,
                      'target': 2,
                      'met': code_switching_actions >= 2,
                  },
                  'translation_actions': {
                      'observed': translation_actions,
                      'target': 1,
                      'met': translation_actions >= 1,
                  },
                  'clarification_actions': {
                      'observed': clarification_actions,
                      'target': 2,
                      'met': clarification_actions >= 2,
                  },
              },
              'final_household_state': copy.deepcopy(
                  self._household_state
              ),
          },
      }

  def get_state(self) -> entity_component.ComponentState:
    with self._lock:
      return {
          'episode_index': self._episode_index,
          'actions_in_episode': self._actions_in_episode,
          'turn': self._turn,
          'events': copy.deepcopy(self._events),
          'deliveries': copy.deepcopy(self._deliveries),
          'household_state': copy.deepcopy(self._household_state),
      }

  def set_state(self, state: entity_component.ComponentState) -> None:
    with self._lock:
      self._episode_index = int(state['episode_index'])
      self._actions_in_episode = int(state['actions_in_episode'])
      self._turn = int(state['turn'])
      self._events = cast(list[dict[str, Any]], state['events'])
      self._deliveries = cast(list[dict[str, Any]], state['deliveries'])
      self._household_state = cast(
          dict[str, str], state['household_state']
      )
