from __future__ import annotations

from shelfmon.schemas import Gap, ShelfRow


def find_gaps(
    row: ShelfRow, shelf_x1: float, shelf_x2: float, width_multiplier: float = 1.5
) -> list[Gap]:
    """Find empty horizontal intervals in one row (FR-03).

    A gap is any free interval — between neighbouring boxes, or between the shelf edges
    (`shelf_x1`, `shelf_x2`) and the first/last box — wider than
    `width_multiplier × mean product width` of the row.

    TODO(FR-03): implement; merge overlapping boxes before measuring free space.
    """
    raise NotImplementedError("find_gaps is not implemented yet (FR-03)")
