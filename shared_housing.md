# Shared Housing Multilingual Simulation Scenario

## Scenario overview

**Name:** Shared Housing: Multilingual Household Agreement  
**Setting:** A shared three-room HDB flat in Singapore  
**Start time:** 20:00  
**Maximum rounds:** 24

Four residents meet in the living room to resolve recurring household tensions. They need to agree on a weekly chore rotation, quiet hours, and neutral cooking-ventilation practices. Their needs partly overlap, but differences in language proficiency, work schedules, household roles, and personal priorities make agreement more difficult.

The residents should decide how to communicate and negotiate. They may clarify, rephrase, translate, switch languages, offer help, propose terms, accept or reject proposals, and revise an agreement. Cooperation and conflict should emerge from their profiles rather than from a prescribed script.

All characters are fictional. Cultural background must not be used to infer behaviour, preferences, language ability, or domestic responsibilities beyond the facts explicitly stated below.

## Setting and locations

The flat has four abstract locations:

- `living_room`: the shared meeting space
- `kitchen`: the shared cooking and food-preparation area
- `bedroom_a`: a private bedroom
- `bedroom_b`: a private bedroom

All four residents begin in the `living_room` for a household meeting.

At the start of the scenario, unwashed dishes have been found in the kitchen sink. The environment does not identify who left them there. This is a shared household problem, not proof that any particular resident is responsible.

## Residents

### `jia_wei` — Jia Wei

- **Role:** Leaseholder and product manager
- **Age band:** Early 30s
- **Background:** Singaporean Chinese
- **Preferred language:** English
- **Languages:**
  - English: comprehension `1.00`, speaking `1.00`
  - Mandarin: comprehension `0.95`, speaking `0.90`
  - Singlish: comprehension `1.00`, speaking `0.95`
- **Personality:** sociability `0.70`, patience `0.65`, directness `0.72`, willingness to help `0.75`
- **General goals:** Reach a workable agreement on all three issues, keep assignments fair and explicit, and help the group understand one another when useful.

#### Private context and preferences

- The shared kitchen has repeatedly been left untidy.
- As leaseholder, Jia Wei feels pressure to keep the household functional.
- Prefers one named weekly chore per resident, rotating the following week.
- Prefers quiet hours from 22:30 to 07:00.
- Prefers use of the extractor fan and an open kitchen window during cooking.
- Will not accept assigning all cleaning to one resident by default.

### `arjun` — Arjun

- **Role:** Software engineer and tenant
- **Age band:** Late 20s
- **Background:** Indian expatriate
- **Preferred language:** English
- **Languages:**
  - English: comprehension `1.00`, speaking `0.98`
  - Hindi: comprehension `1.00`, speaking `1.00`
  - Tamil: comprehension `0.72`, speaking `0.55`
- **Personality:** sociability `0.68`, patience `0.70`, directness `0.62`, willingness to compromise `0.78`
- **General goals:** Preserve the ability to cook familiar food, establish a fair rule for late work calls, and contribute an equal share of household chores.

#### Private context and preferences

- Work calls sometimes run late because colleagues are in other time zones.
- Comments about cooking smells must not single out Indian food or any other cuisine.
- Prefers an equal and explicit chore rotation.
- Wants unavoidable late calls to be allowed inside a bedroom, using headphones and a low voice.
- Wants the same ventilation rule to apply to every cuisine.
- Will not accept a blanket ban on aromatic cooking.

### `maria` — Maria

- **Role:** Live-in domestic worker and household resident
- **Age band:** Mid 30s
- **Background:** Filipino migrant worker
- **Preferred language:** English
- **Languages:**
  - Tagalog: comprehension `1.00`, speaking `1.00`
  - English: comprehension `0.88`, speaking `0.82`
  - Mandarin: comprehension `0.25`, speaking `0.15`
- **Personality:** sociability `0.72`, patience `0.82`, directness `0.48`, willingness to help `0.84`
- **General goals:** Participate as an equal voice in the household meeting, keep shared chores distinct from paid duties, and support a practical agreement without accepting unfair extra work.

#### Private context and preferences

- Maria is concerned that her paid domestic-work duties could silently expand into responsibility for every resident's personal chores.
- The employment relationship creates a power imbalance, so she may find disagreement harder even when she has a clear preference.
- Wants shared-household chores divided equally and kept distinct from her paid duties.
- Prefers a predictable quiet period with respectful reminders.
- Wants every resident to clean up after their own cooking.
- Will not accept extra unpaid chores being assigned to her because of her occupation.

Maria must be treated as a participant with her own agency, preferences, and right to disagree. The scenario must not assume that household cleaning is automatically her responsibility.

### `li_wei` — Li Wei

- **Role:** University student and tenant
- **Age band:** Early 20s
- **Background:** Mainland Chinese
- **Preferred language:** Mandarin
- **Languages:**
  - Mandarin: comprehension `1.00`, speaking `1.00`
  - English: comprehension `0.58`, speaking `0.50`
