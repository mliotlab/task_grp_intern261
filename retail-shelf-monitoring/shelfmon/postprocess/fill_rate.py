from __future__ import annotations

from shelfmon.schemas import ShelfRow


def row_fill_rate(row: ShelfRow, shelf_x1: float, shelf_x2: float) -> float:
    """Share of the row's width covered by products, in [0, 1] (FR-04).

    TODO(FR-04): union of box x-intervals (overlaps counted once) / (shelf_x2 - shelf_x1).
    """
    raise NotImplementedError("row_fill_rate is not implemented yet (FR-04)")


def image_fill_rate(rows: list[ShelfRow]) -> float:
    """Fill rate of the whole image (FR-04).

    TODO(FR-04): decide (and document) the aggregation — mean of rows, or width-weighted mean.
    An image with no detected rows has fill rate 0.0.
    """
    raise NotImplementedError("image_fill_rate is not implemented yet (FR-04)")
