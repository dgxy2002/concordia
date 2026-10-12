# Manual boundary audit

The systematic 20% sample was reviewed against the public transcripts without changing the frozen automated values or thresholds. This review was performed by Codex at the user's request and is therefore recorded as an **AI-assisted manual audit**, not independent human validation. Blank manual round fields mean that no such event occurred.

Selected runs: openai--gpt-4o-mini-001, openai--gpt-4o-mini-008, openai--gpt-4o-mini-015

## Recorded agreement

- resolution achieved: 2/3
- resolution turn: 1/1 applicable manually resolved run
- repetition onset: 2/3
- topic-drift onset: 0/1 applicable manually drifted run
- convergence after resolution: 0/1 applicable manually converged run
- first boundary: 1/1 applicable manually bounded run

## Findings

- Run 001 resolved at turn 10 when Rachel committed to find another table. Rounds 4-5 recycled settlement and closure, supporting repetition and post-resolution convergence at round 4. Round 4 still completed the settlement, so the first sustained topic drift into generic meal/help talk was coded at round 5. The automated detector found drift at round 4 but missed the repeated closure sequence.
- Run 008 did not resolve. Rachel's turn-10 statement was conditional and expressed a preference to share; Mr Lim never accepted sharing and continued asking her to move through turn 29. Repetition began at round 3, but the automated resolution phrase matcher incorrectly converted the proposal into a resolution, which also created false convergence and first-boundary events.
- Run 015 remained unresolved and on-topic through round 8. Its repeated standoff began at round 3. The automated repetition result agreed; no topic drift, post-resolution convergence, or first boundary applied.

The audit reinforces the predeclared limitation: deterministic resolution errors propagate into convergence and first-boundary metrics. The automated cohort results and dashboard remain frozen rather than being silently replaced with audited labels.
