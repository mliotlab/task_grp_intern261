"""Deterministic unit tests for ADR-0002 & ADR-0003 post-processing, ROI, visuals, and pipeline."""

from __future__ import annotations

import math

import numpy as np
import pytest
from pydantic import ValidationError

from shelfmon.alert import determine_alert_reason, should_alert
from shelfmon.config import Settings
from shelfmon.inference.detector import FakeDetector
from shelfmon.pipeline import analyze_image
from shelfmon.postprocess import (
    PostprocessConfig,
    StoreROI,
    clamp_boxes,
    draw_annotations,
    estimate_shelf_rows,
    filter_by_confidence,
    filter_geometric_outliers,
    find_gaps,
    group_into_rows,
    image_fill_rate,
    merge_intervals,
    rescale_boxes,
    row_fill_rate,
    run_postprocess,
)
from shelfmon.schemas import AnalysisResult, BoundingBox, Gap, ShelfRow


def _make_row_boxes(
    y1: float,
    y2: float,
    xs: list[tuple[float, float]],
    conf: float = 0.9,
) -> list[BoundingBox]:
    return [BoundingBox(x1=a, y1=y1, x2=b, y2=y2, confidence=conf) for a, b in xs]


# ---------------------------------------------------------------------------
# Baseline FR-03 / FR-04 tests (originally scaffolded in test_postprocess.py)
# ---------------------------------------------------------------------------


def test_groups_boxes_into_two_rows(two_row_shelf: list[BoundingBox]) -> None:
    rows = group_into_rows(two_row_shelf)
    assert [len(r.boxes) for r in rows] == [7, 10]
    assert rows[0].y1 < rows[1].y1
    assert [r.index for r in rows] == [0, 1]
    for row in rows:
        xs = [b.x1 for b in row.boxes]
        assert xs == sorted(xs)


def test_empty_input_gives_no_rows() -> None:
    assert group_into_rows([]) == []


def test_finds_the_single_gap(two_row_shelf: list[BoundingBox]) -> None:
    rows = group_into_rows(two_row_shelf)
    gaps = find_gaps(rows[0], shelf_x1=0, shelf_x2=1000, width_multiplier=1.5)
    assert len(gaps) == 1
    assert (gaps[0].x1, gaps[0].x2) == (400, 700)
    assert gaps[0].row_index == 0
    assert find_gaps(rows[1], 0, 1000, 1.5) == []


def test_fill_rates(two_row_shelf: list[BoundingBox]) -> None:
    rows = group_into_rows(two_row_shelf)
    assert row_fill_rate(rows[0], 0, 1000) == pytest.approx(0.7)
    assert row_fill_rate(rows[1], 0, 1000) == pytest.approx(1.0)
    assert 0.7 <= image_fill_rate(rows) <= 1.0


def test_overlapping_boxes_are_not_double_counted() -> None:
    boxes = [
        BoundingBox(x1=0, y1=0, x2=60, y2=10),
        BoundingBox(x1=40, y1=0, x2=100, y2=10),
    ]
    (row,) = group_into_rows(boxes)
    assert row_fill_rate(row, 0, 200) == pytest.approx(0.5)


def test_no_rows_means_zero_fill_rate() -> None:
    assert image_fill_rate([]) == 0.0


# ---------------------------------------------------------------------------
# Pre-clustering filtering & coordinate contract (ADR-0003 §1, DESIGN.md §3)
# ---------------------------------------------------------------------------


def test_rescale_boxes_restores_original_coordinates() -> None:
    boxes = [BoundingBox(x1=50, y1=100, x2=150, y2=200, confidence=0.85)]
    scaled = rescale_boxes(boxes, from_size=(500, 1000), to_size=(1000, 2000))
    assert len(scaled) == 1
    assert (scaled[0].x1, scaled[0].y1, scaled[0].x2, scaled[0].y2) == (100.0, 200.0, 300.0, 400.0)
    assert scaled[0].confidence == pytest.approx(0.85)


def test_rescale_boxes_rejects_non_positive_dims() -> None:
    with pytest.raises(ValueError, match="positive"):
        rescale_boxes([], from_size=(0, 100), to_size=(100, 100))


