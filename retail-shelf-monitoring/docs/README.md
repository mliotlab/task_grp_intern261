# Documentation – Retail Shelf Monitoring

Templates: [`/docs/templates`](../../docs/templates/).

| Document | Path | Due | Status |
|---|---|---|---|
| Product Requirements | `PRD.md` | Sprint 1 | ⬜ |
| Design Doc v0 → v1 (incl. row/gap/fill-rate algorithm) | `DESIGN.md` | Sprint 1 → 2 | 🟨 Draft; architecture and open decisions documented |
| ADRs | `adr/` | as decisions are made | 🟨 1 accepted, 2 proposed |
| Model Card | `../models/<version>/MODEL_CARD.md` | Sprint 3 | ⬜ |
| Test Plan | `TEST_PLAN.md` | Sprint 3 | ⬜ |
| Evaluation Report (mAP, gap P/R, latency, gap labeling rules) | `EVAL_REPORT.md` | Sprint 3 | ⬜ |
| Release Notes · Runbook · Postmortem | `RELEASE_NOTES.md` · `RUNBOOK.md` · `POSTMORTEM.md` | Sprint 4 | ⬜ |
| Weekly Status Reports | `reports/WSR-S<n>.md` | Every Friday | ⬜ |
| Dataset EDA Report (`sku110k-shelf-v2`) | `reports/sku110k_eda.md` | Sprint 1 | ✅ |
| Pretrained Baseline Report (`yolo26s`) | `reports/baseline_yolo26s.md` | Sprint 1 | ✅ |

Current ADRs: `0001-record-architecture-decisions` (Accepted), `0002-gap-detection-rule` (Proposed), `0003-post-processing-rule` (Proposed).
Suggested next ADRs: `0004-database-sqlite-vs-postgres`, `0005-detector-model-and-license`, `0006-experiment-tracking`.
