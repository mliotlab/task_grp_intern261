"""Shelf geometry estimation, row clustering, tilt deskewing, and empty tiers (ADR-0003)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from shelfmon.postprocess.types import PostprocessConfig, RowRegion, ShelfGeometry
from shelfmon.schemas import BoundingBox, ShelfRow


@dataclass(frozen=True)
class _ProjectedBox:
    """Product box represented in the deskewed frame ``(x', y')``."""

    box: BoundingBox
    x1: float
    y1: float
    x2: float
    y2: float
    cx: float
    cy: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass(frozen=True)
class _StackUnit:
    """One atomic product column on a shelf tier (single box or vertically stacked boxes)."""

    items: tuple[_ProjectedBox, ...]
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def cx(self) -> float:
        return 0.5 * (self.x1 + self.x2)

    @property
    def cy(self) -> float:
        return 0.5 * (self.y1 + self.y2)

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def orig_y1(self) -> float:
        return min(p.box.y1 for p in self.items)

    @property
    def orig_y2(self) -> float:
        return max(p.box.y2 for p in self.items)


def _to_deskewed(
    x: float,
    y: float,
    pivot_x: float,
    pivot_y: float,
    cos_t: float,
    sin_t: float,
) -> tuple[float, float]:
    """Rotate image point ``(x, y)`` by ``-theta`` into the deskewed frame."""
    dx = x - pivot_x
    dy = y - pivot_y
    return (dx * cos_t + dy * sin_t + pivot_x, -dx * sin_t + dy * cos_t + pivot_y)


def _from_deskewed(
    xp: float,
    yp: float,
    pivot_x: float,
    pivot_y: float,
    cos_t: float,
    sin_t: float,
) -> tuple[float, float]:
    """Rotate deskewed point ``(x', y')`` by ``+theta`` back into image coordinates."""
    dx = xp - pivot_x
    dy = yp - pivot_y
    return (dx * cos_t - dy * sin_t + pivot_x, dx * sin_t + dy * cos_t + pivot_y)


def _project_boxes(
    boxes: list[BoundingBox],
    pivot_x: float,
    pivot_y: float,
    theta_rad: float,
) -> list[_ProjectedBox]:
    if theta_rad == 0.0:
        return [
            _ProjectedBox(
                box=b,
                x1=b.x1,
                y1=b.y1,
                x2=b.x2,
                y2=b.y2,
                cx=b.center[0],
                cy=b.center[1],
            )
            for b in boxes
        ]

    cos_t = math.cos(theta_rad)
    sin_t = math.sin(theta_rad)
    projected: list[_ProjectedBox] = []
    for b in boxes:
        cx, cy = b.center
        cxp, cyp = _to_deskewed(cx, cy, pivot_x, pivot_y, cos_t, sin_t)
        hw = 0.5 * b.width
        hh = 0.5 * b.height
        projected.append(
            _ProjectedBox(
                box=b,
                x1=cxp - hw,
                y1=cyp - hh,
                x2=cxp + hw,
                y2=cyp + hh,
                cx=cxp,
                cy=cyp,
            )
        )
    return projected


def _find_root(parent: list[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union_sets(parent: list[int], a: int, b: int) -> None:
    ra, rb = _find_root(parent, a), _find_root(parent, b)
    if ra != rb:
        parent[rb] = ra


def _build_stack_units(
    projected: list[_ProjectedBox],
    config: PostprocessConfig,
) -> list[_StackUnit]:
    """Group vertically stacked product boxes into atomic stack columns (ADR-0002 §4)."""
    if not config.consolidate_stacked_boxes or len(projected) < 2:
        return [_StackUnit(items=(p,), x1=p.x1, y1=p.y1, x2=p.x2, y2=p.y2) for p in projected]

    n = len(projected)
    parent = list(range(n))
    for i in range(n):
        a = projected[i]
        ar_a = a.width / max(a.height, 1.0)
        for j in range(i + 1, n):
            b = projected[j]
            ix = min(a.x2, b.x2) - max(a.x1, b.x1)
            if ix <= 0.0:
                continue
            min_w = min(a.width, b.width)
            if min_w <= 0.0 or (ix / min_w) < config.stack_x_overlap_ratio:
                continue

            upper, lower = (a, b) if a.cy <= b.cy else (b, a)
            v_sep = lower.y1 - upper.y2
            min_h = min(upper.height, lower.height)
            ar_b = b.width / max(b.height, 1.0)
            is_flat_pair = (
                ar_a >= config.flat_stack_aspect_ratio and ar_b >= config.flat_stack_aspect_ratio
            )
            max_sep = (
                config.flat_stack_v_gap_ratio * min_h
                if is_flat_pair
                else config.stack_v_gap_ratio * min_h
            )
            if (-0.5 * min_h) <= v_sep <= max_sep:
                _union_sets(parent, i, j)

    groups: dict[int, list[_ProjectedBox]] = {}
    for i, item in enumerate(projected):
        groups.setdefault(_find_root(parent, i), []).append(item)

    units: list[_StackUnit] = []
    for items in groups.values():
        items.sort(key=lambda p: (p.y1, p.x1))
        units.append(
            _StackUnit(
                items=tuple(items),
                x1=min(p.x1 for p in items),
                y1=min(p.y1 for p in items),
                x2=max(p.x2 for p in items),
                y2=max(p.y2 for p in items),
            )
        )
    return units


def _vertical_overlap_fraction(a_y1: float, a_y2: float, b_y1: float, b_y2: float) -> float:
    min_h = min(a_y2 - a_y1, b_y2 - b_y1)
    if min_h <= 0.0:
        return 0.0
    inter = max(0.0, min(a_y2, b_y2) - max(a_y1, b_y1))
    return inter / min_h


def _cluster_units_center_y(
    units: list[_StackUnit],
    config: PostprocessConfig,
) -> list[list[_StackUnit]]:
    """Height-relative ``center_y`` clustering with vertical-overlap affinity (ADR-0003 §2.1)."""
    if not units:
        return []

    ordered = sorted(units, key=lambda u: (u.cy, u.x1))
    global_med_h = float(np.median([u.height for u in ordered]))
    clusters: list[list[_StackUnit]] = [[ordered[0]]]
    sum_cy = ordered[0].cy

    for unit in ordered[1:]:
        cur = clusters[-1]
        mean_cy = sum_cy / len(cur)
        cur_y1 = float(np.median([u.y1 for u in cur])) if len(cur) >= 3 else min(u.y1 for u in cur)
        cur_y2 = float(np.median([u.y2 for u in cur])) if len(cur) >= 3 else max(u.y2 for u in cur)
        cur_h = max(1.0, cur_y2 - cur_y1)
        ref_h = 0.5 * (cur_h + unit.height) if config.use_local_row_height else global_med_h
        tol = config.row_y_tolerance_ratio * ref_h
        v_ov = _vertical_overlap_fraction(cur_y1, cur_y2, unit.y1, unit.y2)

        if abs(unit.cy - mean_cy) <= tol or (
            config.consolidate_stacked_boxes and v_ov >= config.row_v_merge_threshold
        ):
            cur.append(unit)
            sum_cy += unit.cy
        else:
            clusters.append([unit])
            sum_cy = unit.cy

    return clusters


def _cluster_units_dbscan_1d(
    units: list[_StackUnit],
    config: PostprocessConfig,
) -> list[list[_StackUnit]]:
    """1D vertical DBSCAN-style clustering (``min_samples=1`` to preserve sparse rows)."""
    if not units:
        return []

    ordered = sorted(units, key=lambda u: (u.cy, u.x1))
    global_med_h = float(np.median([u.height for u in ordered]))
    clusters: list[list[_StackUnit]] = [[ordered[0]]]

    for unit in ordered[1:]:
        prev = clusters[-1][-1]
        ref_h = 0.5 * (prev.height + unit.height) if config.use_local_row_height else global_med_h
        eps = config.row_y_tolerance_ratio * ref_h
        if (unit.cy - prev.cy) <= eps:
            clusters[-1].append(unit)
        else:
            clusters.append([unit])

    return clusters


def _consolidate_overlapping_clusters(
    clusters: list[list[_StackUnit]],
    v_merge_threshold: float,
) -> list[list[_StackUnit]]:
    """Iteratively merge clusters whose vertical bands overlap strongly (eliminates ghost rows)."""
    if len(clusters) < 2:
        return clusters

    changed = True
    while changed and len(clusters) > 1:
        changed = False
        clusters.sort(key=lambda c: float(np.median([u.cy for u in c])))
        merged: list[list[_StackUnit]] = [clusters[0]]
        for nxt in clusters[1:]:
            cur = merged[-1]
            cur_y1 = (
                float(np.percentile([u.y1 for u in cur], 25))
                if len(cur) >= 3
                else min(u.y1 for u in cur)
            )
            cur_y2 = (
                float(np.percentile([u.y2 for u in cur], 75))
                if len(cur) >= 3
                else max(u.y2 for u in cur)
            )
            nxt_y1 = (
                float(np.percentile([u.y1 for u in nxt], 25))
                if len(nxt) >= 3
                else min(u.y1 for u in nxt)
            )
            nxt_y2 = (
                float(np.percentile([u.y2 for u in nxt], 75))
                if len(nxt) >= 3
                else max(u.y2 for u in nxt)
            )
            v_ov = _vertical_overlap_fraction(cur_y1, cur_y2, nxt_y1, nxt_y2)
            if v_ov >= v_merge_threshold:
                merged[-1] = cur + nxt
                changed = True
            else:
                merged.append(nxt)
        clusters = merged
    return clusters


def _cluster_projected(
    projected: list[_ProjectedBox],
    config: PostprocessConfig,
) -> list[list[_StackUnit]]:
    units = _build_stack_units(projected, config)
    if config.clustering_method == "dbscan_1d":
        clusters = _cluster_units_dbscan_1d(units, config)
    else:
        clusters = _cluster_units_center_y(units, config)

    if config.consolidate_stacked_boxes:
        clusters = _consolidate_overlapping_clusters(clusters, config.row_v_merge_threshold)

    clusters.sort(key=lambda c: float(np.median([u.cy for u in c])))
    for c in clusters:
        c.sort(key=lambda u: (u.x1, u.x2))
    return clusters


def _estimate_tilt_rad(
    clusters: list[list[_StackUnit]],
    config: PostprocessConfig,
    *,
    apply_deadband: bool = True,
) -> float:
    """Estimate shelf roll/tilt angle ``theta`` from linear row centerlines (ADR-0003 §2.2)."""
    all_widths = [p.width for c in clusters for u in c for p in u.items]
    if not all_widths:
        return 0.0
    med_w = float(np.median(all_widths))

    slopes: list[float] = []
    for cluster in clusters:
        if len(cluster) < config.tilt_min_boxes_per_row:
            continue
        xs = np.array([u.cx for u in cluster], dtype=np.float64)
        ys = np.array([u.cy for u in cluster], dtype=np.float64)
        if float(xs.max() - xs.min()) < 2.0 * med_w:
            continue
        x_mean = float(xs.mean())
        y_mean = float(ys.mean())
        denom = float(np.sum((xs - x_mean) ** 2))
        if denom <= 1e-6:
            continue
        slope = float(np.sum((xs - x_mean) * (ys - y_mean)) / denom)
        slopes.append(slope)

    if not slopes:
        return 0.0

    theta_rad = math.atan(float(np.median(slopes)))
    theta_deg = abs(math.degrees(theta_rad))
    if apply_deadband and theta_deg < config.tilt_deadband_deg:
        return 0.0
    if theta_deg > config.tilt_max_deg:
        return 0.0
    return theta_rad


def _row_vertical_edges(
    values_y1: list[float],
    values_y2: list[float],
    mode: str,
) -> tuple[float, float]:
    """Compute representative row ``(y1, y2)`` using robust median or strict envelope."""
    if mode == "robust" and len(values_y1) >= 3:
        y1 = float(np.median(values_y1))
        y2 = float(np.median(values_y2))
        if y2 > y1:
            return y1, y2
    return float(min(values_y1)), float(max(values_y2))


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(val, hi))


@dataclass
class _DraftRow:
    """Intermediate row representation in deskewed coordinates before empty-tier insertion."""

    boxes: list[BoundingBox]
    orig_y1: float
    orig_y2: float
    deskew_y1: float
    deskew_y2: float
    deskew_x1: float
    deskew_x2: float
    is_inferred_empty: bool = False

    @property
    def deskew_cy(self) -> float:
        return 0.5 * (self.deskew_y1 + self.deskew_y2)

    @property
    def deskew_h(self) -> float:
        return max(0.0, self.deskew_y2 - self.deskew_y1)


def _infer_empty_tiers(
    occupied: list[_DraftRow],
    config: PostprocessConfig,
    mid_x_deskew: float,
    pivot_x: float,
    pivot_y: float,
    cos_t: float,
    sin_t: float,
    image_height: float | None,
) -> list[_DraftRow]:
    """Insert sandwiched empty middle tiers via ``Δy`` + periodic pitch check (ADR-0003 §4)."""
    if not config.infer_empty_tiers or len(occupied) < 2:
        return occupied

    heights = [r.deskew_h for r in occupied if r.deskew_h > 0]
    if not heights:
        return occupied
    global_med_h = float(np.median(heights))

    pitches = [
        occupied[i + 1].deskew_cy - occupied[i].deskew_cy
        for i in range(len(occupied) - 1)
        if (occupied[i + 1].deskew_cy - occupied[i].deskew_cy) > 0
    ]
    if len(pitches) >= 3:
        # Periodic shelf pitch: lower-half percentile resists 1–2 missing tiers inflating pitch.
        pitch_ref = float(np.percentile(pitches, 40))
    elif len(pitches) == 2:
        pitch_ref = min(pitches)
    else:
        pitch_ref = 1.25 * global_med_h
    pitch_ref = max(pitch_ref, global_med_h)

    all_rows: list[_DraftRow] = []
    for i, r_top in enumerate(occupied):
        all_rows.append(r_top)
        if i == len(occupied) - 1:
            break

        r_bot = occupied[i + 1]
        delta_y = r_bot.deskew_y1 - r_top.deskew_y2
        h_ref = max(0.5 * (r_top.deskew_h + r_bot.deskew_h), 0.5 * global_med_h)
        delta_c = r_bot.deskew_cy - r_top.deskew_cy

        if (
            delta_y <= config.empty_tier_kv * h_ref
            or delta_c < config.empty_tier_min_pitch_ratio * pitch_ref
        ):
            continue

        missing_count = min(config.max_empty_tiers_per_gap, round(delta_c / pitch_ref) - 1)
        if missing_count < 1:
            continue
        slot_span = delta_y / missing_count
        if slot_span <= 1e-6:
            continue

        for s in range(missing_count):
            sy1_p = r_top.deskew_y2 + s * slot_span
            sy2_p = r_top.deskew_y2 + (s + 1) * slot_span
            _, orig_y1 = _from_deskewed(mid_x_deskew, sy1_p, pivot_x, pivot_y, cos_t, sin_t)
            _, orig_y2 = _from_deskewed(mid_x_deskew, sy2_p, pivot_x, pivot_y, cos_t, sin_t)
            if orig_y2 < orig_y1:
                orig_y1, orig_y2 = orig_y2, orig_y1
            if image_height is not None:
                orig_y1 = _clamp(orig_y1, 0.0, float(image_height))
                orig_y2 = _clamp(orig_y2, 0.0, float(image_height))
            if orig_y2 <= orig_y1:
                continue
            all_rows.append(
                _DraftRow(
                    boxes=[],
                    orig_y1=orig_y1,
                    orig_y2=orig_y2,
                    deskew_y1=sy1_p,
                    deskew_y2=sy2_p,
                    deskew_x1=min(r_top.deskew_x1, r_bot.deskew_x1),
                    deskew_x2=max(r_top.deskew_x2, r_bot.deskew_x2),
                    is_inferred_empty=True,
                )
            )

    return all_rows


def _effective_row_deskew_x(
    idx: int,
    draft_rows: list[_DraftRow],
    shelf_x1_p: float,
    shelf_x2_p: float,
    config: PostprocessConfig,
) -> tuple[float, float]:
    """Compute per-row deskewed horizontal span ``[x1', x2']`` per configured bound mode."""
    draft = draft_rows[idx]
    if config.shelf_bound_mode == "row_extent" and draft.boxes:
        return draft.deskew_x1, draft.deskew_x2

    if config.shelf_bound_mode == "neighbor_median" and len(draft_rows) >= 3:
        lo = max(0, idx - 1)
        hi = min(len(draft_rows), idx + 2)
        nbrs = [
            draft_rows[k]
            for k in range(lo, hi)
            if len(draft_rows[k].boxes) >= config.edge_min_neighbor_boxes or k == idx
        ]
        win_x1 = float(np.median([r.deskew_x1 for r in nbrs]))
        win_x2 = float(np.median([r.deskew_x2 for r in nbrs]))
        if draft.boxes:
            return min(win_x1, draft.deskew_x1), max(win_x2, draft.deskew_x2)
        return win_x1, win_x2

    return shelf_x1_p, shelf_x2_p


def estimate_shelf_rows(
    boxes: list[BoundingBox],
    *,
    image_width: float | None = None,
    image_height: float | None = None,
    config: PostprocessConfig | None = None,
) -> ShelfGeometry:
    """Estimate shelf geometry and row regions in no-ROI rule-based mode (ADR-0003 §2–§4)."""
    cfg = config or PostprocessConfig()
    if not boxes:
        return ShelfGeometry(mode="rule", regions=[], tilt_deg=0.0, shelf_polygon=None)

    if image_width is not None and image_height is not None:
        pivot_x = 0.5 * float(image_width)
        pivot_y = 0.5 * float(image_height)
    else:
        pivot_x = float(np.mean([b.center[0] for b in boxes]))
        pivot_y = float(np.mean([b.center[1] for b in boxes]))

    # Step 1: Initial vertical clustering in original image coordinates
    initial_projected = _project_boxes(boxes, pivot_x, pivot_y, theta_rad=0.0)
    initial_clusters = _cluster_projected(initial_projected, cfg)

    # Step 2: Estimate tilt angle & deskew if outside deadband (with 1 refinement pass)
    theta_rad = _estimate_tilt_rad(initial_clusters, cfg, apply_deadband=True)

    if theta_rad != 0.0:
        projected = _project_boxes(boxes, pivot_x, pivot_y, theta_rad=theta_rad)
        clusters = _cluster_projected(projected, cfg)
        residual = _estimate_tilt_rad(clusters, cfg, apply_deadband=False)
        refined = theta_rad + residual
        if abs(math.degrees(refined)) <= cfg.tilt_max_deg and abs(residual) > 1e-4:
            theta_rad = refined if abs(math.degrees(refined)) >= cfg.tilt_deadband_deg else 0.0
            projected = _project_boxes(boxes, pivot_x, pivot_y, theta_rad=theta_rad)
            clusters = _cluster_projected(projected, cfg)
    else:
        projected = initial_projected
        clusters = initial_clusters

    cos_t = math.cos(theta_rad)
    sin_t = math.sin(theta_rad)

    # Step 3: Outer-product horizontal envelope in deskewed frame
    shelf_x1_p = min(p.x1 for p in projected)
    shelf_x2_p = max(p.x2 for p in projected)
    shelf_y1_p = min(p.y1 for p in projected)
    shelf_y2_p = max(p.y2 for p in projected)
    mid_x_p = 0.5 * (shelf_x1_p + shelf_x2_p)

    # Step 4: Build draft occupied rows with representative vertical bounds
    occupied: list[_DraftRow] = []
    for cluster in clusters:
        row_boxes = sorted(
            [p.box for u in cluster for p in u.items],
            key=lambda b: (b.x1, b.x2),
        )
        orig_y1, orig_y2 = _row_vertical_edges(
            [u.orig_y1 for u in cluster],
            [u.orig_y2 for u in cluster],
            cfg.row_vertical_bounds,
        )
        deskew_y1, deskew_y2 = _row_vertical_edges(
            [u.y1 for u in cluster],
            [u.y2 for u in cluster],
            cfg.row_vertical_bounds,
        )
        if image_height is not None:
            orig_y1 = _clamp(orig_y1, 0.0, float(image_height))
            orig_y2 = _clamp(orig_y2, 0.0, float(image_height))
        if orig_y2 <= orig_y1:
            orig_y1 = min(b.y1 for b in row_boxes)
            orig_y2 = max(b.y2 for b in row_boxes)
            if image_height is not None:
                orig_y1 = _clamp(orig_y1, 0.0, float(image_height))
                orig_y2 = _clamp(orig_y2, 0.0, float(image_height))
        occupied.append(
            _DraftRow(
                boxes=row_boxes,
                orig_y1=orig_y1,
                orig_y2=orig_y2,
                deskew_y1=deskew_y1,
                deskew_y2=deskew_y2,
                deskew_x1=min(u.x1 for u in cluster),
                deskew_x2=max(u.x2 for u in cluster),
                is_inferred_empty=False,
            )
        )

    # Step 5: Infer sandwiched completely empty middle tiers (ADR-0003 §4)
    draft_rows = _infer_empty_tiers(
        occupied=occupied,
        config=cfg,
        mid_x_deskew=mid_x_p,
        pivot_x=pivot_x,
        pivot_y=pivot_y,
        cos_t=cos_t,
        sin_t=sin_t,
        image_height=image_height,
    )

    # Step 6: Map horizontal bounds back to original image space & clamp (ADR-0003 §2.3 & §3)
    regions: list[RowRegion] = []
    for idx, draft in enumerate(draft_rows):
        if cfg.shelf_bound_mode == "image_width" and image_width is not None:
            row_x1, row_x2 = 0.0, float(image_width)
        else:
            eff_x1_p, eff_x2_p = _effective_row_deskew_x(
                idx, draft_rows, shelf_x1_p, shelf_x2_p, cfg
            )
            left_x, _ = _from_deskewed(eff_x1_p, draft.deskew_cy, pivot_x, pivot_y, cos_t, sin_t)
            right_x, _ = _from_deskewed(eff_x2_p, draft.deskew_cy, pivot_x, pivot_y, cos_t, sin_t)
            row_x1, row_x2 = (left_x, right_x) if left_x <= right_x else (right_x, left_x)
            if image_width is not None:
                row_x1 = _clamp(row_x1, 0.0, float(image_width))
                row_x2 = _clamp(row_x2, 0.0, float(image_width))

        shelf_row = ShelfRow(
            index=idx,
            y1=draft.orig_y1,
            y2=draft.orig_y2,
            boxes=draft.boxes,
            gaps=[],
            fill_rate=0.0 if not draft.boxes else 1.0,
        )
        regions.append(
            RowRegion(
                row=shelf_row,
                x1=row_x1,
                x2=row_x2,
                y1=draft.orig_y1,
                y2=draft.orig_y2,
                is_inferred_empty=draft.is_inferred_empty,
            )
        )

    raw_corners = [
        _from_deskewed(shelf_x1_p, shelf_y1_p, pivot_x, pivot_y, cos_t, sin_t),
        _from_deskewed(shelf_x2_p, shelf_y1_p, pivot_x, pivot_y, cos_t, sin_t),
        _from_deskewed(shelf_x2_p, shelf_y2_p, pivot_x, pivot_y, cos_t, sin_t),
        _from_deskewed(shelf_x1_p, shelf_y2_p, pivot_x, pivot_y, cos_t, sin_t),
    ]
    if image_width is not None and image_height is not None:
        polygon = [
            (_clamp(x, 0.0, float(image_width)), _clamp(y, 0.0, float(image_height)))
            for x, y in raw_corners
        ]
    else:
        polygon = raw_corners

    return ShelfGeometry(
        mode="rule",
        regions=regions,
        tilt_deg=round(math.degrees(theta_rad), 3),
        shelf_polygon=polygon,
    )


def group_into_rows(
    boxes: list[BoundingBox],
    *,
    image_width: float | None = None,
    image_height: float | None = None,
    config: PostprocessConfig | None = None,
) -> list[ShelfRow]:
    """Group product boxes into shelf rows ordered top → bottom, boxes left → right (FR-03)."""
    geometry = estimate_shelf_rows(
        boxes,
        image_width=image_width,
        image_height=image_height,
        config=config,
    )
    return geometry.rows