def test_clamp_boxes_drops_off_canvas_boxes() -> None:
    boxes = [
        BoundingBox(x1=-20, y1=-10, x2=50, y2=80),
        BoundingBox(x1=120, y1=10, x2=150, y2=80),
    ]
    clamped = clamp_boxes(boxes, image_width=100, image_height=100)
    assert len(clamped) == 1
    assert (clamped[0].x1, clamped[0].y1, clamped[0].x2, clamped[0].y2) == (0.0, 0.0, 50.0, 80.0)
    assert clamp_boxes(boxes, image_width=0, image_height=100) == []


def test_filter_geometric_outliers_removes_price_tags_and_giant_boxes() -> None:
    normal = _make_row_boxes(
        100,
        200,
        [(i * 100, (i + 1) * 100) for i in range(8)],
    )
    price_tag = BoundingBox(x1=50, y1=205, x2=65, y2=215)  # h=10 (0.1x), area=150 (0.015x)
    giant_box = BoundingBox(x1=0, y1=0, x2=200, y2=950)  # h=950 (9.5x)
    kept = filter_geometric_outliers(
        [*normal, price_tag, giant_box],
        min_height_ratio=0.12,
        max_height_ratio=8.0,
        min_area_ratio=0.02,
    )
    assert len(kept) == 8
    assert price_tag not in kept
    assert giant_box not in kept


def test_sparse_rows_with_one_or_two_boxes_are_preserved() -> None:
    """ADR-0003 §1: never drop sparse rows (1-2 products) via a min_boxes_per_row cutoff."""
    row0 = _make_row_boxes(100, 200, [(100, 200)])
    row1 = _make_row_boxes(260, 360, [(100, 200), (800, 900)])
    row2 = _make_row_boxes(420, 520, [(i * 100, (i + 1) * 100) for i in range(10)])
    rows = group_into_rows(row0 + row1 + row2)
    assert [len(r.boxes) for r in rows] == [1, 2, 10]


# ---------------------------------------------------------------------------
# Tilt estimation, deskewing, stacked tiers & empty tiers (ADR-0003 §2-§4)
# ---------------------------------------------------------------------------


def test_tilted_shelf_deskewing_recovers_rows_and_angle() -> None:
    """A 6-degree tilted 2-row shelf should be deskewed cleanly without fragmenting rows."""
    angle_deg = 6.0
    slope = math.tan(math.radians(angle_deg))
    boxes: list[BoundingBox] = []
    for base_y in (200.0, 320.0):
        for i in range(10):
            cx = 100.0 + i * 100.0
            cy = base_y + slope * (cx - 550.0)
            boxes.append(BoundingBox(x1=cx - 45, y1=cy - 45, x2=cx + 45, y2=cy + 45))

    geom = estimate_shelf_rows(boxes, image_width=1200, image_height=800)
    assert abs(geom.tilt_deg - angle_deg) < 0.5
    assert len(geom.regions) == 2
    assert [len(r.row.boxes) for r in geom.regions] == [10, 10]
    assert geom.shelf_polygon is not None
    assert len(geom.shelf_polygon) == 4


def test_small_tilt_within_deadband_is_treated_as_zero() -> None:
    angle_deg = 0.8
    slope = math.tan(math.radians(angle_deg))
    boxes = [
        BoundingBox(
            x1=100 + i * 100,
            y1=200 + slope * (i * 100) - 40,
            x2=190 + i * 100,
            y2=200 + slope * (i * 100) + 40,
        )
        for i in range(8)
    ]
    geom = estimate_shelf_rows(boxes, image_width=1000, image_height=500)
    assert geom.tilt_deg == 0.0


