from __future__ import annotations

from shelfmon.schemas import BoundingBox


def filter_by_confidence(boxes: list[BoundingBox], threshold: float) -> list[BoundingBox]:
    """Keep boxes with confidence >= threshold."""
    return [b for b in boxes if b.confidence >= threshold]
