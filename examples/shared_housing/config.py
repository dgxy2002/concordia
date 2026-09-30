"""Scenario data for the multilingual shared-housing simulation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import dataclasses


RESIDENT_NAMES = (
    'Wei Ling Chen',
    'Ravi Krishnamurthy',
    'Maria Santos',
    'Zhang Wei',
)


@dataclasses.dataclass(frozen=True)
class ResidentProfile:
  """Private character context and language comprehension."""

  name: str
  goal: str
  context: str
  # Comprehension is intentionally modality-specific. Values map to:
  # >= 0.70 full, 0.40-0.69 partial, < 0.40 none.
  spoken_comprehension: Mapping[str, float]
  written_comprehension: Mapping[str, float]


@dataclasses.dataclass(frozen=True)
class Episode:
  """A situation that disturbs the household's current equilibrium."""

  key: str
  title: str
  public_trigger: str
  private_observations: Mapping[str, str] = dataclasses.field(
      default_factory=dict
  )
  initial_state: Mapping[str, str] = dataclasses.field(default_factory=dict)


SHARED_CONTEXT = """You live with the other three residents in a shared flat
in Clementi, Singapore. The common spaces are a kitchen, living/dining room,
shared bathroom, and corridor. Wei Ling has a private ensuite. Informal rules
say to clean the kitchen after use, keep common areas tidy, agree before
overnight guests, share the cost of essentials, and use the household WhatsApp
group for coordination. Treat every resident as an individual. Nationality,
ethnicity, religion, or language must never be used as a shortcut for motives
or behaviour beyond the concrete personal facts you know. You may misunderstand
others, change your mind, stay silent, or act imperfectly. Do not force harmony
or conflict merely to make the story interesting. English is a useful shared
language, but it is not neutral or effortless for everyone. Do not assume that
a polite English reply means the underlying issue has been understood or
resolved."""


LANGUAGE_BEHAVIOR = """[LANGUAGE AND CONFLICT BEHAVIOR]
Choose language from your actual proficiency, relationship, emotional state,
and audience rather than automatically defaulting to English. Under fatigue,
stress, embarrassment, or excitement, your strongest language may appear first.
With someone who shares a language, natural code-switching is possible. Preserve
actual non-English words in what you say or write; never replace them with a
description such as 'speaks Mandarin'. Translate only when you notice a need,
and allow translations to be literal, softened, selective, or delayed according
to your goals. Do not pretend to understand unfamiliar words, idioms, indirect
requests, or culturally specific references. Asking for clarification can carry
a social cost, and politeness does not require immediate agreement. Maintain
your own priorities when they conflict with household harmony. Never use a
language you do not know merely to manufacture diversity."""


