# Chope cross-framework benchmark

Experiment: `chope-concordia-gpt4o-mini-20261013`

These are exploratory 0-run comparisons of model/framework behavior under an authored scenario. They do not establish external validity about Singaporean behavior. Counts are shown with percentages.

## Protocol and framework controls

- Framework: Concordia 2.4.0
- Generation: `openai/gpt-4o-mini` through OpenRouter; provider mix `{}`
- Evaluator: `openai/gpt-5-mini`; one call per completed run
- Embeddings: `openai/text-embedding-3-small`; eight round and one full per run
- Eight fixed rounds, 32 fixed-order agent slots, no early stopping, parallel generation, cache, consolidation, semantic retrieval, or action-quality regeneration.
- Every run creates fresh Concordia entities, memory banks, and game master.

## Side-by-side outcomes

| Metric | TinyTroupe baseline | Concordia |
|---|---:|---:|
| Completed/attempted runs | 15/15 | 0/15 |
| Conflict rate | 15/15 (100.0%) | n/a |
| Deterministic resolution | 6/15 (40.0%) | n/a |
| Evaluator resolution | 13/15 (86.7%) | n/a |
| Norm recognition | 15/15 (100.0%) | n/a |
| Rachel acknowledged norm | 14/15 (93.3%) | n/a |
| Mediation | 8/15 (53.3%) | n/a |
| Immediate capitulation | 2/15 (13.3%) | n/a |
| Premature yield | 1/15 (6.7%) | n/a |
| Age deference | 0/15 (0.0%) | n/a |
| Repetition onset | 9/15 (60.0%), median R4 | n/a |
| Topic drift | 5/15 (33.3%), median R4 | n/a |
| Convergence (after resolution) | 5/15 (33.3%), median R4 | n/a |
| First boundary | 6/15 (40.0%), median R3 | n/a |
| Deterministic outcomes | 6 compromise, 9 unresolved | {} |
| Evaluator outcomes | 3 consensus, 10 compromise, 2 unresolved | {} |
| Mean persona adherence | 8.3167 / 9 | n/a |
| Mean perspective diversity | 3.9333 / 4 | n/a |
| Post-first-boundary token share | 24.4% | n/a |

## Side-by-side resources and reliability

| Metric | TinyTroupe baseline | Concordia |
|---|---:|---:|
| Actual generation providers | OpenAI and Azure | `{}` |
| Failed calls / failed runs | 7 / 0 | 45 / 15 |
| Simulation tokens | 3,663,683 | None |
| Simulation / evaluation / embedding cost (USD) | $0.3965145 / $0.1064300 / $0.0014634 | None / None / None |
| Mean wall time per run | 202,860 ms | None ms |
| Manual-audit agreement | Repetition 3/3; resolution 2/3; drift 2/2; convergence/first boundary 1/2 | pending human review |

## Resources and reliability

- Total tokens: None
- Mean total tokens per completed run / mean simulation tokens per round: None / None
- Simulation/evaluation/embedding costs: None / None / None USD
- Failed calls: 45; runs containing a failed call: 15; failed runs: 15
- Exact cost complete: False
- Cost per completed/resolved run: None / None USD
- Known cost incurred by failed runs: 0 USD; exact complete: False
- Total local API latency: 92576.212 ms
- Mean wall time per completed run: None ms
- Resolution detector/evaluator disagreements: 0

Missing cost metadata is reported as unknown, never as exact zero. Post-boundary totals exclude the onset round and are conservative when the strict resolution detector misses a resolution.

## Manual audit

Pending. The systematic 20% sample is prefilled in `manual_review.csv`; no automated output is represented as human review.

## Interpretation boundary

Compare distributions and operational behavior, not exact dialogue. Across-run cohort convergence is a separate adaptive analysis and is not established by this fixed 15-run boundary cohort.
