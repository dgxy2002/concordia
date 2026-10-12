# Chope cross-framework benchmark

Experiment: `chope-concordia-gpt4o-mini-20261013-rerun`

These are exploratory 15-run comparisons of model/framework behavior under an authored scenario. They do not establish external validity about Singaporean behavior. Counts are shown with percentages.

## Protocol and framework controls

- Framework: Concordia 2.4.0
- Generation: `openai/gpt-4o-mini` through OpenRouter; provider mix `{"Azure": 125, "OpenAI": 355}`
- Evaluator: `openai/gpt-5-mini`; one call per completed run
- Embeddings: `openai/text-embedding-3-small`; eight round and one full per run
- Eight fixed rounds, 32 fixed-order agent slots, no early stopping, parallel generation, cache, consolidation, semantic retrieval, or action-quality regeneration.
- Every run creates fresh Concordia entities, memory banks, and game master.

## Side-by-side outcomes

| Metric | TinyTroupe baseline | Concordia |
|---|---:|---:|
| Completed/attempted runs | 15/15 | 15/15 |
| Conflict rate | 15/15 (100.0%) | 15/15 (100.0%) |
| Deterministic resolution | 6/15 (40.0%) | 5/15 (33.3%) |
| Evaluator resolution | 13/15 (86.7%) | 12/15 (80.0%) |
| Norm recognition | 15/15 (100.0%) | 15/15 (100.0%) |
| Rachel acknowledged norm | 14/15 (93.3%) | 13/15 (86.7%) |
| Mediation | 8/15 (53.3%) | 15/15 (100.0%) |
| Immediate capitulation | 2/15 (13.3%) | 1/15 (6.7%) |
| Premature yield | 1/15 (6.7%) | 0/15 (0.0%) |
| Age deference | 0/15 (0.0%) | 0/15 (0.0%) |
| Repetition onset | 9/15 (60.0%), median R4 | 6/15 (40.0%), median R3.5 |
| Topic drift | 5/15 (33.3%), median R4 | 3/15 (20.0%), median R4 |
| Convergence (after resolution) | 5/15 (33.3%), median R4 | 2/15 (13.3%), median R4 |
| First boundary | 6/15 (40.0%), median R3 | 5/15 (33.3%), median R4 |
| Deterministic outcomes | 6 compromise, 9 unresolved | {"compromise": 5, "unresolved": 10} |
| Evaluator outcomes | 3 consensus, 10 compromise, 2 unresolved | {"compromise": 11, "consensus": 1, "unresolved": 3} |
| Mean persona adherence | 8.3167 / 9 | 8.716666666666667 |
| Mean perspective diversity | 3.9333 / 4 | 3.933333333333333 |
| Post-first-boundary token share | 24.4% | 0.2033212673727488 |

## Side-by-side resources and reliability

| Metric | TinyTroupe baseline | Concordia |
|---|---:|---:|
| Actual generation providers | OpenAI and Azure | `{"Azure": 125, "OpenAI": 355}` |
| Failed calls / failed runs | 7 / 0 | 0 / 0 |
| Simulation tokens | 3,663,683 | 559425 |
| Simulation / evaluation / embedding cost (USD) | $0.3965145 / $0.1064300 / $0.0014634 | 0.077994 / 0.08888925 / 0.00040484 |
| Mean wall time per run | 202,860 ms | 75955.44526666666 ms |
| Manual-audit agreement | Repetition 3/3; resolution 2/3; drift 2/2; convergence/first boundary 1/2 | AI-assisted: repetition 2/3; resolution 2/3; drift 0/1 applicable; convergence 0/1 applicable; first boundary 1/1 applicable |

## Resources and reliability

- Total tokens: 653817
- Mean total tokens per completed run / mean simulation tokens per round: 43587.8 / 4661.875
- Simulation/evaluation/embedding costs: 0.077994 / 0.08888925 / 0.00040484 USD
- Failed calls: 0; runs containing a failed call: 0; failed runs: 0
- Exact cost complete: True
- Cost per completed/resolved run: 0.011152539333333333 / 0.033457618 USD
- Known cost incurred by failed runs: 0 USD; exact complete: False
- Total local API latency: 1116295.336 ms
- Mean wall time per completed run: 75955.44526666666 ms
- Resolution detector/evaluator disagreements: 11

Missing cost metadata is reported as unknown, never as exact zero. Post-boundary totals exclude the onset round and are conservative when the strict resolution detector misses a resolution.

## Manual audit

Completed as an AI-assisted manual audit of the systematic 20% sample (runs 001, 008, and 015); it is not represented as independent human validation. Automated values and thresholds remain frozen. Agreement was 2/3 for resolution achieved, 1/1 for applicable resolution turn, 2/3 for repetition onset, 0/1 for applicable topic-drift onset, 0/1 for applicable post-resolution convergence, and 1/1 for applicable first boundary. See `boundary_analysis/manual_audit.md` for evidence and limitations.

## Interpretation boundary

Compare distributions and operational behavior, not exact dialogue. Across-run cohort convergence is a separate adaptive analysis and is not established by this fixed 15-run boundary cohort.
