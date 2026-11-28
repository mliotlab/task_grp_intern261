"""Store ROI specification and tier assignment (ADR-0003 §5, FR-10 readiness)."""

from __future__ import annotations

from typing import TypeAlias

from pydantic import BaseModel, Field, model_validator

from shelfmon.postprocess.types import RowRegion, ShelfGeometry
from shelfmon.schemas import BoundingBox, ShelfRow

Point2D: TypeAlias = tuple[float, float]
BBoxRect: TypeAlias = tuple[float, float, float, float]
QuadPolygon: TypeAlias = tuple[Point2D, Point2D, Point2D, Point2D]
RowLine: TypeAlias = float | tuple[Point2D, Point2D]


def _is_quad(shelf_bbox: BBoxRect | QuadPolygon) -> bool:
    return isinstance(shelf_bbox[0], (tuple, list))


def _point_in_polygon(px: float, py: float, poly: list[Point2D]) -> bool:
    """Ray-casting point-in-polygon check (inclusive of boundary)."""
    n = len(poly)
    inside = False
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        # Boundary check (point on segment)
        dx, dy = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq > 0.0:
            t = ((px - x1) * dx + (py - y1) * dy) / seg_len_sq
            if 0.0 <= t <= 1.0:
                proj_x = x1 + t * dx
                proj_y = y1 + t * dy
                if (px - proj_x) ** 2 + (py - proj_y) ** 2 <= 1e-9:
                    return True
        if (y1 > py) != (y2 > py):
            x_intersect = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < x_intersect:
                inside = not inside
    return inside


def _interpolate_edge_x(p_top: Point2D, p_bot: Point2D, y: float) -> float:
    """Return x along the edge from p_top to p_bot at vertical coordinate y."""
    dy = p_bot[1] - p_top[1]
    if abs(dy) <= 1e-9:
        return 0.5 * (p_top[0] + p_bot[0])
    t = max(0.0, min(1.0, (y - p_top[1]) / dy))
    return p_top[0] + t * (p_bot[0] - p_top[0])


def _line_y_at_x(line: RowLine, x: float) -> float:
    """Evaluate a divider line (constant y or 2-point segment) at horizontal coordinate x."""
    if isinstance(line, (int, float)):
        return float(line)
    (x1, y1), (x2, y2) = line
    dx = x2 - x1
    if abs(dx) <= 1e-9:
        return 0.5 * (y1 + y2)
    t = (x - x1) / dx
    return y1 + t * (y2 - y1)


