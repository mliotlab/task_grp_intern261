from __future__ import annotations

import pytest
from pydantic import ValidationError

from shelfmon.alert import should_alert
from shelfmon.postprocess import filter_by_confidence
from shelfmon.schemas import BoundingBox


def test_bbox_geometry() -> None:
    b = BoundingBox(x1=10, y1=20, x2=50, y2=100)
    assert (b.width, b.height) == (40, 80)
    assert b.center == (30, 60)


@pytest.mark.parametrize("coords", [(10, 10, 5, 20), (10, 10, 20, 10)])
def test_bbox_rejects_inverted_coordinates(coords: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = coords
    with pytest.raises(ValidationError):
        BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)


def test_filter_by_confidence() -> None:
    boxes = [
        BoundingBox(x1=0, y1=0, x2=1, y2=1, confidence=0.2),
        BoundingBox(x1=0, y1=0, x2=1, y2=1, confidence=0.25),
        BoundingBox(x1=0, y1=0, x2=1, y2=1, confidence=0.9),
    ]
    assert [b.confidence for b in filter_by_confidence(boxes, 0.25)] == [0.25, 0.9]


@pytest.mark.parametrize(("fill", "expected"), [(0.79, True), (0.80, False), (1.0, False)])
def test_alert_threshold(fill: float, expected: bool) -> None:
    assert should_alert(fill, 0.80) is expected
