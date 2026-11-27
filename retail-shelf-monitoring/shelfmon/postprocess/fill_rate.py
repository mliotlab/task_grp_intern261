"""Row-level and image-level shelf fill-rate calculations (FR-04, ADR-0002 §3)."""

from __future__ import annotations

from shelfmon.postprocess.gaps import merge_intervals
from shelfmon.schemas import ShelfRow


def row_fill_rate(row: ShelfRow, shelf_x1: float, shelf_x2: float) -> float:
    """Share of the row's width covered by products, in ``[0, 1]`` (FR-04, ADR-0002 §3.1).

    Overlapping boxes are merged so they are counted once. Empty rows return ``0.0``.
    """
    span = float(shelf_x2) - float(shelf_x1)
    if span <= 0.0 or not row.boxes:
        return 0.0

    clipped = [(max(float(shelf_x1), b.x1), min(float(shelf_x2), b.x2)) for b in row.boxes]
    merged = merge_intervals(clipped)
    occupied = sum(x2 - x1 for x1, x2 in merged)
    return max(0.0, min(1.0, occupied / span))


def image_fill_rate(rows: list[ShelfRow]) -> float:
    """Arithmetic mean fill rate across all shelf rows including empty tiers (ADR-0002 §3.2).

    Returns ``0.0`` when no rows exist.
    """
    if not rows:
        return 0.0
    mean_rate = sum(r.fill_rate for r in rows) / len(rows)
    return max(0.0, min(1.0, mean_rate))