def test_clipped_shelf_bounds_are_strictly_clamped_to_canvas() -> None:
    """ADR-0003 §3: never extrapolate shelf/row bounds outside [0, W] x [0, H]."""
    angle_deg = 8.0
    slope = math.tan(math.radians(angle_deg))
    boxes = []
    for base_y in (80.0, 720.0):
        for i in range(10):
            cx = 50.0 + i * 100.0
            cy = max(40.0, min(760.0, base_y + slope * (cx - 500.0)))
            boxes.append(
                BoundingBox(
                    x1=max(0.0, cx - 48),
                    y1=cy - 35,
                    x2=min(1000.0, cx + 48),
                    y2=cy + 35,
                )
            )

    geom = estimate_shelf_rows(boxes, image_width=1000, image_height=800)
    for reg in geom.regions:
        assert 0.0 <= reg.x1 <= reg.x2 <= 1000.0
        assert 0.0 <= reg.y1 <= reg.y2 <= 800.0


def test_short_box_on_same_shelf_does_not_create_ghost_row() -> None:
    """A shorter item sitting on the same shelf plank as tall bottles stays in the same row."""
    tall = _make_row_boxes(100, 300, [(i * 100, (i + 1) * 100) for i in range(8) if i != 3])
    short = [BoundingBox(x1=300, y1=220, x2=400, y2=300, confidence=0.9)]
    out = run_postprocess(tall + short, image_width=800, image_height=400)
    assert len(out.rows) == 1
    assert out.gaps == []
    assert out.fill_rate == pytest.approx(1.0)


def test_double_stacked_flat_packs_consolidate_into_one_tier() -> None:
    """Flat toothpaste-style packs stacked 3-high on one shelf tier produce 1 row, not 3."""
    boxes: list[BoundingBox] = []
    # Tier 0: 3 stacked layers of flat boxes (w=180, h=50) touching vertically at y=100..250
    for layer in range(3):
        y1 = 100.0 + layer * 50.0
        for col in range(5):
            if col == 2:
                continue  # 180px interior gap across whole stack
            boxes.append(BoundingBox(x1=col * 180, y1=y1, x2=(col + 1) * 180, y2=y1 + 50))
    # Tier 1: separated by 90px shelf bar at y=340..490 (completely full)
    for layer in range(3):
        y1 = 340.0 + layer * 50.0
        for col in range(5):
            boxes.append(BoundingBox(x1=col * 180, y1=y1, x2=(col + 1) * 180, y2=y1 + 50))

    cfg = PostprocessConfig(gap_width_multiplier=0.9)
    out = run_postprocess(boxes, image_width=900, image_height=600, config=cfg)
    assert len(out.rows) == 2
    assert len(out.gaps) == 1
    assert (out.gaps[0].x1, out.gaps[0].x2) == pytest.approx((360.0, 540.0))


def test_uniform_tall_headroom_does_not_hallucinate_empty_tiers() -> None:
    """Shelves with tall headroom above every short-item row must not trigger empty tiers."""
    boxes: list[BoundingBox] = []
    for tier in range(5):
        y1 = 50.0 + tier * 240.0  # h=60, headroom=180 -> identical pitch=240 on every tier
        boxes.extend(_make_row_boxes(y1, y1 + 60.0, [(i * 100, (i + 1) * 100) for i in range(8)]))

    out = run_postprocess(boxes, image_width=800, image_height=1300)
    assert len(out.rows) == 5
    assert out.gaps == []
    assert out.fill_rate == pytest.approx(1.0)


def test_empty_middle_tier_inference_and_sequential_indexing() -> None:
    """ADR-0003 §4 & ADR-0002 §2: sandwiched empty middle tier gets full-row gap & fill_rate=0."""
    # 4-tier shelf: tier 0 occupied (100..200), tier 1 EMPTY, tier 2 (380..480), tier 3 (520..620)
    row0 = _make_row_boxes(100, 200, [(100 + i * 80, 180 + i * 80) for i in range(8)])
    row2 = _make_row_boxes(380, 480, [(100 + i * 80, 180 + i * 80) for i in range(8)])
    row3 = _make_row_boxes(520, 620, [(100 + i * 80, 180 + i * 80) for i in range(8)])

    out = run_postprocess(row0 + row2 + row3, image_width=900, image_height=700)
    assert len(out.rows) == 4
    assert [r.index for r in out.rows] == [0, 1, 2, 3]
    empty_row = out.rows[1]
    assert empty_row.boxes == []
    assert empty_row.fill_rate == 0.0
    assert len(empty_row.gaps) == 1
    assert empty_row.gaps[0].row_index == 1
    assert (empty_row.gaps[0].x1, empty_row.gaps[0].x2) == (100.0, 740.0)
    assert out.fill_rate == pytest.approx(0.75)
    assert out.alert is True
    assert out.alert_reason == "low_fill"


