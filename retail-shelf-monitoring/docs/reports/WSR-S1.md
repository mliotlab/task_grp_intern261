# Weekly Status Report – Sprint 1 (17/11 – 21/11/2026)

**Project:** Retail Shelf Monitoring (RSM) · **Scrum Master:** Trần Tất Nguyên · **Status:** 🟢 Green

## 1. TL;DR

Sprint 1 completed the PRD, Design Doc v0, the inference/post-processing contract, the curated `sku110k-shelf-v2` dataset, a pretrained YOLO26s baseline, and the first gap-annotation evaluation set. The main Sprint 1 deliverables were merged with green CI; implementation of the walking skeleton and remaining runtime decisions move to Sprint 2. Mentor confirmation is still needed for the PostgreSQL runtime plan, no-detection alert policy, and final post-processing decisions.

## 2. Sprint goal and outcome

**Goal:** Establish a shared product/design baseline, reproducible dataset and evaluation setup, and a technically reviewed starting point for the Sprint 2 walking skeleton.

**Outcome:** **Achieved** — the planned Sprint 1 documentation, dataset, baseline evaluation, and gap-labeling deliverables were completed and merged.

## 3. Work progress

| Issue | Owner | Status | PR | Notes |
|---|---|---|---|---|
| #10 [Task] Write PRD v1.0 | Nguyên | Done | [#17](https://github.com/mliotlab/task_grp_intern261/pull/17) | Product scope, FR/NFR, sprint plan, and team responsibilities documented. |
| #11 [Task] Write Design Doc v0 | Nguyên / Phú | Done | [#33](https://github.com/mliotlab/task_grp_intern261/pull/33) | Earlier PR #28 was closed; the work continued on the same branch and was merged through PR #33. |
| #12 Define inference/post-processing JSON schema | Phú | Done | [#33](https://github.com/mliotlab/task_grp_intern261/pull/33) | JSON contract aligned with `shelfmon` schemas; ADR-0002 and ADR-0003 added. |
| #13 [NFR-06] Create SKU-110K subset and EDA | Phú | Done | [#18](https://github.com/mliotlab/task_grp_intern261/pull/18) | Deterministic `1000/200/200` subset and EDA pipeline created. |
| #39 [NFR-06] Curate `sku110k-shelf-v2` | Phú | Done | [#36](https://github.com/mliotlab/task_grp_intern261/pull/36) | 193 non-shelf/floor-stack/blurry images excluded and splits deterministically backfilled. |
| #14 [NFR-01][NFR-03] Run pretrained YOLO baseline | Phú | Done | [#48](https://github.com/mliotlab/task_grp_intern261/pull/48) | YOLO26s baseline evaluated on `val_spike50`; report and reproducible scripts added. |
| #15 [FR-03][NFR-02] Gap labeling guidelines | Phú / Nguyên | Done | [#53](https://github.com/mliotlab/task_grp_intern261/pull/53) | 60-image gap set completed: 30 `valid` images for tuning and 30 `test` images held out for final evaluation. |

## 4. Metrics

- Issues completed / committed: **7/7** Sprint 1 issues (`#10`, `#11`, `#12`, `#13`, `#14`, `#15`, `#39`).
- PRs merged: **6** relevant RSM PRs (`#17`, `#18`, `#33`, `#36`, `#48`, `#53`). PR #28 was an earlier closed iteration superseded by PR #33.
- Average review time: **TBD** — to be calculated from GitHub review timestamps.
- CI pass rate on `main`: **100% for the listed merged RSM PR checks**; RSM lint/test and Docker smoke checks passed for the recent PRs.
- Test coverage: **72%** in the current scaffold test run (`26 passed`, existing TODO-related tests skipped where applicable).
- Product and dataset metrics:
  - Curated dataset: **1,400 images** (`1,000 train / 200 val / 200 test`), **203,873 product boxes**, seed `2026`.
  - Manifest SHA-256: `c18daf36f20b59c210c5a6265c65f024af26dd80ba80ce8215da01dc80fcf22d`.
  - Pretrained YOLO26s on `val_spike50` (50 validation images, 7,284 GT boxes): `mAP@0.5 = 0.3753`; `mAP@0.5:0.95 = 0.1731`.
  - Baseline latency: GPU p95 **1,153.6 ms**; CPU p95 **4,756.2 ms** on approximately 8 MP images. CPU latency must be rechecked under the NFR-03 longest-edge `<=1920 px` condition.
  - Gap evaluation set: **60 images / 207 gap boxes** (`valid`: 30 images/96 boxes for tuning; `test`: 30 images/111 boxes held out for final NFR-02 reporting).
- Hours per member: **TBD** — to be filled from the team's time records.

