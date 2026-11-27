# ADR-0002: Empty-gap detection, fill-rate calculation, and evaluation rules

**Status:** Proposed · **Date:** 25/11/2026 · **Deciders:** Phạm Minh Phú, Trần Tất Nguyên, Lê Trần Tấn Phát (mentor)

## Context

The detector outputs only product bounding boxes (`BoundingBox`), with no separate gap or shelf-divider class. As a result, empty shelf gaps are inferred horizontally along shelf tiers whose bounds are established either by rule-based shelf/row geometry ([ADR-0003](0003-post-processing-rule.md)) or by an explicit Store ROI (`shelf_bbox` + `row_lines`, FR-10).

Three specific mismatches had to be resolved before implementation and NFR-02 labeling:

1. **Product width variation within a row:** Using a single whole-row `mean` box width breaks down when a shelf mixes wide and narrow packages or exhibits mild horizontal perspective variation across the row.
2. **Completely empty rows:** Both `Δy`-inferred empty tiers (ADR-0003) and zero-product ROI tiers must produce consistent `Gap` records and `row_fill_rate = 0.0` while preserving sequential `row_index`.
3. **Evaluation vs. algorithm geometry:** Because the algorithm detects horizontal emptiness per row, strict 2D bounding-box IoU evaluation unfairly penalizes valid gap detections due to vertical (`y1/y2`) labeling differences between human annotators and row-derived heights.

## Options considered

1. **Whole-row mean box width + 2D box IoU evaluation**
   - *Pros:* Simplest arithmetic.
   - *Cons:* Sensitive to mixed product widths and outliers within a row; 2D IoU conflates vertical box-height ambiguity with horizontal gap localization accuracy.
2. **Local 4–5 neighbor `median` product width + unified row bounds + full-row empty-tier gaps + Row-Aligned 1D Horizontal IoU evaluation**
   - *Pros:* Adapts locally to adjacent product sizes, resists width outliers, handles empty tiers identically under rule-based and ROI modes, and evaluates gap localization on the exact horizontal axis the algorithm predicts.
   - *Cons:* Slightly more neighborhood indexing logic and requires a custom matching script (rather than off-the-shelf 2D COCO eval) for NFR-02.

## Decision

Adopt **Option 2**. All gap detection, fill-rate calculations, annotation guidelines, and NFR-02 evaluation metrics operate on the unified per-row regions (`row_index`, `[row_x1, row_x2]`, `[row_y1, row_y2]`, sorted `boxes`) produced by [ADR-0003](0003-post-processing-rule.md) or Store ROI.

### 1. Gap detection within an occupied row (`len(boxes) > 0`)

1. **Horizontal interval merging:** Clip each box's `[x1, x2]` to the effective row bounds `[row_x1, row_x2]` and merge overlapping or touching intervals into sorted, disjoint occupied intervals `I_1, I_2, ..., I_m`.
2. **Candidate free intervals:** Collect all uncovered horizontal spans within `[row_x1, row_x2]`:
   - Left edge span: `[row_x1, I_1.x1]` (when `I_1.x1 > row_x1`).
   - Inter-product spans: `[I_j.x2, I_{j+1}.x1]` for `j = 1 .. m-1`.
   - Right edge span: `[I_m.x2, row_x2]` (when `row_x2 > I_m.x2`).
3. **Local reference width (`median` of 4–5 neighboring products):**
   - For each candidate free interval, select up to **4–5 nearest original product boxes** in the same row (balanced across left and right neighbors for interior spans; nearest 4–5 boxes for left/right edge spans).
   - Measure `local_ref_width = median(b.width for b in neighbor_boxes)` using **original unmerged boxes** so overlapping products do not inflate the reference width.
   - *Sparse-row fallback:* If the row contains fewer than 4 boxes, use the median width of all boxes in that row; if the row has only 1 box, optionally stabilize against the shelf-wide median box width if available.
4. **Threshold rule:** Report a `Gap` whenever:
   `gap_width > GAP_WIDTH_MULTIPLIER * local_ref_width`
   where `GAP_WIDTH_MULTIPLIER` defaults to `1.5` (configurable via settings and tunable on the 30-image `val` gap set in Sprint 2–3).
