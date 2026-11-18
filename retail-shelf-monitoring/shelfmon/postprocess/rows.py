from __future__ import annotations

from shelfmon.schemas import BoundingBox, ShelfRow


def group_into_rows(boxes: list[BoundingBox]) -> list[ShelfRow]:
    """Group product boxes into shelf rows by vertical position (FR-03).

    Returns rows ordered top → bottom, each with its boxes sorted left → right.

    TODO(FR-03): suggested baseline —
      1. sort boxes by center-y;
      2. start a new row when a box's center-y is farther than ~0.5 × median box height
         from the current row's mean center-y;
      3. row.y1/y2 = min(y1)/max(y2) of its boxes.
    Document the chosen rule (and failure cases: tilted photos, partial shelves) in the Design Doc.
    """
    raise NotImplementedError("group_into_rows is not implemented yet (FR-03)")
