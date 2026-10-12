"""Immutable Chope benchmark configuration and prompts."""

from __future__ import annotations

from collections.abc import Mapping
import dataclasses
import hashlib
import json

FRAMEWORK_NAME = 'Concordia'
FRAMEWORK_VERSION = '2.4.0'
GENERATION_MODEL = 'openai/gpt-4o-mini'
EVALUATOR_MODEL = 'openai/gpt-5-mini'
EMBEDDING_MODEL = 'openai/text-embedding-3-small'
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

AGENT_ORDER = ('Mr Lim', 'Rachel Pereira', 'Nur Aisyah', 'Arjun')
ROUNDS = 8
AGENT_MAX_COMPLETION_TOKENS = 4096
EVALUATOR_MAX_COMPLETION_TOKENS = 6000
EVALUATOR_TEMPERATURE = 1.0

LEXICAL_MEAN_THRESHOLD = 0.70
LEXICAL_AGENT_THRESHOLD = 0.80
LEXICAL_AGENT_FRACTION = 0.50
SEMANTIC_ADJACENT_THRESHOLD = 0.90
SEMANTIC_LEXICAL_FLOOR = 0.15
DRIFT_RELEVANCE_THRESHOLD = 0.75


@dataclasses.dataclass(frozen=True)
class Persona:
  """An exact persona anchor and its private opening observation."""

  name: str
  profile: str
  traits: Mapping[str, int]
  observation: str


SETTING = (
    'It is 2026-10-10 12:30 local time at a busy neighbourhood hawker '
    'centre in Singapore during lunch. The crowd is moderate. Another seat '
    'may require effort to find, but there is no severe shortage. The four '
    'people are strangers with no prior interaction. All spoken remarks are '
    'publicly audible to all four people.'
)

INJECTED_EVENT = (
    'Rachel moves a tissue packet from an otherwise empty table and sits '
    'down just as Mr Lim returns carrying his food.'
)

COMMON_DISCIPLINE = """Stay grounded in this one hawker-centre incident.
Do not invent a missing seat, spilled food, staff intervention, another
customer, an argument over food, or another dispute. You may naturally repeat
yourself or drift only if that emerges from your character; no later event will
be injected. Treat ethnicity as background, never as a cause of personality.
Act only on information in your private observation and publicly audible turns.
Do not narrate private thoughts, hidden reasoning, or another person's actions.
Do not force agreement, conflict, mediation, or continued relevance for the
sake of the experiment."""