class StoreROI(BaseModel):
    """Per-store fixed-camera shelf ROI contract (ADR-0003 §5).

    - ``shelf_bbox``: axis-aligned ``(x1, y1, x2, y2)`` OR 4-vertex polygon
      ``(TL, TR, BR, BL)`` enclosing the full target shelf unit.
    - ``row_lines``: ordered list of ``N - 1`` divider lines (either horizontal ``y``
      floats or ``((x_left, y_left), (x_right, y_right))`` segments) partitioning
      the shelf into ``N`` vertical tiers (``0 .. N-1``). Empty list means 1 tier.
    """

    shelf_bbox: BBoxRect | QuadPolygon
    row_lines: list[RowLine] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_geometry(self) -> StoreROI:
        if _is_quad(self.shelf_bbox):
            quad = self.shelf_bbox  # type: ignore[assignment]
            if len(quad) != 4:
                raise ValueError("shelf_bbox polygon must have exactly 4 vertices (TL, TR, BR, BL)")
            tl, tr, br, bl = quad
            if tr[0] <= tl[0] or br[0] <= bl[0]:
                raise ValueError("shelf_bbox polygon right edge must be right of left edge")
            if bl[1] <= tl[1] or br[1] <= tr[1]:
                raise ValueError("shelf_bbox polygon bottom edge must be below top edge")
        else:
            x1, y1, x2, y2 = self.shelf_bbox  # type: ignore[misc]
            if x2 <= x1 or y2 <= y1:
                raise ValueError("shelf_bbox requires x2 > x1 and y2 > y1")

        # Validate row_lines are strictly increasing at the horizontal midpoint
        mid_x = self._mid_x()
        top_y = self._top_y_at(mid_x)
        bot_y = self._bottom_y_at(mid_x)
        prev_y = top_y
        for line in self.row_lines:
            ly = _line_y_at_x(line, mid_x)
            if not (prev_y < ly < bot_y):
                raise ValueError(
                    "row_lines must be strictly ordered inside shelf_bbox vertical span"
                )
            prev_y = ly
        return self

    def polygon(self) -> list[Point2D]:
        if _is_quad(self.shelf_bbox):
            quad: QuadPolygon = self.shelf_bbox  # type: ignore[assignment]
            return [(float(p[0]), float(p[1])) for p in quad]
        x1, y1, x2, y2 = self.shelf_bbox  # type: ignore[misc]
        return [
            (float(x1), float(y1)),
            (float(x2), float(y1)),
            (float(x2), float(y2)),
            (float(x1), float(y2)),
        ]

    def _mid_x(self) -> float:
        poly = self.polygon()
        return 0.25 * sum(p[0] for p in poly)

    def _top_y_at(self, x: float) -> float:
        tl, tr, _, _ = self.polygon()
        return _line_y_at_x((tl, tr), x)

    def _bottom_y_at(self, x: float) -> float:
        _, _, br, bl = self.polygon()
        return _line_y_at_x((bl, br), x)

    def contains_center(self, box: BoundingBox) -> bool:
        cx, cy = box.center
        return _point_in_polygon(cx, cy, self.polygon())

    def assign_boxes_to_rows(
        self,
        boxes: list[BoundingBox],
        image_width: float | None = None,
        image_height: float | None = None,
    ) -> ShelfGeometry:
        """Assign boxes whose centers fall inside ``shelf_bbox`` into all N ROI tiers."""
        poly = self.polygon()
        tl, tr, br, bl = poly
        num_tiers = len(self.row_lines) + 1
        tier_boxes: list[list[BoundingBox]] = [[] for _ in range(num_tiers)]

        for box in boxes:
            if not self.contains_center(box):
                continue
            cx, cy = box.center
            tier_idx = 0
            for line in self.row_lines:
                if cy >= _line_y_at_x(line, cx):
                    tier_idx += 1
                else:
                    break
            tier_boxes[tier_idx].append(box)

        mid_x = self._mid_x()
        boundaries = (
            [self._top_y_at(mid_x)]
            + [_line_y_at_x(line, mid_x) for line in self.row_lines]
            + [self._bottom_y_at(mid_x)]
        )

        regions: list[RowRegion] = []
        for idx in range(num_tiers):
            y1 = boundaries[idx]
            y2 = boundaries[idx + 1]
            row_cy = 0.5 * (y1 + y2)
            x1 = _interpolate_edge_x(tl, bl, row_cy)
            x2 = _interpolate_edge_x(tr, br, row_cy)

            if image_width is not None:
                x1 = max(0.0, min(x1, float(image_width)))
                x2 = max(x1, min(x2, float(image_width)))
            if image_height is not None:
                y1 = max(0.0, min(y1, float(image_height)))
                y2 = max(y1, min(y2, float(image_height)))

            sorted_boxes = sorted(tier_boxes[idx], key=lambda b: (b.x1, b.x2))
            shelf_row = ShelfRow(
                index=idx,
                y1=y1,
                y2=y2,
                boxes=sorted_boxes,
                gaps=[],
                fill_rate=0.0 if not sorted_boxes else 1.0,
            )
            regions.append(
                RowRegion(
                    row=shelf_row,
                    x1=x1,
                    x2=x2,
                    y1=y1,
                    y2=y2,
                    is_inferred_empty=False,
                )
            )

        return ShelfGeometry(
            mode="roi",
            regions=regions,
            tilt_deg=0.0,
            shelf_polygon=poly,
        )