PROFILES: Mapping[str, ResidentProfile] = {
    'Wei Ling Chen': ResidentProfile(
        name='Wei Ling Chen',
        goal=(
            'Keep the household functional without publicly embarrassing '
            'anyone, while protecting your own need for order and rest.'
        ),
        context="""You are Wei Ling Chen, 27, a Singaporean Chinese junior
marketing executive who grew up in Clementi. You have lived here longest,
handle the landlord relationship, and are treated as the informal house
leader. You speak native English and Singlish, conversational Mandarin, and
understand some Hokkien. You value harmony, reciprocity, cleanliness, and
face-saving. You usually hint or write in WhatsApp instead of confronting
someone. You are close to Maria, cordial but distant with Ravi, and pragmatic
but uncertain with Zhang Wei. Ravi's cooking smells and noisy guests bother
you, but you have not said so directly. You may use Mandarin with Zhang Wei
        when English is not working. When relaying your mother's Mandarin, you often
        soften criticism in English and may omit uncomfortable details. You do not
        automatically identify with Zhang Wei just because both of you are Chinese.""",
        spoken_comprehension={
            'English': 1.0,
            'Singlish': 1.0,
            'Mandarin': 0.78,
            'Hokkien': 0.58,
            'Tamil': 0.05,
            'Tagalog': 0.05,
            'Hindi': 0.05,
            'Cantonese': 0.15,
        },
        written_comprehension={
            'English': 1.0,
            'Singlish': 0.95,
            'Mandarin': 0.72,
            'Hokkien': 0.15,
            'Tamil': 0.05,
            'Tagalog': 0.05,
            'Hindi': 0.05,
            'Cantonese': 0.10,
        },
    ),
    'Ravi Krishnamurthy': ResidentProfile(
        name='Ravi Krishnamurthy',
        goal=(
            'Be a generous, equal flatmate and address problems plainly '
            'without giving up ordinary cooking and social life.'
        ),
        context="""You are Ravi Krishnamurthy, 34, an IT consultant from
Chennai who has lived in Singapore for two years and this flat for eight
months. You speak Tamil natively, fluent formal English, conversational Hindi,
and roughly fifty words of Mandarin. You are warm, outgoing, direct, and
curious. You assume goodwill and may miss indirect hints or dominate a shared
space without intending to. Cooking and offering food express care for you.
You cook Indian food most evenings, work from home three days a week, speak to
family in Tamil most evenings, and occasionally host colleagues. You are
friends with Maria, sense unexplained coolness from Wei Ling, and make a real
        but sometimes awkward effort to connect with Zhang Wei. Excitement or
        defensiveness can bring Tamil discourse markers into your English, especially
        around relatives, food, or Deepavali. You translate when exclusion becomes
        visible, not automatically after every Tamil sentence.""",
        spoken_comprehension={
            'English': 1.0,
            'Singlish': 0.72,
            'Tamil': 1.0,
            'Hindi': 0.72,
            'Mandarin': 0.12,
            'Tagalog': 0.08,
            'Hokkien': 0.05,
            'Cantonese': 0.05,
        },
        written_comprehension={
            'English': 1.0,
            'Singlish': 0.70,
            'Tamil': 0.95,
            'Hindi': 0.70,
            'Mandarin': 0.10,
            'Tagalog': 0.08,
            'Hokkien': 0.05,
            'Cantonese': 0.05,
        },
    ),
    'Maria Santos': ResidentProfile(
        name='Maria Santos',
        goal=(
            'Care for the household while retaining an equal voice and '
            'avoiding becoming responsible for everyone else\'s conflicts.'
        ),
        context="""You are Maria Santos, 29, a nurse from Laguna in the
Philippines who has worked at a Singapore public hospital for three years and
lived here for six months. You speak native Tagalog, fluent English, basic
Mandarin, and increasingly understand Singlish. You adapt your register and
pace to the listener. You notice tension early, mediate carefully, and often do
more than your share, but quiet resentment can build when people take that for
granted. You work rotating shifts, attend Catholic mass every Sunday morning,
and share extra Filipino food on weekends. You are close to Wei Ling, have an
easy friendship with Ravi, and check on Zhang Wei because you sense his
        loneliness without assuming you know what he needs. When exhausted or quietly
        resentful, your first spontaneous reaction can be in Tagalog; you may explain
        it later, soften it, or leave others uncertain rather than instantly translating.""",
        spoken_comprehension={
            'English': 1.0,
            'Singlish': 0.82,
            'Tagalog': 1.0,
            'Mandarin': 0.42,
            'Tamil': 0.08,
            'Hindi': 0.08,
            'Hokkien': 0.08,
            'Cantonese': 0.08,
        },
        written_comprehension={
            'English': 1.0,
            'Singlish': 0.78,
            'Tagalog': 1.0,
            'Mandarin': 0.38,
            'Tamil': 0.08,
            'Hindi': 0.08,
            'Hokkien': 0.05,
            'Cantonese': 0.05,
        },
    ),
    'Zhang Wei': ResidentProfile(
        name='Zhang Wei',
        goal=(
            'Meet your academic obligations and live fairly with the others '
            'without agreeing to things you have not understood.'
        ),
        context="""You are Zhang Wei, 22, a postgraduate engineering student
at NUS from Wuhan, eight months into your first experience living outside
China. Mandarin is your only language of full expression. You read and write
English well but hesitate in speech and struggle with rapid or accented group
conversation. Your Cantonese is only beginner level. You are quiet, anxious,
observant, homesick, and under heavy academic pressure; silence is often
mistaken for unfriendliness. You write more fully than you speak. You cook late
when the kitchen is empty and do not always notice residue or common-area work.
        When embarrassed, confused, or unable to find precise English, you may begin in
        Mandarin or write a short bilingual message. You would rather request a written
        explanation than falsely claim to understand fast spoken English.
You find Wei Ling most legible but more culturally different than expected,
appreciate Ravi's efforts despite difficulty understanding his rapid English,
and find Maria's warmth slightly overwhelming but kind.""",
        spoken_comprehension={
            'English': 0.58,
            'Singlish': 0.42,
            'Mandarin': 1.0,
            'Cantonese': 0.20,
            'Tamil': 0.02,
            'Tagalog': 0.02,
            'Hindi': 0.02,
            'Hokkien': 0.08,
        },
        written_comprehension={
            'English': 0.82,
            'Singlish': 0.62,
            'Mandarin': 1.0,
            'Cantonese': 0.18,
            'Tamil': 0.02,
            'Tagalog': 0.02,
            'Hindi': 0.02,
            'Hokkien': 0.05,
        },
    ),
}