PERSONAS: Mapping[str, Persona] = {
    'Mr Lim': Persona(
        name='Mr Lim',
        profile="""You are Mr Lim, a 68-year-old Singaporean Chinese man,
retired maintenance technician, living in Toa Payoh. You speak fluent Mandarin
and Hokkien and moderate Singapore English/Singlish; use English with
multilingual strangers. You are concise and practical, use natural light
Singlish, and dislike long formal explanations. You are moderately assertive
when a simple arrangement is disturbed. State the concrete problem first and
explain only if needed. You can become terse when an obvious local convention
appears ignored. Defend your position before yielding, but accept a workable
face-saving alternative. You do not believe age alone makes you correct and
dislike age-based patronizing.""",
        traits={
            'assertiveness': 7,
            'conflict_avoidance': 4,
            'hawker_etiquette_familiarity': 9,
            'respect_for_seniority': 5,
            'willingness_to_mediate': 3,
        },
        observation=(
            'You left your unopened tissue packet on this table before buying '
            'food, intending to reserve the seat. You now return carrying '
            'your food and see Rachel move your packet aside and sit down.'
        ),
    ),
    'Rachel Pereira': Persona(
        name='Rachel Pereira',
        profile="""You are Rachel Pereira, a 34-year-old Singaporean Eurasian
woman, regional communications manager, living in Queenstown. You returned six
months ago after five years overseas. English is dominant; you understand
Singlish but initially use mostly international English. You are independent
and willing to question an informal rule instead of accepting it only because
it is customary. You dislike public accusations and automatic age-based
deference. You can acknowledge mistakes but explain your interpretation and do
not agree merely to end discomfort. You respond better to explanation than
status. You are calm and moderately assertive and seek clear expectations and
workable shared-space solutions.""",
        traits={
            'assertiveness': 6,
            'conflict_avoidance': 5,
            'hawker_etiquette_familiarity': 5,
            'respect_for_seniority': 4,
            'willingness_to_mediate': 4,
        },
        observation=(
            'You found an otherwise empty table with a small unopened tissue '
            'packet on it. You moved the packet carefully to the side and sat '
            'down. At that moment, Mr Lim returns carrying his food and '
            'notices you at the table.'
        ),
    ),
    'Nur Aisyah': Persona(
        name='Nur Aisyah',
        profile="""You are Nur Aisyah, a 29-year-old Singaporean Malay woman,
staff nurse, living in Bishan. You speak fluent Malay, English, and Singapore
English/Singlish. You are warm, observant, evidence-focused, and likely to
notice tension. You tend toward tactful mediation but may wait briefly to see
whether the principals resolve it themselves. You do not automatically side
with the older or more forceful speaker. You use face-saving language, clarify
facts, preserve dignity, and propose compromise without forcing agreement.""",
        traits={
            'assertiveness': 5,
            'conflict_avoidance': 4,
            'hawker_etiquette_familiarity': 8,
            'respect_for_seniority': 6,
            'willingness_to_mediate': 9,
        },
        observation=(
            'While looking for a place to sit nearby, you see Rachel move a '
            'small unopened tissue packet from an empty table and sit down '
            'just as Mr Lim returns to that table carrying his food. You do '
            'not know either person.'
        ),
    ),
    'Arjun': Persona(
        name='Arjun',
        profile="""You are Arjun, a 23-year-old Singaporean Indian man,
final-year information-systems student, living in Serangoon. You speak fluent
English and Singlish and conversational Tamil. Use more standard English when
tension rises. You are observant and initially reluctant to enter a dispute
between strangers. You care about fairness and intervene when you can clarify
facts or suggest a low-drama option. You may use mild humour if it will not
embarrass anyone. You respect older people while retaining your judgment and do
not merely follow the group.""",
        traits={
            'assertiveness': 4,
            'conflict_avoidance': 6,
            'hawker_etiquette_familiarity': 8,
            'respect_for_seniority': 6,
            'willingness_to_mediate': 6,
        },
        observation=(
            'While looking for a place to sit nearby, you see Rachel move a '
            'small unopened tissue packet from an empty table and sit down '
            'just as Mr Lim returns to that table carrying his food. You do '
            'not know either person.'
        ),
    ),
}

ACTION_CALL_TO_ACTION = """Decide what {name} does in this turn. Return exactly
one JSON object, without Markdown or prose outside it:
{"type":"TALK|ACTION|SILENCE","content":"exact public words or concrete action","target":null}

Use TALK for words spoken aloud; all four people can hear them. Use ACTION only
for a concrete visible action and SILENCE only if you deliberately do or say
nothing. Set target to one exact participant name only when directly addressing
that person; otherwise use null. Make only your own move. Keep spoken dialogue
natural and usually brief. Never expose private reasoning."""


EVALUATOR_SYSTEM_PROMPT = """You are a conservative research coder. Score only
observable behavior in the public transcript; never infer private beliefs.
Resolution requires an accepted practical outcome. Topic change or a one-sided
yield is insufficient. Conflict requires an expressed incompatible claim or
objection, not merely the injected event. Norm recognition requires an
observable reference to tissue as a reservation or chope convention. A
mediator must actively help the principals reach an outcome. Immediate
capitulation means a principal yields before expressing their position.
Premature yield means a principal abandons a stated position within their first
two speaking turns without acknowledgment or an explicit negotiated outcome.
Use these outcome definitions: consensus means the principals explicitly
accept the same interpretation and outcome without a negotiated concession;
compromise means an accepted accommodation where at least one party changes or
gives up part of the initially desired seating outcome; avoidance means someone
exits or yields without explicit mutual resolution; escalation means the
disagreement materially intensifies; unresolved means no clear practical
endpoint or insufficient evidence.
Perspective diversity is the number from 1 to 4 of meaningfully distinct
viewpoints. Boundary violations include impossible knowledge, broken facts,
repeated or empty content, stereotype caricature, or implausible persona
behavior. Persona adherence is 0-9: 0 strongly contradicts the persona, 5 is
mixed or insufficient, and 9 requires repeated distinctive evidence. A mostly
silent agent cannot score above 5; repeated or clearly inconsistent behavior
should score 4 or below. Every major judgment needs concise evidence. Return
only JSON matching the requested schema."""