def test_dbscan_1d_clustering_matches_clean_multi_row_shelf(
    two_row_shelf: list[BoundingBox],
) -> None:
    cfg = PostprocessConfig(clustering_method="dbscan_1d")
    rows = group_into_rows(two_row_shelf, config=cfg)
    assert [len(r.boxes) for r in rows] == [7, 10]


def test_neighbor_median_resists_multi_row_poster_while_catching_single_row_edge_gap() -> None:
    """Neighbor-median shelf framing avoids poster edge FPs while keeping real edge gaps."""
    # Row 0: [0, 1000] (top full)
    # Row 1: [0, 700]  (rows 1-4 all end at 700 due to a right-side poster panel!)
    # Row 2: [0, 400]  (genuine missing right edge [400, 700] compared to neighbors 1 & 3!)
    # Row 3: [0, 700]
    row0 = _make_row_boxes(50, 150, [(i * 100, (i + 1) * 100) for i in range(10)])
    row1 = _make_row_boxes(200, 300, [(i * 100, (i + 1) * 100) for i in range(7)])
    row2 = _make_row_boxes(350, 450, [(i * 100, (i + 1) * 100) for i in range(4)])
    row3 = _make_row_boxes(500, 600, [(i * 100, (i + 1) * 100) for i in range(7)])

    cfg = PostprocessConfig(shelf_bound_mode="neighbor_median", gap_width_multiplier=1.5)
    out = run_postprocess(row0 + row1 + row2 + row3, image_width=1000, image_height=650, config=cfg)
    assert len(out.rows) == 4
    # Row 3 (surrounded by [0,700] rows) has NO false poster gap [700,1000]
    assert out.rows[3].gaps == []
    # Row 2 (missing [400,700] vs neighbor rows ending at 700) DOES flag [400, 700]!
    assert len(out.rows[2].gaps) == 1
    assert (out.rows[2].gaps[0].x1, out.rows[2].gaps[0].x2) == pytest.approx((400.0, 700.0))


# ---------------------------------------------------------------------------
# Gap detection rules: local neighbor median, boundaries, edges, overlaps (ADR-0002)
# ---------------------------------------------------------------------------


def test_merge_intervals_handles_overlaps_touching_and_unsorted() -> None:
    merged = merge_intervals([(50, 100), (10, 30), (30, 55), (120, 150), (130, 140)])
    assert merged == [(10, 100), (120, 150)]


def test_gap_threshold_boundary_is_strictly_greater() -> None:
    """gap_width == k * local_ref_width must NOT trigger; +0.1px MUST trigger."""
    exact_row = ShelfRow(
        index=0,
        y1=0,
        y2=100,
        boxes=_make_row_boxes(0, 100, [(0, 100), (250, 350)]),
    )
    assert find_gaps(exact_row, 0, 350, width_multiplier=1.5) == []

    over_row = ShelfRow(
        index=0,
        y1=0,
        y2=100,
        boxes=_make_row_boxes(0, 100, [(0, 100), (250.1, 350.1)]),
    )
    gaps = find_gaps(over_row, 0, 350.1, width_multiplier=1.5)
    assert len(gaps) == 1
    assert (gaps[0].x1, gaps[0].x2) == pytest.approx((100.0, 250.1))


def test_local_neighbor_median_adapts_to_mixed_product_widths() -> None:
    """ADR-0002 §1.3: narrow products on left vs wide products on right use local median widths."""
    boxes = _make_row_boxes(
        0,
        100,
        [
            (0, 40),
            (40, 80),
            (155, 195),  # 75px gap (> 1.5 * 40 = 60 -> GAP!)
            (195, 235),
            (235, 355),  # w=120
            (355, 475),  # w=120
            (625, 745),  # 150px gap (<= 1.5 * 120 = 180 -> NOT a gap!)
            (745, 865),  # w=120
        ],
    )
    row = ShelfRow(index=0, y1=0, y2=100, boxes=boxes)
    gaps = find_gaps(row, 0, 865, width_multiplier=1.5, neighbor_count=4)
    assert len(gaps) == 1
    assert (gaps[0].x1, gaps[0].x2) == (80.0, 155.0)


