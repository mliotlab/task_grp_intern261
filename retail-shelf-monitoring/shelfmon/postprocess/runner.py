"""End-to-end pure-Python post-processing orchestrator (ADR-0002 & ADR-0003)."""

from __future__ import annotations

import numpy as np

from shelfmon.alert import determine_alert_reason, should_alert
from shelfmon.postprocess.fill_rate import image_fill_rate, row_fill_rate
from shelfmon.postprocess.filtering import (
    clamp_boxes,
    filter_by_confidence,
    filter_geometric_outliers,
)
from shelfmon.postprocess.gaps import find_gaps, merge_intervals
from shelfmon.postprocess.roi import StoreROI
from shelfmon.postprocess.rows import estimate_shelf_rows
from shelfmon.postprocess.types import PostprocessConfig, PostprocessOutput
from shelfmon.schemas import BoundingBox, Gap, ShelfRow


def _v_overlap_ratio(a_y1: float, a_y2: float, b_y1: float, b_y2: float) -> float:
    min_h = min(a_y2 - a_y1, b_y2 - b_y1)
    if min_h <= 0.0:
        return 0.0
    return max(0.0, min(a_y2, b_y2) - max(a_y1, b_y1)) / min_h


def _h_iou_1d(a: Gap, b: Gap) -> float:
    inter = max(0.0, min(a.x2, b.x2) - max(a.x1, b.x1))
    if inter <= 0.0:
        return 0.0
    union = a.width + b.width - inter
    return inter / union if union > 0.0 else 0.0


def _filter_covered_gaps(
    gaps: list[Gap],
    boxes: list[BoundingBox],
    v_overlap_thresh: float,
    max_coverage: float,
) -> list[Gap]:
    """Drop candidate gaps heavily overlapped by actual product detections."""
    if not gaps or not boxes:
        return gaps

    clean: list[Gap] = []
    for gap in gaps:
        occ_spans = [
            (max(gap.x1, b.x1), min(gap.x2, b.x2))
            for b in boxes
            if b.x2 > gap.x1
            and b.x1 < gap.x2
            and _v_overlap_ratio(b.y1, b.y2, gap.y1, gap.y2) >= v_overlap_thresh
        ]
        covered = sum(x2 - x1 for x1, x2 in merge_intervals(occ_spans))
        if (covered / gap.width) < max_coverage:
            clean.append(gap)
    return clean


def _deduplicate_row_gaps(rows: list[ShelfRow]) -> None:
    """Remove duplicate gaps emitted across vertically overlapping sub-rows."""
    indexed: list[tuple[int, Gap]] = [
        (row_idx, gap) for row_idx, row in enumerate(rows) for gap in row.gaps
    ]
    if len(indexed) < 2:
        return

    # Keep larger (more complete) gap when two gaps describe the same physical empty region
    indexed.sort(key=lambda item: -(item[1].width * item[1].height))
    kept_by_row: dict[int, list[Gap]] = {i: [] for i in range(len(rows))}
    kept_all: list[Gap] = []

    for row_idx, gap in indexed:
        is_dup = any(
            _v_overlap_ratio(gap.y1, gap.y2, other.y1, other.y2) >= 0.5
            and _h_iou_1d(gap, other) >= 0.5
            for other in kept_all
        )
        if not is_dup:
            kept_all.append(gap)
            kept_by_row[row_idx].append(gap)

    for row_idx, row in enumerate(rows):
        row.gaps = sorted(kept_by_row[row_idx], key=lambda g: (g.x1, g.x2))