5. **Gap bounding box coordinates (`Gap`):**
   - Horizontal bounds `(x1, x2)` snap **tightly to the edges of the two adjacent products** (from the right edge of the left product/cluster to the left edge of the right product/cluster) or **to the shelf/row edge** (`row_x1` or `row_x2`) for edge gaps.
   - Vertical bounds `(y1, y2)` align with the vertical span of the neighboring product group / row tier (`[row_y1, row_y2]` or ROI tier boundaries), keeping `Gap(row_index, x1, y1, x2, y2)` compatible with `shelfmon/schemas.py`.

### 2. Completely empty rows (`len(boxes) == 0`)

When a row contains zero products — either inferred as an empty middle tier by the `Δy` vertical-spacing rule ([ADR-0003](0003-post-processing-rule.md)) or defined as an empty tier in Store ROI:

1. Preserve the row's sequential `row_index`.
2. Emit one full-width `Gap` covering the entire row region:
   `Gap(row_index=row.index, x1=row_x1, y1=row_y1, x2=row_x2, y2=row_y2)`.
3. Set `row_fill_rate = 0.0`.

### 3. Fill-rate calculation and no-detection alert policy

1. **Row fill rate:** For each row `r` with `row_x2 > row_x1`:
   $$\text{row\_fill\_rate}(r) = \frac{\sum_{I \in \text{merged\_intervals}(r)} (I.x_2 - I.x_1)}{\text{row\_x}_2 - \text{row\_x}_1}$$
   (Overlapping boxes are counted once; empty rows have `row_fill_rate = 0.0`.) Normal tight inter-product spacing smaller than `1.5 × local_ref_width` is not flagged as a `Gap`, yet is still excluded from occupied coverage so sparse spacing lowers `fill_rate` smoothly rather than artificially reporting `1.0`.
2. **Overall image fill rate:** Arithmetic mean across all rows (including inferred or ROI empty rows):
   $$\text{image\_fill\_rate} = \frac{1}{|R|} \sum_{r \in R} \text{row\_fill\_rate}(r)$$
3. **No-detection policy:** If `len(rows) == 0` (no valid detections and no Store ROI configured), return `fill_rate = 0.0`, set `alert = True` (consistent with `fill_rate < FILL_RATE_ALERT_THRESHOLD`), and persist the alert record with `reason = "no_detection"` (distinct from `"low_fill"`). When Store ROI is active and all `N` tiers have zero detections, `image_fill_rate = 0.0` and `alert = True` as well.

### 4. Gap annotation guidelines and NFR-02 matching criteria

