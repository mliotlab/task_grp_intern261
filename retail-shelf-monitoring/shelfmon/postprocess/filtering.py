"""Pre-clustering detection filtering and coordinate normalization (ADR-0003 §1, DESIGN.md §3)."""

from __future__ import annotations

import numpy as np

from shelfmon.schemas import BoundingBox


def filter_by_confidence(boxes: list[BoundingBox], threshold: float) -> list[BoundingBox]:
    """Keep boxes with confidence >= threshold."""
    return [b for b in boxes if b.confidence >= threshold]


def clamp_boxes(
    boxes: list[BoundingBox],
    image_width: float,
    image_height: float,
    min_side_px: float = 0.0,
) -> list[BoundingBox]:
    """Clamp box coordinates to ``[0, image_width] x [0, image_height]``.

    Drops any box that becomes degenerate (``width <= min_side_px`` or
    ``height <= min_side_px``) after clamping.
    """
    if image_width <= 0 or image_height <= 0:
        return []

    clamped: list[BoundingBox] = []
    max_x = float(image_width)
    max_y = float(image_height)
    for b in boxes:
        x1 = max(0.0, min(b.x1, max_x))
        y1 = max(0.0, min(b.y1, max_y))
        x2 = max(0.0, min(b.x2, max_x))
        y2 = max(0.0, min(b.y2, max_y))
        if (x2 - x1) > min_side_px and (y2 - y1) > min_side_px:
            clamped.append(b.model_copy(update={"x1": x1, "y1": y1, "x2": x2, "y2": y2}))
    return clamped


def rescale_boxes(
    boxes: list[BoundingBox],
    from_size: tuple[int, int],
    to_size: tuple[int, int],
    *,
    clamp: bool = True,
) -> list[BoundingBox]:
    """Convert boxes from resized inference coordinates back to original image pixels.

    Args:
        boxes: Detections produced on an image of size ``from_size``.
        from_size: ``(width, height)`` of the image passed to the detector.
        to_size: ``(width, height)`` of the original uploaded image.
        clamp: Clamp resulting coordinates into ``[0, to_w] x [0, to_h]``.
    """
    from_w, from_h = from_size
    to_w, to_h = to_size
    if from_w <= 0 or from_h <= 0 or to_w <= 0 or to_h <= 0:
        raise ValueError("Image dimensions must be positive")
    if from_w == to_w and from_h == to_h:
        return clamp_boxes(boxes, to_w, to_h) if clamp else list(boxes)

    sx = to_w / from_w
    sy = to_h / from_h
    scaled: list[BoundingBox] = []
    for b in boxes:
        x1 = b.x1 * sx
        y1 = b.y1 * sy
        x2 = b.x2 * sx
        y2 = b.y2 * sy
        if clamp:
            x1 = max(0.0, min(x1, float(to_w)))
            y1 = max(0.0, min(y1, float(to_h)))
            x2 = max(0.0, min(x2, float(to_w)))
            y2 = max(0.0, min(y2, float(to_h)))
        if x2 > x1 and y2 > y1:
            scaled.append(b.model_copy(update={"x1": x1, "y1": y1, "x2": x2, "y2": y2}))
    return scaled


def filter_geometric_outliers(
    boxes: list[BoundingBox],
    *,
    min_side_px: float = 2.0,
    min_height_ratio: float = 0.25,
    max_height_ratio: float = 3.5,
    min_area_ratio: float = 0.08,
    min_boxes_for_stats: int = 6,
) -> list[BoundingBox]:
    """Remove degenerate boxes and extreme size outliers (e.g. price tags) before clustering.

    Per ADR-0003 §1, this never discards sparse rows via a minimum box-count cutoff;
    statistical median filtering only activates when at least ``min_boxes_for_stats``
    non-degenerate detections are present so small synthetic inputs remain intact.
    """
    non_degenerate = [b for b in boxes if b.width >= min_side_px and b.height >= min_side_px]
    if len(non_degenerate) < min_boxes_for_stats:
        return non_degenerate

    heights = np.array([b.height for b in non_degenerate], dtype=np.float64)
    areas = np.array([b.area for b in non_degenerate], dtype=np.float64)
    med_h = float(np.median(heights))
    med_area = float(np.median(areas))

    min_h = min_height_ratio * med_h
    max_h = max_height_ratio * med_h
    min_area = min_area_ratio * med_area

    return [b for b in non_degenerate if min_h <= b.height <= max_h and b.area >= min_area]
