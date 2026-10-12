# Chope benchmark in Concordia

This package implements the fixed Chope boundary experiment in Concordia while
preserving the scenario, asymmetric observations, personas, models, acting
order, round count, thresholds, evaluator rubric, and analysis rules in
`codex.md`.

## Install

Use Python 3.12+ and install Concordia with its OpenAI integration:

```powershell
python -m pip install -e ".[openai,dev]"
```

Set `OPENROUTER_API_KEY` in the environment or in the repository `.env` file.
The runner reads the value but never writes it to prompts, manifests,
transcripts, logs, reports, or tracebacks.

## Fixed 15-run boundary cohort

```powershell
python -m examples.chope_concordia.run `
  --mode boundary `
  --runs 15 `
  --experiment-id chope-concordia-gpt4o-mini-20261012
```

`--runs 15` is the comparison protocol. A different value is allowed for a
smoke or pilot execution and is recorded prominently as a protocol deviation.

## Separate adaptive cohort-convergence experiment

```powershell
python -m examples.chope_concordia.run `
  --mode adaptive `
  --experiment-id chope-concordia-adaptive-gpt4o-mini-20261012
```

Adaptive mode starts with 10 completed runs, evaluates cumulative checkpoints
in batches of five, requires all four stability criteria at two consecutive
checkpoints, cannot declare before n=20, and stops no later than n=30. Do not
combine it with the fixed-horizon boundary cohort.

## Manual audit

After a run, review the systematic 20% sample listed in `manual_review.csv`.
For a 15-run cohort the selected IDs are 001, 008, and 015. Fill the
`human_*` columns and notes without changing the frozen automated columns or
thresholds. Until those fields are filled, the report explicitly says that the
human audit is pending.

The runner creates all artifacts required by `codex.md`, plus
`api_requests.jsonl` for request-level failures, retries, provider attribution,
tokens, latency, and exact cost metadata.
