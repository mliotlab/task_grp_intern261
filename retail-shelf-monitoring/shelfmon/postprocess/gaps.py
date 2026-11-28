"""Empty-gap detection per shelf row using local neighbor median width (ADR-0002 §1–§2)."""

from __future__ import annotations

import numpy as np

from shelfmon.schemas import BoundingBox, Gap, ShelfRow


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Merge overlapping or touching 1D intervals ``(x1, x2)`` into sorted disjoint spans."""
    valid = [(x1, x2) for x1, x2 in intervals if x2 > x1]
    if not valid:
        return []
    valid.sort(key=lambda iv: (iv[0], iv[1]))
    merged: list[tuple[float, float]] = [valid[0]]
    for x1, x2 in valid[1:]:
        prev_x1, prev_x2 = merged[-1]
        if x1 <= prev_x2:
            merged[-1] = (prev_x1, max(prev_x2, x2))
        else:
            merged.append((x1, x2))
    return merged


def _select_neighbor_boxes(
    orig_boxes: list[BoundingBox],
    gx1: float,
    gx2: float,
    kind: str,
    neighbor_count: int,
) -> list[BoundingBox]:
    """Select up to ``neighbor_count`` (4–5) nearest original boxes for a candidate gap.

    Per ADR-0002 §1.3:
    - Interior gaps select balanced neighbors across left and right sides.
    - Left/right edge gaps select the nearest boxes to that edge.
    """
    k = max(1, neighbor_count)
    if len(orig_boxes) <= k:
        return orig_boxes

    ordered = sorted(orig_boxes, key=lambda b: (b.center[0], b.x1))
    if kind == "left":
        return ordered[:k]
    if kind == "right":
        return ordered[-k:]

    # Interior span: balance left and right neighbors nearest to [gx1, gx2]
    gap_mid = 0.5 * (gx1 + gx2)
    left_side = sorted(
        [b for b in ordered if b.center[0] <= gap_mid],
        key=lambda b: (max(0.0, gx1 - b.x2), abs(gap_mid - b.center[0])),
    )
    right_side = sorted(
        [b for b in ordered if b.center[0] > gap_mid],
        key=lambda b: (max(0.0, b.x1 - gx2), abs(b.center[0] - gap_mid)),
    )

    half = k // 2
    chosen_left = left_side[:half]
    chosen_right = right_side[:half]
    rem_left = left_side[len(chosen_left) :]
    rem_right = right_side[len(chosen_right) :]

    # Fill remaining slots (odd k or one side shorter than half) by closest distance to gap
    remaining = sorted(
        rem_left + rem_right,
        key=lambda b: (
            max(0.0, gx1 - b.x2) if b.center[0] <= gap_mid else max(0.0, b.x1 - gx2),
            abs(b.center[0] - gap_mid),
        ),
    )
    needed = k - (len(chosen_left) + len(chosen_right))
    return chosen_left + chosen_right + remaining[:needed]


def find_gaps(
    row: ShelfRow,
    shelf_x1: float,
    shelf_x2: float,
    width_multiplier: float = 1.5,
    *,
    neighbor_count: int = 5,
    shelf_median_width: float | None = None,
    use_local_y: bool = False,
    image_height: float | None = None,
) -> list[Gap]:
    """Find empty horizontal intervals in one shelf row (FR-03, ADR-0002 §1–§2).

    - Completely empty rows (``len(row.boxes) == 0``) emit one full-width ``Gap``.
    - Occupied rows merge overlapping clipped x-intervals and flag every free span
      strictly wider than ``width_multiplier * local_ref_width``, where
      ``local_ref_width`` is the median width of up to ``neighbor_count`` (default 5)
      nearest original unmerged boxes around the candidate span.
    """
    if shelf_x2 <= shelf_x1:
        return []

    if not row.boxes:
        if row.y2 <= row.y1:
            return []
        return [
            Gap(
                row_index=row.index,
                x1=float(shelf_x1),
                y1=float(row.y1),
                x2=float(shelf_x2),
                y2=float(row.y2),
            )
        ]

    # Clip product x-intervals to effective row horizontal bounds and merge overlaps
    clipped: list[tuple[float, float]] = []
    in_bounds_boxes: list[BoundingBox] = []
    for box in row.boxes:
        cx1 = max(float(shelf_x1), box.x1)
        cx2 = min(float(shelf_x2), box.x2)
        if cx2 > cx1:
            clipped.append((cx1, cx2))
            in_bounds_boxes.append(box)

    merged = merge_intervals(clipped)
    if not merged:
        if row.y2 <= row.y1:
            return []
        return [
            Gap(
                row_index=row.index,
                x1=float(shelf_x1),
                y1=float(row.y1),
                x2=float(shelf_x2),
                y2=float(row.y2),
            )
        ]

    # Candidate free spans within [shelf_x1, shelf_x2]
    candidates: list[tuple[float, float, str]] = []
    if merged[0][0] > shelf_x1:
        candidates.append((float(shelf_x1), merged[0][0], "left"))
    for i in range(len(merged) - 1):
        gx1, gx2 = merged[i][1], merged[i + 1][0]
        if gx2 > gx1:
            candidates.append((gx1, gx2, "interior"))
    if shelf_x2 > merged[-1][1]:
        candidates.append((merged[-1][1], float(shelf_x2), "right"))

    gaps: list[Gap] = []
    for gx1, gx2, kind in candidates:
        neighbors = _select_neighbor_boxes(
            in_bounds_boxes,
            gx1=gx1,
            gx2=gx2,
            kind=kind,
            neighbor_count=neighbor_count,
        )
        if len(in_bounds_boxes) == 1 and shelf_median_width is not None and shelf_median_width > 0:
            local_ref_width = 0.5 * (in_bounds_boxes[0].width + shelf_median_width)
        else:
            local_ref_width = float(np.median([b.width for b in neighbors]))

        if (gx2 - gx1) > width_multiplier * local_ref_width:
            if use_local_y and neighbors:
                gy1 = float(np.median([b.y1 for b in neighbors]))
                gy2 = float(np.median([b.y2 for b in neighbors]))
                if image_height is not None:
                    gy1 = max(0.0, min(gy1, float(image_height)))
                    gy2 = max(0.0, min(gy2, float(image_height)))
                if gy2 <= gy1:
                    gy1, gy2 = float(row.y1), float(row.y2)
            else:
                gy1, gy2 = float(row.y1), float(row.y2)

            if gy2 > gy1:
                gaps.append(
                    Gap(
                        row_index=row.index,
                        x1=gx1,
                        y1=gy1,
                        x2=gx2,
                        y2=gy2,
                    )
                )

    return gaps