#### Labeled gap dataset & split protocol
- **Status:** Annotation is completed and dataset version **v3** (`2026-11-23`) is finalized on **Roboflow** and exported locally in **COCO JSON** format with **60 images total** (`0 train` / **30 `valid`** with 96 `gap` boxes / **30 `test`** with 111 `gap` boxes; **207 `gap` boxes** total).
- **Dataset reference:**
  - **Roboflow version link:** [RSM v3 — 60 images (`retail-shelf-monitoring-qq6op/rsm-nys2u/3`)](https://app.roboflow.com/retail-shelf-monitoring-qq6op/rsm-nys2u/3) *(keep project private; never commit API keys or redistributed SKU-110K images)*.
  - **Export format & preprocessing:** **COCO JSON** (`valid/_annotations.coco.json`, `test/_annotations.coco.json`; class `gap`, `category_id: 1`; original SKU-110K filenames preserved in `images[].extra.name`). Preprocessing: `Auto-Orient: Applied` (with EXIF-orientation stripping; no resize, original resolution preserved); Augmentations: `None`.
  - **Local artifact layout (git-ignored):** Extracted under `retail-shelf-monitoring/data/gap_eval/roboflow_v3/` (explicitly ignored via `retail-shelf-monitoring/.gitignore` and documented in [`../../data/README.md`](../../data/README.md)). If annotations are later shared inside the repo, commit only stripped annotations/manifests without image binaries so evaluation reuses local `data/sku110k_subset/images/{val,test}/`.
- **Usage plan (preventing test leakage):**
  - **`val` (30 images):** Used exclusively to refine post-processing rules and tune hyperparameters (e.g., `GAP_WIDTH_MULTIPLIER`, outlier filters, `Δy` empty-tier multiplier `k_v`).
  - **`test` (30 images):** Strictly held out during tuning and used solely to report final NFR-02 gap Precision and Recall in `EVAL_REPORT.md` (satisfies the `>= 30` evaluation-image requirement).

#### Annotation guidelines
- **Empty-space criterion:** Annotate each significant empty shelf space as an axis-aligned bounding box (`gap`) wide enough to accommodate roughly `>= 1.5` typical adjacent products on that tier.
- **Horizontal bounds (`x1, x2`):** Both left and right edges of the bounding box must snap tightly against the facing edges of the two adjacent products (from the right edge of the left product to the left edge of the right product), or flush against the **image edge** (or outer shelf boundary when the shelf ends inside the frame) for missing row ends.
- **Vertical bounds (`y1, y2`):** The bottom edge (`y2`) must touch the actual shelf-row base (the surface / baseline where actual products sit; vertically stacked / double-stacked product cases are ignored), and the top edge (`y1`) must touch the underside (bottom edge) of the upper shelf. Anchoring `y1` to the upper shelf underside gives annotators an unambiguous visual reference without penalizing predicted row-height boxes, because the NFR-02 vertical check evaluates **overlap only** as a binary tier-alignment gate rather than scoring vertical box tightness.
- **Recessed / deep-shelf products:** When products are pushed back deeper inside the shelf, if the recessed product is visible enough to be seen in the image, do **not** label the front opening as a `gap`. Label as a `gap` only when no product is visible in that space.
- **Empty-tier annotations:** Completely empty middle tiers (and any empty tier inside a known ROI) are labeled as full-row gaps spanning the shelf width. Completely empty top-most or bottom-most tiers on no-ROI images should be tagged separately (or isolated in `EVAL_REPORT.md` error analysis) because no-ROI geometry cannot observe tiers outside the topmost/bottommost products.

#### Matching rule for NFR-02 (`Precision >= 0.70`, `Recall >= 0.70`)
Evaluate predicted gaps against ground-truth gap boxes on the held-out **30-image `test` split** (after tuning on the **30-image `val` split**) using **Row-Aligned 1D Horizontal IoU**:

1. **Vertical tier alignment check (overlap-only gate, unscored):** A predicted gap `G_p` and ground-truth gap `G_gt` match vertically only if:
   $$\frac{\max(0, \min(G_p.y_2, G_{gt}.y_2) - \max(G_p.y_1, G_{gt}.y_1))}{\min(G_p.\text{height}, G_{gt}.\text{height})} \ge 0.5$$
2. **1D Horizontal IoU check:** Among vertically aligned pairs, compute 1D IoU along the `x`-axis:
   $$\text{IoU}_x(G_p, G_{gt}) = \frac{\text{intersection}_x(G_p, G_{gt})}{\text{union}_x(G_p, G_{gt})} \ge 0.5$$
3. Match predictions to ground-truth boxes 1-to-1 greedily in descending order of `IoU_x` to compute overall gap Precision and Recall.

## Consequences

- Gap thresholds adapt locally across mixed product sizes and mild horizontal perspective, while `GAP_WIDTH_MULTIPLIER` remains configurable for Sprint 2–3 tuning on the 30-image `val` gap split, with final NFR-02 metrics reported on the held-out 30-image `test` split.
- Both rule-based estimation (`ADR-0003`) and Store ROI (`FR-10`) share the exact same gap and fill-rate implementation.
- Existing Pydantic schemas (`Gap`, `ShelfRow`, `AnalysisResult` in `shelfmon/schemas.py`) and synthetic-box unit tests (`tests/unit/test_postprocess.py`) remain valid without breaking contract changes.
- NFR-02 evaluation metrics accurately measure horizontal gap localization and tier assignment without false penalties from minor vertical annotation differences.
