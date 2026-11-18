from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from shelfmon.pipeline import resize_max_side

_spec = importlib.util.spec_from_file_location(
    "prepare_subset", Path("training/scripts/prepare_subset.py")
)
prepare_subset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prepare_subset)


def test_sample_split_is_deterministic_and_order_independent() -> None:
    ids = [f"img_{i}" for i in range(100)]
    a = prepare_subset.sample_split(ids, 10, seed=1)
    b = prepare_subset.sample_split(list(reversed(ids)), 10, seed=1)
    assert a == b and len(set(a)) == 10


def test_to_yolo_line_normalises() -> None:
    line = prepare_subset.to_yolo_line(0, 0, 100, 50, img_w=200, img_h=100)
    assert line == "0 0.250000 0.250000 0.500000 0.500000"


@pytest.mark.parametrize(
    ("shape", "expected"), [((3000, 1500, 3), (1920, 960)), ((800, 600, 3), (800, 600))]
)
def test_resize_max_side(shape: tuple[int, int, int], expected: tuple[int, int]) -> None:
    out, _ = resize_max_side(np.zeros(shape, dtype=np.uint8), 1920)
    assert out.shape[:2] == expected
