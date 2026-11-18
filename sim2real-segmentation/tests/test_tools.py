from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from s2r_tools.figures import invalid_result_names, side_by_side
from s2r_tools.palette import CLASSES, PALETTE, colorize


def test_palette_matches_19_classes() -> None:
    assert len(CLASSES) == len(PALETTE) == 19


def test_colorize_maps_ids_and_ignore() -> None:
    label = np.array([[0, 13], [255, 18]], dtype=np.uint8)
    rgb = colorize(label)
    assert rgb.shape == (2, 2, 3)
    assert tuple(rgb[0, 0]) == (128, 64, 128)  # road
    assert tuple(rgb[0, 1]) == (0, 0, 142)  # car
    assert tuple(rgb[1, 0]) == (0, 0, 0)  # ignore
    assert tuple(rgb[1, 1]) == (119, 11, 32)  # bicycle


def test_colorize_rejects_rgb_input() -> None:
    with pytest.raises(ValueError):
        colorize(np.zeros((2, 2, 3)))


def test_side_by_side_layout() -> None:
    img = Image.new("RGB", (64, 32))
    fig = side_by_side(img, np.zeros((16, 32), dtype=np.uint8), with_legend=False)
    assert fig.size == (128, 32)


def test_result_name_check(tmp_path: Path) -> None:
    for name in ["gta_01.png", "cs_12.png", "vn_03.png", "vietnam1.png", "gta_1.png"]:
        (tmp_path / name).touch()
    assert invalid_result_names(tmp_path) == ["gta_1.png", "vietnam1.png"]
