# `shelfmon/postprocess` — Shelf Geometry, Gap Detection & Fill Rate

Pure-Python + NumPy post-processing stage (no model weights, no DB/network I/O). Implements [ADR-0003](../../docs/adr/0003-post-processing-rule.md) (shelf/row geometry & Store ROI) and [ADR-0002](../../docs/adr/0002-gap-detection-rule.md) (local-width gap detection, fill rates, and NFR-02 evaluation).

## File Map

| File | Responsibility | Algorithm / Spec |
|---|---|---|
| `runner.py` | End-to-end pure orchestrator (`run_postprocess`) connecting filtering → ROI/rule geometry → gap detection → cross-row guard & deduplication → fill rates & alert reason. | ADR-0002 + ADR-0003 |
| `types.py` | `PostprocessConfig` (all tunable thresholds + `from_settings`), internal geometry carriers (`RowRegion`, `ShelfGeometry`), and `PostprocessOutput`. Keeps per-row `[x1, x2]` bounds internal so API `ShelfRow` JSON stays unchanged. | DESIGN.md §3, §5 |
| `filtering.py` | `filter_by_confidence`, `clamp_boxes` (to `[0, W] × [0, H]`), `rescale_boxes` (resized → original pixels), and `filter_geometric_outliers` (drops tiny price-tag slivers / degenerate boxes without enforcing a hard `min_boxes_per_row`). | ADR-0003 §1, DESIGN.md §3 |
| `rows.py` | Rule-based no-ROI shelf localization (`estimate_shelf_rows`, `group_into_rows`): aspect-aware vertical stack consolidation, `center_y` or `dbscan_1d` clustering + vertical-overlap merging, 2-pass tilt estimation (`|θ| < 1.5°` deadband) & deskewing, per-row horizontal framing (`neighbor_median` / `outer_products` / `row_extent` / `image_width`), and periodic-pitch `Δy` empty-tier inference. | ADR-0003 §2–§4 |
| `roi.py` | Fixed-camera `StoreROI` (`shelf_bbox` rect or 4-vertex polygon + `row_lines` horizontal or slanted dividers). When configured for a `store_id`, skips heuristic clustering/deskew/empty-tier inference and assigns boxes directly to all `N` ROI tiers. | ADR-0003 §5 (FR-10) |
| `gaps.py` | `merge_intervals` and `find_gaps`: clips/merges occupied `x`-intervals per row, selects 4–5 nearest **original** unmerged boxes around each free span (balanced left/right for interior, nearest for edges, shelf-median fallback for 1-box rows), flags spans `> k × local_median_width`, and emits full-width gaps for empty tiers. | ADR-0002 §1–§2 |
| `fill_rate.py` | `row_fill_rate` (merged occupied width / effective row width, `0.0` for empty rows) and `image_fill_rate` (arithmetic mean across all rows, `0.0` when `0` rows). | ADR-0002 §3 |
| `visualize.py` | In-memory `draw_annotations` (FR-02): renders green product boxes, red semi-transparent gaps (`α = 0.35`), optional shelf polygon, row fill rates, and top-left HUD/alert banner on a copy of the original image. | DESIGN.md §3, FR-02 |

## Algorithm Summary (Rule-Based No-ROI Mode)

1. **Filter & clamp:** Drop boxes `< conf_threshold`, clamp to `[0, W] × [0, H]`, and remove extreme size outliers once `>= outlier_min_boxes` detections exist.
2. **Row localization & deskewing:**
   - Merge directly stacked same-column boxes into atomic stack units so multi-layer flat packs (e.g., stacked toothpaste boxes) stay on one physical tier.
   - Cluster vertically (`center_y` or `dbscan_1d`) and merge vertically overlapping sub-rows (`row_v_merge_threshold`) to prevent short products next to tall bottles from spawning ghost sub-rows.
   - Fit median row-centerline slope across rows with `>= 4` units; if `1.5° <= |θ| <= 20°`, deskew with a 2-pass refinement and re-cluster in `(x', y')`.
   - Compute per-row horizontal bounds `[row_x1, row_x2]` clamped to `[0, W]` using `shelf_bound_mode`:
     - `neighbor_median` *(default)*: median left/right extent of `[r-1, r, r+1]` (preserves single-row edge gaps while resisting multi-row posters / offset adjacent bays).
     - `outer_products`: ADR-0003 global parallelogram `[min x1', max x2']` mapped per row.
     - `row_extent`: interior-only (`[min x1, max x2]` of each row; highest precision without Store ROI, skips edge gaps).
     - `image_width`: full `[0, W]`.
   - Infer sandwiched empty middle tiers only when both clearance `Δy > empty_tier_kv × H_ref` and center pitch `Δc >= 1.75 × pitch_ref` (40th-percentile shelf pitch).
3. **Gap detection & occupancy guards:**
   - Detect candidate free spans per row (`gap_width > gap_width_multiplier × local_median_width`).
   - Suppress any candidate span heavily covered (`>= 30%` width) by vertically overlapping detections from neighboring rows (`enable_cross_row_mask`), and deduplicate overlapping gaps across rows.
4. **Fill rate & alert:**
   - `row_fill_rate = union_occupied_x / (row_x2 - row_x1)`, `image_fill_rate = mean(row_fill_rate)`.
   - Zero rows → `fill_rate = 0.0`, `alert = True`, `alert_reason = "no_detection"`.