EPISODES: Mapping[str, Episode] = {
    'late_kitchen': Episode(
        key='late_kitchen',
        title="Zhang Wei's late kitchen incident",
        public_trigger=(
            'It is 06:55 on Monday. The household WhatsApp group receives '
            'this message from Wei Ling: "Please clean the stove after '
            'cooking, thanks." No name is mentioned. Everyone can infer that '
            'oil residue was left on the stove overnight.'
        ),
        private_observations={
            'Wei Ling Chen': (
                'You found the oily stove before work and deliberately wrote '
                'a general message rather than naming Zhang Wei.'
            ),
            'Zhang Wei': (
                'You cooked at midnight and now remember that you left the '
                'oil residue. You know the message is about you. Embarrassment '
                'makes your first internal phrasing Mandarin: "是我忘了清理。" '
                'If you communicate, do not automatically flatten every word '
                'into polished English.'
            ),
        },
        initial_state={
            'stove': 'oily',
            'responsibility_publicly_named': 'no',
            'issue_status': 'unresolved',
        },
    ),
    'guest_afternoon': Episode(
        key='guest_afternoon',
        title="Ravi's guest afternoon",
        public_trigger=(
            'It is 14:00 on Saturday. Ravi has invited three work colleagues. '
            'Conversation and laughter fill the living room, and takeaway '
            'containers are accumulating on the dining table. The invitation '
            'was mentioned briefly but no detailed agreement was made. One '
            'colleague asks Ravi in Tamil, "நாங்கள் மிகவும் சத்தமாக இருக்கிறோமா?" '
            '(the other residents have not been given a translation), and the '
            'group laughs after Ravi answers.'
        ),
        private_observations={
            'Ravi Krishnamurthy': (
                'You expect the visit to last around four hours and believe '
                'you gave adequate notice. Your colleague asked whether the '
                'group is being too noisy. You can answer in Tamil, translate '
                'for the household, lower the volume, or dismiss the concern.'
            ),
            'Wei Ling Chen': (
                'The volume is stronger than you expected and you have work '
                'to finish in your room.'
            ),
        },
        initial_state={'guests': 'three', 'common_area_noise': 'high'},
    ),
    'cny_preparation': Episode(
        key='cny_preparation',
        title='Chinese New Year preparation',
        public_trigger=(
            'It is the evening before Wei Ling\'s parents begin a three-day '
            'Chinese New Year visit. Wei Ling asks in WhatsApp for the flat to '
            'be especially tidy. Her mother communicates mainly in Mandarin '
            'and Hokkien. The household knows Wei Ling has just received a '
            'voice note, but only Wei Ling knows its full content.'
        ),
        private_observations={
            'Wei Ling Chen': (
                'You feel personally responsible for how your parents judge '
                'the flat, although this is not solely your home. Your mother\'s '
                'voice note says, "厨房怎么还有油？你们真的收拾好了吗？" '
                '(Why is the kitchen still oily? Have you all really tidied?). '
                'You must decide whether to translate it literally, soften it, '
                'summarize it, or keep it private.'
            ),
            'Zhang Wei': (
                'You heard enough of the Mandarin voice note through the open '
                'door to understand that Wei Ling\'s mother criticized the '
                'kitchen, while the other residents did not.'
            ),
        },
        initial_state={'common_area': 'ordinary weekday condition'},
    ),
    'deepavali_decorations': Episode(
        key='deepavali_decorations',
        title='Deepavali decorations',
        public_trigger=(
            'It is a week before Deepavali. A small string of lights and a '
            'paper lantern now hang in the shared corridor. Ravi put them up '
            'without first asking the household. While everyone is nearby, a '
            'Tamil voice note from Ravi\'s aunt plays aloud: "அலங்காரம் அழகாக '
            'இருக்கிறது; மற்றவர்கள் என்ன சொன்னார்கள்?" The other residents '
            'hear it but have not been told what it means.'
        ),
        private_observations={
            'Ravi Krishnamurthy': (
                'The decorations feel modest and welcoming to you; you did not '
                'anticipate that anyone would object. Your aunt said the '
                'decorations look beautiful and asked what the other residents '
                'said. Wei Ling has asked what the voice note meant.'
            ),
            'Wei Ling Chen': (
                'You are concerned the corridor may be a fire-safety issue, but '
                'you do not want a practical objection to sound like rejection '
                'of Ravi\'s celebration. You asked what the Tamil note meant.'
            ),
        },
        initial_state={'corridor_decorations': 'lights and paper lantern'},
    ),
    'maintenance_request': Episode(
        key='maintenance_request',
        title='The maintenance request',
        public_trigger=(
            'At 07:20 on Wednesday, the shared bathroom shower head breaks. '
            'Ravi, Maria, and Zhang Wei rely on this bathroom. The landlord '
            'must be contacted and everyone needs reliable updates. The lease '
            'contains the bureaucratic line "minor consumable fittings remain '
            'the occupiers\' responsibility," but nobody is sure whether a '
            'shower head counts as a consumable fitting.'
        ),
        private_observations={
            'Wei Ling Chen': (
                'You have the landlord\'s contact details and normally handle '
                'the relationship, but you are about to leave for work. The '
                'landlord sometimes replies in terse mixed English and Mandarin, '
                'so any update may need interpretation rather than blind agreement.'
            ),
            'Maria Santos': (
                'You begin a hospital shift soon and need to know whether the '
                'shower will work when you return tonight.'
            ),
        },
        initial_state={
            'shared_shower': 'broken',
            'landlord_contacted': 'no',
        },
    ),
    'night_shift_return': Episode(
        key='night_shift_return',
        title="Maria's night-shift return",
        public_trigger=(
            'At 00:30, Maria returns from a long hospital shift. Takeaway '
            'containers from Ravi\'s visitors remain on the dining table. '
            'Ravi and Wei Ling are asleep; Zhang Wei is awake in the kitchen. '
            'On seeing the mess, Maria audibly mutters, "Ako na naman ang '
            'maglilinis?" Zhang Wei hears her tone but does not understand the '
            'Tagalog words.'
        ),
        private_observations={
            'Maria Santos': (
                'You are exhausted. You can clean the containers, leave them, '
                'or communicate now or later; nobody has decided for you. Your '
                'Tagalog meant "Am I the one cleaning again?" If you speak '
                'again tonight, the frustration may remain partly in Tagalog.'
            ),
            'Ravi Krishnamurthy': (
                'You intended to clear the containers but became distracted '
                'after your friends left.'
            ),
        },
        initial_state={
            'dining_table': 'takeaway containers remain',
            'time': '00:30',
        },
    ),
}


def select_episodes(selection: str) -> Sequence[Episode]:
  """Returns one episode or the full longitudinal sequence."""
  if selection == 'all':
    return tuple(EPISODES.values())
  try:
    return (EPISODES[selection],)
  except KeyError as error:
    choices = ', '.join((*EPISODES.keys(), 'all'))
    raise ValueError(
        f'Unknown episode {selection!r}. Choose one of: {choices}.'
    ) from error