def run_postprocess(
    boxes: list[BoundingBox],
    image_width: float,
    image_height: float,
    *,
    config: PostprocessConfig | None = None,
    roi: StoreROI | None = None,
) -> PostprocessOutput:
    """Run the complete ADR-0003 + ADR-0002 post-processing stage on original-image boxes.

    Performs zero file or network I/O.
    Steps:
      1. Confidence threshold filtering & optional clamping to image canvas.
      2. Geometric outlier filtering (degenerate boxes / price-tag slivers).
      3. Shelf & row geometry estimation via Store ROI (FR-10) or rule-based deskewing,
         stacked-column consolidation, parallelogram/local framing & ``Δy`` empty-tier inference.
      4. Per-row empty-gap detection using local 4–5 neighbor median width, cross-row
         occupancy guard, deduplication, and full-row empty-tier gaps (ADR-0002 §1–§2).
      5. Row-level and overall image fill-rate calculation & alert policy (ADR-0002 §3).
    """
    cfg = config or PostprocessConfig()

    # 1. Confidence filtering and coordinate clamping
    conf_boxes = filter_by_confidence(boxes, cfg.conf_threshold)
    if cfg.clamp_to_image and image_width > 0 and image_height > 0:
        conf_boxes = clamp_boxes(conf_boxes, image_width, image_height)

    # 2. Geometric outlier removal (never enforces a hard min_boxes_per_row cutoff)
    if cfg.enable_outlier_filter:
        filtered = filter_geometric_outliers(
            conf_boxes,
            min_side_px=cfg.min_box_side_px,
            min_height_ratio=cfg.min_height_ratio,
            max_height_ratio=cfg.max_height_ratio,
            min_area_ratio=cfg.min_area_ratio,
            min_boxes_for_stats=cfg.outlier_min_boxes,
        )
    else:
        filtered = list(conf_boxes)

    # 3. Mode switch: Store ROI vs Rule-based estimation (ADR-0003 §5)
    if roi is not None:
        geometry = roi.assign_boxes_to_rows(
            filtered,
            image_width=image_width,
            image_height=image_height,
        )
        active_boxes = [b for region in geometry.regions for b in region.row.boxes]
        mask_pool = active_boxes
    else:
        geometry = estimate_shelf_rows(
            filtered,
            image_width=image_width,
            image_height=image_height,
            config=cfg,
        )
        active_boxes = filtered
        mask_pool = conf_boxes

    shelf_median_width = float(np.median([b.width for b in active_boxes])) if active_boxes else None

    # 4 & 5. Per-row gap detection and fill-rate calculation
    use_local_y = cfg.use_local_gap_y and geometry.mode == "rule"
    for region in geometry.regions:
        row = region.row
        if cfg.enable_cross_row_mask and geometry.mode == "rule" and row.boxes:
            overlapping = [
                b
                for b in mask_pool
                if _v_overlap_ratio(b.y1, b.y2, row.y1, row.y2) >= cfg.cross_row_v_overlap
            ]
            row_for_gap = ShelfRow(
                index=row.index,
                y1=row.y1,
                y2=row.y2,
                boxes=overlapping or row.boxes,
            )
        else:
            row_for_gap = row

        raw_gaps = find_gaps(
            row_for_gap,
            shelf_x1=region.x1,
            shelf_x2=region.x2,
            width_multiplier=cfg.gap_width_multiplier,
            neighbor_count=cfg.neighbor_count,
            shelf_median_width=(shelf_median_width if cfg.single_box_use_shelf_median else None),
            use_local_y=use_local_y,
            image_height=image_height if image_height > 0 else None,
        )
        if cfg.enable_cross_row_mask and geometry.mode == "rule" and row.boxes:
            row.gaps = _filter_covered_gaps(
                raw_gaps,
                mask_pool,
                v_overlap_thresh=cfg.cross_row_v_overlap,
                max_coverage=cfg.max_gap_product_coverage,
            )
        else:
            row.gaps = raw_gaps
        row.fill_rate = row_fill_rate(row, region.x1, region.x2)

    rows = geometry.rows
    if cfg.deduplicate_gaps and geometry.mode == "rule":
        _deduplicate_row_gaps(rows)

    all_gaps = [gap for row in rows for gap in row.gaps]
    overall_fill = image_fill_rate(rows)
    reason = determine_alert_reason(
        fill_rate=overall_fill,
        row_count=len(rows),
        threshold=cfg.fill_rate_alert_threshold,
    )
    is_alert = reason is not None or should_alert(overall_fill, cfg.fill_rate_alert_threshold)

    return PostprocessOutput(
        boxes=active_boxes,
        rows=rows,
        gaps=all_gaps,
        fill_rate=overall_fill,
        alert=is_alert,
        alert_reason=reason,
        geometry=geometry,
    )