## 5. Demo

- Dataset EDA report: [`docs/reports/sku110k_eda.md`](./sku110k_eda.md).
- Pretrained baseline report: [`docs/reports/baseline_yolo26s.md`](./baseline_yolo26s.md).
- Gap annotation export and local review set are documented in PR #53; exported images remain local and are not committed.
- Sprint 1 demo: Live walkthrough of `sku110k_eda.md`, `baseline_yolo26s.md`, and Roboflow v3 gap annotations during Friday mentor sync.

## 6. Technical decisions

- [Design Doc v0](../DESIGN.md) defines the architecture, API contracts, ML/backend boundary, data model, and Sprint 2 implementation target.
- [ADR-0002 – Gap detection, fill rate, and evaluation](../adr/0002-gap-detection-rule.md) defines local gap-width references, empty-row handling, fill-rate aggregation, annotation rules, and NFR-02 matching.
- [ADR-0003 – Shelf geometry and row estimation](../adr/0003-post-processing-rule.md) defines row/shelf geometry, no-ROI estimation, empty-tier inference, and the optional Store ROI contract.
- The curated `sku110k-shelf-v2` dataset uses deterministic selection with seed `2026` and a committed manifest checksum.
- The pretrained YOLO26s evaluation is a Sprint 1 baseline; the untouched 200-image test split remains reserved for the later final evaluation.

## 7. Risks and issues

| ID | Description | Impact (H/M/L) | Likelihood (H/M/L) | Mitigation | Owner | Status |
|---|---|---:|---:|---|---|---|
| R1 | CPU baseline latency was measured on images larger than the NFR-03 longest-edge limit. | H | M | Re-run latency with longest edge `<=1920 px`; compare single-pass and tiled inference. | Nguyên / Phú | Open |
| R2 | Pretrained COCO semantics do not fully match the single-class retail-product definition in SKU-110K. | H | H | Fine-tune YOLO26s on `sku110k-shelf-v2` and evaluate against the held-out test split. | Phú | Open |
| R3 | Center-y row grouping and geometry heuristics may fail on stacked/depth-ambiguous or non-standard displays. | M | M | Keep representative failure cases, refine post-processing in Sprint 2, and document limits in evaluation. | Phú | Open |
| R4 | PostgreSQL is the selected Sprint 2 storage direction but runtime integration is not implemented yet. | H | M | Implement database models/migrations, Compose service, health behavior, and integration tests. | Nguyên | Open |
| R5 | The gap test split must remain untouched while thresholds are tuned. | H | L | Tune only on the 30-image `valid` split and use the 30-image `test` split only for final NFR-02 reporting. | Phú / Nguyên | Controlled |

## 8. Retrospective

**Keep:** Review documentation as code, use deterministic manifests and checksums, preserve the untouched test split, and align the ML/backend JSON contract before implementation.

**Fix:** Make scope boundaries and runtime-vs-documentation decisions explicit earlier; keep shared-branch iterations clearly linked to the final merged PR.

**Actions:** Add an acceptance checklist to each Sprint 2 PR, record dependencies between API/persistence/post-processing issues, and confirm annotation/metric conventions before tuning on evaluation data.

## 9. Next sprint plan

**Goal:** Deliver the walking skeleton from image upload through detector, post-processing, persistence, and a Dockerized API response.

**Committed issues:**

- [#40 – Implement `POST /v1/analyze` and `GET /health`](https://github.com/mliotlab/task_grp_intern261/issues/40)
- [#41 – Persist analysis history and alert records in PostgreSQL](https://github.com/mliotlab/task_grp_intern261/issues/41)
- [#42 – Implement post-processing v1](https://github.com/mliotlab/task_grp_intern261/issues/42)
- [#43 – Set up Docker Compose and CI smoke test](https://github.com/mliotlab/task_grp_intern261/issues/43)
- [#44 – Update Design Doc to v1](https://github.com/mliotlab/task_grp_intern261/issues/44)
- [#46 – Run the first YOLO fine-tuning experiment](https://github.com/mliotlab/task_grp_intern261/issues/46)
- [#47 – Write Sprint 2 ADRs and WSR-S2](https://github.com/mliotlab/task_grp_intern261/issues/47)

## 10. Help needed from mentor

- Confirm the final no-detection policy (`fill_rate`, alert behavior, and `reason = "no_detection"`).
- Confirm the post-processing/row-geometry decisions in ADR-0002 and ADR-0003, especially for stacked or non-standard displays.
- Confirm the NFR-03 latency protocol using images with longest edge `<=1920 px`.
- Confirm that the 30-image `test` gap set remains held out for final NFR-02 reporting.
