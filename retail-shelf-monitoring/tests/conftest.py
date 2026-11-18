from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from shelfmon.schemas import BoundingBox


def make_row(
    y1: float, y2: float, xs: list[tuple[float, float]], conf: float = 0.9
) -> list[BoundingBox]:
    """Synthetic products on one shelf row: `xs` is a list of (x1, x2) intervals."""
    return [BoundingBox(x1=a, y1=y1, x2=b, y2=y2, confidence=conf) for a, b in xs]


@pytest.fixture
def two_row_shelf() -> list[BoundingBox]:
    """1000 px wide image, two rows.
    Row 0 (y 100–200): full except one 300 px gap between x=400 and x=700.
    Row 1 (y 300–400): completely full.
    """
    top = make_row(
        100,
        200,
        [(0, 100), (100, 200), (200, 300), (300, 400), (700, 800), (800, 900), (900, 1000)],
    )
    bottom = make_row(300, 400, [(i * 100, (i + 1) * 100) for i in range(10)])
    return top + bottom


@pytest.fixture
def api_client() -> TestClient:
    from services.api.main import app

    return TestClient(app)
