# ADR-0003: Post-processing shelf geometry and row estimation rule

**Status:** Proposed · **Date:** 22/11/2026 · **Deciders:** Phạm Minh Phú, Trần Tất Nguyên, Lê Trần Tấn Phát (mentor)

## Context

The object detector produces only axis-aligned product `BoundingBox` predictions (`x1, y1, x2, y2, confidence, label`) in original-image pixel coordinates; it does not directly detect shelf bars, empty gaps, or shelf boundaries. In real retail photos and SKU-110K images, shelves often suffer from:

1. Slight camera roll/tilt so product rows do not lie strictly horizontal (`y = const`).
2. Background clutter (aisles, walls, adjacent racks) outside the target shelf, or shelves that overflow and clip at image boundaries.
3. Partial occlusion or sparse rows where only 1–2 products remain.
4. Completely empty middle shelf tiers (`0` products detected on that tier).

Before gap detection and fill-rate calculation ([ADR-0002](0002-gap-detection-rule.md)) can execute, post-processing must establish reliable shelf and per-row coordinate boundaries — and switch seamlessly to an explicit per-store Region of Interest (ROI) when fixed-camera configuration is available (FR-10).

## Options considered

1. **Full image width `[0, W]` + naive `center_y` row clustering + hard `min_boxes_per_row` cutoff**
   - *Pros:* Minimal code.
   - *Cons:* Generates false edge gaps when background/aisles appear; splits tilted rows into fragments; drops sparse rows with 1–2 remaining products (hiding severe out-of-stock tiers); cannot infer completely empty middle tiers.
2. **Rule-based deskewed parallelogram shelf framing + `Δy` empty-tier inference, with direct switch to Store ROI (`shelf_bbox` + `row_lines`) when configured**
   - *Pros:* Adapts to camera tilt, clipped/occluded shelves, sparse rows, and empty middle tiers; keeps the `ShelfRow` and `Gap(x1, y1, x2, y2)` Pydantic contract unchanged; cleanly transitions to exact tier bounds when Store ROI is configured.
   - *Cons:* In no-ROI mode, outer shelf framing relies on outermost visible products (effectively the shelf corners) and cannot observe completely empty top-most or bottom-most tiers.

## Decision

Adopt **Option 2**. Post-processing geometry estimation operates in two mutually exclusive modes — **Store ROI mode** (when a store ROI is configured) and **Rule-based estimation mode** (default when no ROI exists) — producing a uniform list of `ShelfRow` regions ordered top-to-bottom with continuous sequential `row_index` (`0, 1, ..., N-1`).

### 1. Pre-clustering box filtering

