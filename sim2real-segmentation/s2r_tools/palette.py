"""The 19 Cityscapes evaluation classes shared by GTA5 → Cityscapes, with the official colours.

Using one palette for every figure keeps results comparable across members and weeks.
"""

from __future__ import annotations

import numpy as np

CLASSES: tuple[str, ...] = (
    "road", "sidewalk", "building", "wall", "fence", "pole", "traffic light", "traffic sign",
    "vegetation", "terrain", "sky", "person", "rider", "car", "truck", "bus", "train",
    "motorcycle", "bicycle",
)  # fmt: skip

PALETTE: tuple[tuple[int, int, int], ...] = (
    (128, 64, 128), (244, 35, 232), (70, 70, 70), (102, 102, 156), (190, 153, 153),
    (153, 153, 153), (250, 170, 30), (220, 220, 0), (107, 142, 35), (152, 251, 152),
    (70, 130, 180), (220, 20, 60), (255, 0, 0), (0, 0, 142), (0, 0, 70), (0, 60, 100),
    (0, 80, 100), (0, 0, 230), (119, 11, 32),
)  # fmt: skip

IGNORE_INDEX = 255


def colorize(label_map: np.ndarray) -> np.ndarray:
    """Map an HxW array of train ids (0–18, 255 = ignore) to an HxWx3 RGB uint8 image."""
    if label_map.ndim != 2:
        raise ValueError(f"expected a 2-D label map, got shape {label_map.shape}")
    lut = np.zeros((256, 3), dtype=np.uint8)
    lut[: len(PALETTE)] = np.array(PALETTE, dtype=np.uint8)
    return lut[label_map.astype(np.uint8)]
