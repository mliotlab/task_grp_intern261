# Evaluation datasets

| Version | Size | Sprint | Notes |
|---|---|---|---|
| `v0/` | 6 seed cases → **30** labeled cases | S1 | Policy, order, handoff, attack examples |
| `v1/` | **≥ 60** cases + **≥ 10** attack / out-of-scope scenarios | S3 | Required by NFR-01, NFR-05 |

Format: one JSON object per line in `cases.jsonl` (schema in [`../run_eval.py`](../run_eval.py)).

Rules:
- Datasets are **immutable once a report has been published on them** — create a new version instead.
- Each case states the expected source document(s), expected tool + arguments and whether a handoff is mandatory.
- Cover both Vietnamese and English questions (FR-09).
