"""End-to-end analysis of one shelf image: preprocess → detect → post-process → alert."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import numpy as np

from shelfmon.config import Settings
from shelfmon.inference.detector import Detector
from shelfmon.postprocess import (
    PostprocessConfig,
    StoreROI,
    rescale_boxes,
    run_postprocess,
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
    image: np.ndarray,
    store_id: str,
    detector: Detector,
    settings: Settings,
    *,
    roi: StoreROI | None = None,
    postprocess_config: PostprocessConfig | None = None,
) -> AnalysisResult:
    """Run full single-image shelf analysis returning boxes in original-image pixel coordinates."""
    orig_h, orig_w = image.shape[:2]
    timer = StepTimer()

    with timer.step("preprocess"):
        resized, _ = resize_max_side(image, settings.max_image_side)
        resized_h, resized_w = resized.shape[:2]

    with timer.step("inference"):
        raw_boxes = detector.detect(resized, conf=settings.conf_threshold)

    with timer.step("postprocess"):
        boxes = rescale_boxes(
            raw_boxes,
            from_size=(resized_w, resized_h),
            to_size=(orig_w, orig_h),
            clamp=True,
        )
        cfg = postprocess_config or PostprocessConfig.from_settings(settings)
        output = run_postprocess(
            boxes,
            image_width=float(orig_w),
            image_height=float(orig_h),
            config=cfg,
            roi=roi,
        )

    return AnalysisResult(
        analysis_id=uuid.uuid4().hex,
        store_id=store_id,
        created_at=datetime.now(UTC),
        model_version=detector.version,
        product_count=len(output.boxes),
        boxes=output.boxes,
        rows=output.rows,
        gaps=output.gaps,
        fill_rate=output.fill_rate,
        alert=output.alert,
        timings_ms=timer.timings_ms,
    )