def test_edge_gaps_detected_on_left_and_right_margins() -> None:
    boxes = _make_row_boxes(50, 150, [(200, 260), (260, 320), (320, 380)])
    row = ShelfRow(index=0, y1=50, y2=150, boxes=boxes)
    gaps = find_gaps(row, shelf_x1=0.0, shelf_x2=600.0, width_multiplier=1.5)
    assert [(g.x1, g.x2) for g in gaps] == [(0.0, 200.0), (380.0, 600.0)]


def test_single_box_row_uses_shelf_median_fallback() -> None:
    row = ShelfRow(index=0, y1=0, y2=100, boxes=[BoundingBox(x1=0, y1=0, x2=40, y2=100)])
    assert len(find_gaps(row, 0, 120, width_multiplier=1.5)) == 1
    assert find_gaps(row, 0, 120, width_multiplier=1.5, shelf_median_width=100.0) == []


def test_overlapping_boxes_do_not_inflate_local_ref_width() -> None:
    """ADR-0002 §1.3: ref width uses ORIGINAL unmerged boxes, not merged intervals."""
    boxes = _make_row_boxes(
        0,
        100,
        [(0, 60), (40, 100), (80, 140), (300, 360), (340, 400)],
    )
    row = ShelfRow(index=0, y1=0, y2=100, boxes=boxes)
    # Free span [140, 300] = 160px; original box width = 60 -> thresh = 90
    gaps = find_gaps(row, 0, 400, width_multiplier=1.5)
    assert len(gaps) == 1
    assert (gaps[0].x1, gaps[0].x2) == (140.0, 300.0)


def test_no_detection_policy_sets_alert_and_reason() -> None:
    out = run_postprocess([], image_width=1000, image_height=800)
    assert out.rows == []
    assert out.gaps == []
    assert out.fill_rate == 0.0
    assert out.alert is True
    assert out.alert_reason == "no_detection"
    assert determine_alert_reason(0.0, row_count=0, threshold=0.8) == "no_detection"
    assert determine_alert_reason(0.8, row_count=2, threshold=0.8) is None
    assert should_alert(0.79, 0.80) is True


# ---------------------------------------------------------------------------
# Store ROI mode (ADR-0003 §5, FR-10 readiness)
# ---------------------------------------------------------------------------


def test_store_roi_axis_aligned_assigns_tiers_and_empty_rows() -> None:
    roi = StoreROI(shelf_bbox=(100, 100, 900, 700), row_lines=[300.0, 500.0])
    # Tier 0 empty, tier 1 half-full (+ clutter outside ROI), tier 2 full
    clutter = BoundingBox(x1=10, y1=350, x2=50, y2=450)
    tier1 = _make_row_boxes(320, 480, [(100 + i * 100, 200 + i * 100) for i in range(4)])
    tier2 = _make_row_boxes(520, 680, [(100 + i * 100, 200 + i * 100) for i in range(8)])

    out = run_postprocess([clutter, *tier1, *tier2], image_width=1000, image_height=800, roi=roi)
    assert out.geometry.mode == "roi"
    assert len(out.rows) == 3
    assert [r.index for r in out.rows] == [0, 1, 2]
    assert clutter not in out.boxes
    assert out.rows[0].fill_rate == 0.0
    assert len(out.rows[0].gaps) == 1
    assert (out.rows[0].gaps[0].x1, out.rows[0].gaps[0].x2) == (100.0, 900.0)
    assert out.rows[1].fill_rate == pytest.approx(0.5)
    assert len(out.rows[1].gaps) == 1
    assert (out.rows[1].gaps[0].x1, out.rows[1].gaps[0].x2) == (500.0, 900.0)
    assert out.rows[2].fill_rate == pytest.approx(1.0)
    assert out.rows[2].gaps == []
    assert out.fill_rate == pytest.approx(0.5)
    assert out.alert is True
    assert out.alert_reason == "low_fill"


