# Memory-extraction evaluation

## What is measured

Support AI makes a specific claim: it extracts **durable customer facts** from
a message and keeps them for later recall. The evaluation harness measures the
extraction step, not the quality of the generated answer and not Hindsight's
retrieval ranking.

Each labelled case has:

- a customer message,
- keywords that a good fact set must contain,
- optional forbidden keywords that indicate a hallucination or a stale detail,
- the expected fact kind.

The harness computes:

| Metric | Definition |
| --- | --- |
| **Recall** | fraction of required keywords present across the extracted facts |
| **Precision** | fraction of extracted facts that contain a required keyword and no forbidden keyword |
| **F1** | harmonic mean of recall and precision |
| **Duplicates** | repeated normalised fact texts |
| **Invalid kinds** | facts whose `kind` is outside the schema's allowed set |

Scores are averaged across cases. A run fails when mean recall or mean
precision is below the threshold, or when any fact has an invalid kind.

## Running it

```bash
# Offline: validates the scorer and dataset; used in CI
python -m backend.eval.memory_eval --backend fixture

# Live: measures the configured Qwen3 model through Ollama
python -m backend.eval.memory_eval \
  --backend ollama \
  --model qwen3:8b \
  --min-recall 0.8 \
  --min-precision 0.8 \
  --output text
```

The JSON report contains per-case facts, missing keywords, irrelevant facts,
duplicates, and invalid kinds, so a failure can be debugged instead of just
observed.

## Why fixture mode exists

Fixture mode returns one clean fact per required keyword. It is deliberately
**not** a model benchmark: it proves that the dataset, metrics, thresholds, and
CLI behave correctly without requiring an 8B model in CI. Only `--backend
ollama` measures extraction quality.

## Limitations

- Eight cases is a smoke suite, not a statistically meaningful benchmark.
- Keyword coverage rewards mentioning a term, not understanding it. A fact can
  contain "Ubuntu" and still be wrong about the device.
- Precision uses required/forbidden keywords rather than a human judgement of
  every fact, so it can miss subtle hallucinations.
- The harness does not test recall-through-Hindsight end to end. Retrieval is
  covered by service-level tests with a fake Hindsight client.
- Model output is stochastic; run the live evaluation more than once before
  drawing conclusions.

## Next steps

- Grow the dataset from real (consented, redacted) support transcripts.
- Add a second rater or an LLM judge for factuality, not just keyword coverage.
- Add a cross-customer isolation test: facts retained for customer A must never
  appear in a recall for customer B. The application already uses one Hindsight
  bank per customer; the test would make that guarantee explicit.
- Track precision/recall per model and per prompt revision in CI artifacts.
