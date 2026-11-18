from __future__ import annotations

import numpy as np

from shelfmon.schemas import BoundingBox, Gap

PRODUCT_COLOR = (0, 200, 0)  # BGR green
GAP_COLOR = (0, 0, 255)  # BGR red


def draw_annotations(image: np.ndarray, boxes: list[BoundingBox], gaps: list[Gap]) -> np.ndarray:
    """Return a copy of `image` with boxes outlined and gaps filled semi-transparently (FR-02).

    TODO(FR-02): use cv2.rectangle for boxes; draw gaps on an overlay and cv2.addWeighted(α≈0.35);
    add a legend and the fill rate as text.
    """
    raise NotImplementedError("draw_annotations is not implemented yet (FR-02)")