1. Keep detections with `confidence >= CONF_THRESHOLD` (default `0.25`).
2. Filter extreme geometric outliers before row clustering (e.g., degenerate boxes or tiny false positives such as price tags whose height or area falls far below the image's median product dimensions), rather than discarding sparse rows via a hard `min_boxes_per_row` cutoff.
   - *Rationale:* A shelf tier with only 1–2 valid products remaining is a critical low-stock case and must remain a valid `ShelfRow`.
   - *Compatibility:* Pure `group_into_rows(boxes)` keeps support for small synthetic unit-test inputs (e.g., 2-box overlap tests); outlier filtering runs as an explicit configurable step in the pipeline.

### 2. Rule-based shelf & row estimation (no-ROI mode)

When no Store ROI is configured for `store_id`:

1. **Initial row clustering:** Group filtered boxes vertically using baseline height-relative `center_y` tolerance (Sprint 2 benchmarks this against 1D vertical DBSCAN). Sort rows top-to-bottom and boxes within each row left-to-right.
2. **Tilt angle estimation & deskewing:**
   - Assuming the physical retail shelf is rectangular, fit linear row centerlines (`y = a_r x + b_r`) across rows containing enough boxes (e.g., `>= 4` products) and compute the median tilt angle `θ = arctan(median(a_r))`.
   - Apply a small deadband (e.g., `|θ| < 1.5°` treated as `0°`) to avoid jitter on near-level photos.
   - If `θ != 0°`, rotate box coordinates by `-θ` into a deskewed coordinate frame `(x', y')` and refine row clustering along `y'`.
3. **Parallelogram shelf envelope:**
   - In the deskewed frame `(x', y')`, define the outer shelf horizontal span from the outermost detected products across all valid rows:
     `shelf_x1' = min(b.x1')`, `shelf_x2' = max(b.x2')`.
   - Map `[shelf_x1', shelf_x2']` at each row's vertical center back into original image coordinates to obtain per-row effective horizontal bounds `[row_x1, row_x2]` (forming a tilted rectangle / parallelogram in image space).
4. **Row vertical bounds (`row_y1`, `row_y2`):**
   - Derive representative row vertical edges using robust statistics (e.g., median `y1` and median `y2`, or interquartile bounds) alongside envelope bounds so a single tall outlier or rotated box does not distort the entire tier height.

### 3. Edge cases: clipped and partially occluded shelves

- **Shelf overflowing image borders:** Strictly clamp all computed row/shelf horizontal bounds `[row_x1, row_x2]` to `[0.0, float(image_width)]` and vertical bounds `[row_y1, row_y2]` to `[0.0, float(image_height)]`. Never extrapolate coordinates outside the visible image canvas.
- **Partially occluded or cropped shelves:** When part of the shelf is blocked (e.g., by a cart, pillar, or person) or cropped out, shelf bounds are anchored strictly by the **outermost visible detected products**. No unobservable off-screen or occluded area is hypothesized in no-ROI mode.

### 4. Empty-tier inference (`Δy` vertical spacing rule)

To avoid ignoring completely empty middle tiers in no-ROI mode:

1. Sort detected occupied rows top-to-bottom: `R_0, R_1, ..., R_{k-1}`.
2. Compute vertical clearance between consecutive rows using robust tier edges:
   `Δy_i = top_edge(R_{i+1}) - bottom_edge(R_i)`.
3. Estimate the characteristic product/tier height `H_ref` (e.g., median height of adjacent rows `R_i, R_{i+1}` or global median row height) and typical center-to-center tier pitch `pitch_ref` from adjacent occupied rows.
4. When `Δy_i > k_v × H_ref` (experimental threshold `k_v`, e.g. `1.1–1.3×`, to be calibrated in Sprint 2–3), estimate the number of missing tiers `m = max(1, round(Δc_i / pitch_ref) - 1)` and insert `m` empty `ShelfRow` entries (`boxes=[]`) spanning the interpolated vertical bands and the parallelogram horizontal bounds `[row_x1, row_x2]` at each inserted tier's `y` position.
5. Re-index all rows sequentially top-to-bottom (`row_index = 0, 1, ..., N-1`) so every physical tier — occupied or inferred empty — receives its ordered row index.

### 5. Minimal Store ROI specification (FR-10) & mode switch

For stores with fixed camera angles, define a minimal configurable ROI per `store_id`:

- **`shelf_bbox`:** Bounding region enclosing the full target shelf unit (axis-aligned `[x1, y1, x2, y2]`, or 4-vertex polygon `[TL, TR, BR, BL]` if the fixed camera has slight tilt).
- **`row_lines`:** Ordered list of `N - 1` divider lines spanning from the left edge to the right edge of `shelf_bbox`, partitioning the shelf into `N` vertical tier bands (`0 .. N-1`).
- **Switching behavior:** When a valid ROI is configured for `store_id`:
  1. Skip heuristic tilt/parallelogram estimation, heuristic row clustering, and `Δy` empty-tier inference.
  2. Keep detections whose centers fall inside `shelf_bbox` and assign each detection to the tier band bounded by consecutive `row_lines` (and top/bottom of `shelf_bbox`).
  3. Emit all `N` ROI rows in sequential order (`row_index = 0..N-1`), including any empty top, middle, or bottom tier (`boxes=[]`), with `[row_x1, row_x2]` and `[row_y1, row_y2]` taken directly from the ROI tier geometry.

### 6. Assumptions and limitations (no-ROI mode)

- **Corner & edge product dependency:** Without an ROI, parallelogram framing depends on products existing at the outermost edges (effectively the four corners of the shelf). If an entire vertical edge column is missing across all tiers, the estimated shelf width contracts to the remaining products.
- **Top-most and bottom-most empty tiers:** The `Δy` vertical-spacing rule can only detect empty tiers sandwiched between two occupied rows. Completely empty top or bottom tiers cannot be detected reliably without `shelf_bbox`.
- **Strong perspective distortion:** Heavy oblique camera angles produce trapezoidal convergence (non-parallel left/right edges) and non-uniform row heights across depth, which exceed the parallelogram assumption; fixed oblique cameras should use Store ROI.
- **Mixed tier heights & double-stacking:** Shelves mixing very tall bottom-tier items with short top-tier items can distort global `H_ref` / `pitch_ref` if not normalized locally between adjacent rows; thresholds (`k_v`) must be validated on representative multi-tier photos before locking defaults.
- **Schema contract:** Downstream `Gap` and `ShelfRow` objects remain axis-aligned (`x1, y1, x2, y2`) per `shelfmon/schemas.py`, using the per-row `[row_x1, row_x2]` bounds computed at that tier's vertical band.

## Consequences

- `ADR-0002` (gap detection & fill rate) consumes a single standardized `ShelfRow` contract regardless of whether rows come from rule-based estimation or Store ROI.
- Sparse tiers (1–2 remaining products), clipped edges, and partially occluded shelves remain analyzable without false off-image gaps.
- Sprint 2–3 evaluation must empirically calibrate geometric outlier bounds and `Δy` (`k_v`) parameters and document failure modes in `EVAL_REPORT.md`.
