"""End-to-end analysis of one shelf image: preprocess → detect → post-process → alert."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import numpy as np

from shelfmon.alert import should_alert
from shelfmon.config import Settings
from shelfmon.inference.detector import Detector
from shelfmon.postprocess import (
    filter_by_confidence,
    find_gaps,
    group_into_rows,
    image_fill_rate,
    row_fill_rate,
)
from shelfmon.schemas import AnalysisResult
from shelfmon.timing import StepTimer


def resize_max_side(image: np.ndarray, max_side: int) -> tuple[np.ndarray, float]:
    """Downscale so the longest side is ≤ max_side. Returns (image, scale)."""
    import cv2

    h, w = image.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        image = cv2.resize(
            image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA
        )
    return image, scale


def analyze_image(
    image: np.ndarray, store_id: str, detector: Detector, settings: Settings
) -> AnalysisResult:
    timer = StepTimer()
    with timer.step("preprocess"):
        image, _ = resize_max_side(image, settings.max_image_side)
    with timer.step("inference"):
        boxes = detector.detect(image, conf=settings.conf_threshold)
    with timer.step("postprocess"):
        boxes = filter_by_confidence(boxes, settings.conf_threshold)
        rows = group_into_rows(boxes)
        # TODO(FR-10): use a configured ROI instead of the full image width.
        shelf_x1, shelf_x2 = 0.0, float(image.shape[1])
        for row in rows:
            row.gaps = find_gaps(row, shelf_x1, shelf_x2, settings.gap_width_multiplier)
            row.fill_rate = row_fill_rate(row, shelf_x1, shelf_x2)
        fill = image_fill_rate(rows)

    return AnalysisResult(
        analysis_id=uuid.uuid4().hex,
        store_id=store_id,
        created_at=datetime.now(UTC),
        model_version=detector.version,
        product_count=len(boxes),
        boxes=boxes,
        rows=rows,
        gaps=[g for r in rows for g in r.gaps],
        fill_rate=fill,
        alert=should_alert(fill, settings.fill_rate_alert_threshold),
        timings_ms=timer.timings_ms,
    )