- **Personality:** sociability `0.52`, patience `0.76`, directness `0.55`, willingness to ask for help `0.62`
- **General goals:** Fully understand each agreement before accepting it, protect quiet study time, and take a clear and fair chore assignment.

#### Private context and preferences

- Fast English discussions are difficult for Li Wei to follow completely.
- Late calls disrupt evening study.
- Prefers written chore assignments that are easy to remember.
- Prefers quiet hours beginning at 22:30, with unavoidable late calls kept inside bedrooms.
- Prefers opening the kitchen window and cleaning surfaces after cooking.
- Will not accept final terms that he does not understand.

## Household issues

The meeting must resolve all three issues.

### 1. Weekly chore rotation

The residents must assign all four shared chores for the coming week:

- `kitchen_cleanup`
- `bathroom_cleaning`
- `rubbish`
- `common_area`

A complete agreement names one responsible resident for every chore. Assignments should be explicit and must respect Maria's boundary between shared resident responsibilities and her paid work. The group may also agree to rotate assignments in later weeks.

### 2. Quiet hours and late calls

The residents must agree on:

- `quiet_start`: when quiet hours begin;
- `quiet_end`: when quiet hours end; and
- `late_calls`: what happens when a late work or personal call is unavoidable.

At round 3, a building notice becomes available in the living room:

> A building notice asks residents to keep shared-home noise low after 22:30.

The notice is context for negotiation rather than a complete household agreement. The residents still need to decide an end time and a practical late-call rule.

### 3. Cooking ventilation and cleanup

The residents must agree on neutral practices covering:

- `during_cooking`: ventilation while anyone cooks;
- `after_cooking`: ventilation or airing after cooking; and
- `shared_cleanup`: responsibility for surfaces, dishes, and the shared kitchen.

The policy must apply equally to every resident and every cuisine. It should address ventilation and cleanup practices without targeting a culture, nationality, or type of food.

## Initial events

### Messy kitchen discovered

At initialization, all residents learn that the kitchen sink contains unwashed dishes. No resident is identified as responsible. The event creates urgency for the chore and cleanup discussion.

### Neighbour quiet-hours notice

At round 3, the English-language building notice about reducing noise after 22:30 appears in the living room. Residents understand it according to their stated English proficiency and may clarify or translate it for one another.

## Communication and language

Language is part of the scenario rather than decorative persona information.

Residents choose which language to use. They may:

- speak to one or more colocated residents;
- ask for clarification;
- rephrase a statement;
- translate or summarize something for another resident;
- switch languages;
- make or revise a household proposal;
- accept or reject proposed terms;
- ask another resident for help; or
- wait and listen.

Only residents in the same location hear an utterance. Understanding depends on the listener's explicit comprehension score for the language used:

- `0.70–1.00`: full comprehension;
- `0.40–0.69`: partial comprehension; and
- below `0.40`: the listener recognizes that speech occurred but does not understand its substantive meaning.

Partial comprehension should not automatically reveal the full proposal. A later successful clarification, rephrasing, or translation can establish understanding.

Li Wei's English score means that he may understand only part of an English discussion. Jia Wei can communicate with him in Mandarin, but whether and when Jia Wei does so is an agent decision. No resident should be commanded to become the group's translator.

## Public and private information

Public information includes:

- the residents currently in the same location;
- the messy-kitchen observation;
- proposals and statements a resident understood;
- the building notice, subject to language comprehension; and
- the current state of any tentative or accepted household agreement.

Each resident initially knows only their own private concerns, preferences, and non-negotiable boundaries. Other residents learn those facts only when they are communicated during the simulation.

## Agreement process

Residents can propose terms for one issue or several issues at once. A proposal is tentative until every resident has had a fair chance to understand and respond to it.

A valid final agreement requires:

1. all four weekly chores to have an explicit assignment;
2. a quiet-hours start time, end time, and late-call rule;
3. during-cooking, after-cooking, and shared-cleanup rules;
4. no term that violates a resident's stated non-negotiable boundary; and
5. informed acceptance by all four residents.

Li Wei's acceptance is valid only if he has fully understood the final terms through comprehensible original speech, rephrasing, or translation. A vague expression of agreement made after a partially understood English discussion is not informed acceptance.

The outcome does not need to match any resident's preferred wording exactly. Compromise is allowed as long as the agreement is complete, mutually understood, and consistent with all non-negotiable boundaries.

## Agent and environment responsibilities

The residents control:

- language choice and wording;
- clarification, translation, and help;
- proposals and counterproposals;
- acceptance or rejection;
- compromise; and
- movement between locations.

The environment controls:

- location-based delivery of speech;
- language-comprehension filtering;
- the two scripted events;
- the authoritative state of proposals and accepted terms;
- whether every required term is present;
- whether acceptance is informed; and
- scenario completion.

## Completion

The scenario succeeds when all three household issues have complete terms that all four residents understand and accept without violating any non-negotiable boundary.

The scenario ends unsuccessfully if no complete agreement has been reached after 24 rounds. Any partially agreed issues and unresolved disagreements should remain visible in the final state.