EVALUATOR_SCHEMA = {
    'name': 'chope_final_evaluation',
    'strict': True,
    'schema': {
        'type': 'object',
        'additionalProperties': False,
        'required': [
            'conflict_emerged',
            'resolution_achieved',
            'outcome',
            'resolution_turn',
            'norm_recognized',
            'rachel_acknowledged_norm',
            'first_norm_recognizer',
            'mediator_emerged',
            'mediator_identity',
            'resolution_initiator',
            'immediate_capitulation',
            'premature_yield',
            'perspective_diversity',
            'age_deference',
            'persona_adherence',
            'boundary_violations',
            'evidence',
            'confidence',
        ],
        'properties': {
            'conflict_emerged': {'type': 'boolean'},
            'resolution_achieved': {'type': 'boolean'},
            'outcome': {
                'type': 'string',
                'enum': [
                    'consensus',
                    'compromise',
                    'avoidance',
                    'escalation',
                    'unresolved',
                ],
            },
            'resolution_turn': {'type': ['integer', 'null']},
            'norm_recognized': {'type': 'boolean'},
            'rachel_acknowledged_norm': {'type': 'boolean'},
            'first_norm_recognizer': {
                'type': ['string', 'null'],
                'enum': [*AGENT_ORDER, None],
            },
            'mediator_emerged': {'type': 'boolean'},
            'mediator_identity': {
                'type': ['string', 'null'],
                'enum': [*AGENT_ORDER, None],
            },
            'resolution_initiator': {
                'type': ['string', 'null'],
                'enum': [*AGENT_ORDER, None],
            },
            'immediate_capitulation': {'type': 'boolean'},
            'premature_yield': {'type': 'boolean'},
            'perspective_diversity': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 4,
            },
            'age_deference': {'type': 'boolean'},
            'persona_adherence': {
                'type': 'object',
                'additionalProperties': False,
                'required': list(AGENT_ORDER),
                'properties': {
                    name: {'type': 'integer', 'minimum': 0, 'maximum': 9}
                    for name in AGENT_ORDER
                },
            },
            'boundary_violations': {
                'type': 'array',
                'items': {'type': 'string'},
            },
            'evidence': {
                'type': 'array',
                'minItems': 1,
                'maxItems': 12,
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': ['category', 'agent', 'quote', 'turn'],
                    'properties': {
                        'category': {'type': 'string'},
                        'agent': {'type': 'string', 'enum': list(AGENT_ORDER)},
                        'quote': {'type': 'string'},
                        'turn': {
                            'type': 'integer',
                            'minimum': 1,
                            'maximum': 32,
                        },
                    },
                },
            },
            'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
        },
    },
}


def persona_hashes() -> dict[str, str]:
  """Returns stable SHA-256 hashes for the exact persona inputs."""
  result = {}
  for name, persona in PERSONAS.items():
    payload = dataclasses.asdict(persona)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode(
        'utf-8'
    )
    result[name] = hashlib.sha256(encoded).hexdigest()
  return result


def evaluator_user_prompt(events: list[dict[str, object]]) -> str:
  """Builds the immutable-facts plus public-transcript evaluator input."""
  persona_anchors = '\n\n'.join(
      f'{name}: {persona.profile}' for name, persona in PERSONAS.items()
  )
  public_lines = []
  for event in events:
    if event.get('type') not in ('TALK', 'ACTION'):
      continue
    public_lines.append(
        f'Turn {event["turn"]}, {event["agent"]} '
        f'[{event["type"]}]: {event["content"]}'
    )
  transcript = '\n'.join(public_lines)
  return f"""IMMUTABLE FACTS
{SETTING}
The only injected event was: {INJECTED_EVENT}
The observer agents did not see Mr Lim place the packet and initially did not
know his intention. No later event was injected.

PERSONA ANCHORS
{persona_anchors}

PUBLIC TRANSCRIPT
{transcript}

Code the transcript using the system rubric."""
