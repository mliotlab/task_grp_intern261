"""Build the Week-3 result figures: input | prediction | legend, saved as `<domain>_<nn>.png`."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from s2r_tools.palette import CLASSES, PALETTE, colorize

RESULT_NAME = re.compile(r"^(gta|cs|vn)_\d{2}\.png$")


def legend(height: int, classes: tuple[str, ...] = CLASSES, width: int = 190) -> Image.Image:
    """Vertical colour legend for the 19 classes, scaled to `height` pixels."""
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    row = max(height // len(classes), 1)
    for i, (name, color) in enumerate(zip(classes, PALETTE)):
        y = i * row
        draw.rectangle([8, y + 2, 8 + row - 4, y + row - 2], fill=color)
        draw.text((row + 10, y + max(row // 2 - 6, 0)), name, fill="black")
    return img


def side_by_side(
    image: Image.Image, label_map: np.ndarray, with_legend: bool = True
) -> Image.Image:
    """Concatenate the RGB input, the colourised prediction and (optionally) the legend."""
    pred = Image.fromarray(colorize(label_map)).resize(image.size, Image.NEAREST)
    parts = [image.convert("RGB"), pred]
    if with_legend:
        parts.append(legend(image.height))
    canvas = Image.new("RGB", (sum(p.width for p in parts), image.height), "white")
    x = 0
    for p in parts:
        canvas.paste(p, (x, 0))
        x += p.width
    return canvas


def invalid_result_names(folder: Path) -> list[str]:
    """Return PNG files in `folder` that do not follow `gta_01.png` / `cs_01.png` / `vn_01.png`."""
    return sorted(p.name for p in folder.glob("*.png") if not RESULT_NAME.match(p.name))