def test_store_roi_polygon_and_slanted_row_line() -> None:
    roi = StoreROI(
        shelf_bbox=((100, 100), (900, 120), (880, 520), (80, 500)),
        row_lines=[((90, 300), (890, 320))],
    )
    boxes = _make_row_boxes(150, 260, [(200, 300), (300, 400)])
    out = run_postprocess(boxes, image_width=1000, image_height=600, roi=roi)
    assert len(out.rows) == 2
    assert len(out.rows[0].boxes) == 2
    assert len(out.rows[1].boxes) == 0


def test_store_roi_rejects_unordered_row_lines() -> None:
    with pytest.raises(ValidationError):
        StoreROI(shelf_bbox=(0, 0, 500, 500), row_lines=[300.0, 200.0])


# ---------------------------------------------------------------------------
# Visualization & Pipeline API contract (FR-01, FR-02, DESIGN.md §5)
# ---------------------------------------------------------------------------


def test_draw_annotations_returns_modified_copy_without_mutating_input() -> None:
    img = np.full((300, 600, 3), 128, dtype=np.uint8)
    original_snapshot = img.copy()
    boxes = _make_row_boxes(100, 200, [(50, 150), (400, 500)])
    gaps = [Gap(row_index=0, x1=150, y1=100, x2=400, y2=200)]
    rows = [ShelfRow(index=0, y1=100, y2=200, boxes=boxes, gaps=gaps, fill_rate=0.45)]

    annotated = draw_annotations(
        img,
        boxes,
        gaps,
        fill_rate=0.45,
        rows=rows,
        shelf_polygon=[(50, 100), (500, 100), (500, 200), (50, 200)],
        alert=True,
    )
    assert annotated.shape == img.shape
    assert np.array_equal(img, original_snapshot)
    assert not np.array_equal(annotated, img)


def test_pipeline_analyze_image_rescales_boxes_and_matches_api_schema() -> None:
    """DESIGN.md §3 & §5: resized inference boxes map back to original pixels & API JSON."""
    orig_img = np.zeros((1000, 2000, 3), dtype=np.uint8)
    resized_boxes = [
        BoundingBox(x1=0, y1=100, x2=100, y2=200, confidence=0.91),
        BoundingBox(x1=100, y1=100, x2=200, y2=200, confidence=0.89),
        BoundingBox(x1=400, y1=100, x2=500, y2=200, confidence=0.88),
        BoundingBox(x1=500, y1=100, x2=600, y2=200, confidence=0.92),
    ]
    detector = FakeDetector(boxes=resized_boxes, version="test-v1")
    settings = Settings(
        max_image_side=1000,
        gap_width_multiplier=1.5,
        fill_rate_alert_threshold=0.8,
    )

    result = analyze_image(orig_img, store_id="S001", detector=detector, settings=settings)
    assert isinstance(result, AnalysisResult)
    payload = result.model_dump()
    assert set(payload.keys()) == {
        "analysis_id",
        "store_id",
        "created_at",
        "model_version",
        "product_count",
        "boxes",
        "rows",
        "gaps",
        "fill_rate",
        "alert",
        "timings_ms",
    }
    assert result.product_count == 4
    assert result.boxes[0].x2 == pytest.approx(200.0)
    assert result.boxes[-1].x2 == pytest.approx(1200.0)
    assert len(result.gaps) == 1
    assert (result.gaps[0].x1, result.gaps[0].x2) == pytest.approx((400.0, 800.0))
    assert set(result.timings_ms.keys()) == {"preprocess", "inference", "postprocess"}
    assert set(payload["rows"][0].keys()) == {"index", "y1", "y2", "boxes", "gaps", "fill_rate"}


def test_filter_by_confidence_keeps_exact_boundary() -> None:
    boxes = [
        BoundingBox(x1=0, y1=0, x2=10, y2=10, confidence=0.24),
        BoundingBox(x1=0, y1=0, x2=10, y2=10, confidence=0.25),
    ]
    assert len(filter_by_confidence(boxes, 0.25)) == 1
