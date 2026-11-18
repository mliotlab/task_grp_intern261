"""Detector interface and implementations.

The API and post-processing depend only on `Detector`, so they can be tested with `FakeDetector`
and synthetic boxes — no GPU, no model weights, no ultralytics in CI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np

from shelfmon.schemas import BoundingBox


class Detector(Protocol):
    version: str

    def detect(self, image: np.ndarray, conf: float = 0.25) -> list[BoundingBox]:
        """`image` is an HxWx3 BGR uint8 array (OpenCV convention)."""
        ...


class FakeDetector:
    """Returns pre-defined boxes. For tests and for running the API without a model."""

    def __init__(self, boxes: list[BoundingBox] | None = None, version: str = "fake-0") -> None:
        self._boxes = boxes or []
        self.version = version

    def detect(self, image: np.ndarray, conf: float = 0.25) -> list[BoundingBox]:
        return [b for b in self._boxes if b.confidence >= conf]


class YoloDetector:
    """Ultralytics YOLO detector (requires `pip install -e ".[ml]"`)."""

    def __init__(self, weights: Path, version: str, device: str = "cpu", imgsz: int = 1024) -> None:
        from ultralytics import YOLO  # lazy import: heavy dependency

        self.model = YOLO(str(weights))
        self.version = version
        self.device = device
        self.imgsz = imgsz

    def detect(self, image: np.ndarray, conf: float = 0.25) -> list[BoundingBox]:
        """TODO(FR-01): run `self.model.predict(image, conf=conf, imgsz=self.imgsz,
        device=self.device, verbose=False)` and convert `result.boxes.xyxy` / `.conf` into
        BoundingBox objects. SKU-110K images are dense (~150 objects): raise `max_det`."""
        raise NotImplementedError


def load_detector(
    model_dir: Path, version: str, device: str = "cpu", imgsz: int = 1024
) -> Detector:
    """Load `models/<version>/weights.pt` from the model registry.

    TODO(NFR-06): verify the SHA-256 in `models/<version>/SHA256SUMS` before loading.
    """
    weights = model_dir / version / "weights.pt"
    if not weights.exists():
        raise FileNotFoundError(
            f"Model weights not found at {weights}. See models/README.md for the download link."
        )
    return YoloDetector(weights, version=version, device=device, imgsz=imgsz)
