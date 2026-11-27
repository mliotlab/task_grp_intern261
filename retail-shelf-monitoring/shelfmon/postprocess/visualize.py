"""In-memory annotation rendering for detected products, gaps, and fill rates (FR-02)."""

from __future__ import annotations

import cv2
import numpy as np

from shelfmon.schemas import BoundingBox, Gap, ShelfRow

PRODUCT_COLOR = (0, 200, 0)  # BGR green
GAP_COLOR = (0, 0, 255)  # BGR red
SHELF_COLOR = (255, 180, 0)  # BGR cyan-blue
ROW_TEXT_COLOR = (255, 255, 255)  # BGR white
HUD_BG_COLOR = (20, 20, 20)  # BGR dark charcoal
ALERT_COLOR = (0, 60, 255)  # BGR orange-red
OK_COLOR = (0, 200, 0)  # BGR green


def draw_annotations(
    image: np.ndarray,
    boxes: list[BoundingBox],
    gaps: list[Gap],
    *,
    fill_rate: float | None = None,
    rows: list[ShelfRow] | None = None,
    shelf_polygon: list[tuple[float, float]] | None = None,
    alert: bool | None = None,
    gap_alpha: float = 0.35,
) -> np.ndarray:
    """Return a copy of ``image`` with product boxes, semi-transparent gaps, and HUD legend.

    Pure in-memory renderer (no file I/O). Scales line widths and text size with image
    resolution so both small synthetic images and high-resolution shelf photos remain readable.
    """
    canvas = image.copy()
    if canvas.ndim == 2:
        canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)

    h, w = canvas.shape[:2]
    max_side = max(h, w, 1)
    thickness = max(1, round(max_side / 500))
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.45, min(1.6, max_side / 1600.0))
    text_thickness = max(1, round(font_scale * 2))

    # Optional shelf outer boundary polygon
    if shelf_polygon and len(shelf_polygon) >= 3:
        pts = np.array([[round(x), round(y)] for x, y in shelf_polygon], dtype=np.int32)
        cv2.polylines(canvas, [pts], isClosed=True, color=SHELF_COLOR, thickness=max(1, thickness))

    # Semi-transparent gap fill overlay
    if gaps:
        alpha = max(0.0, min(1.0, gap_alpha))
        overlay = canvas.copy()
        for gap in gaps:
            pt1 = (round(gap.x1), round(gap.y1))
            pt2 = (round(gap.x2), round(gap.y2))
            cv2.rectangle(overlay, pt1, pt2, GAP_COLOR, thickness=-1)
        cv2.addWeighted(overlay, alpha, canvas, 1.0 - alpha, 0.0, dst=canvas)

    # Product bounding boxes
    for box in boxes:
        pt1 = (round(box.x1), round(box.y1))
        pt2 = (round(box.x2), round(box.y2))
        cv2.rectangle(canvas, pt1, pt2, PRODUCT_COLOR, thickness=thickness)

    # Crisp gap borders and row labels
    for gap in gaps:
        pt1 = (round(gap.x1), round(gap.y1))
        pt2 = (round(gap.x2), round(gap.y2))
        cv2.rectangle(canvas, pt1, pt2, GAP_COLOR, thickness=max(2, thickness + 1))
        label = f"GAP R{gap.row_index}"
        text_y = max(round(gap.y1) - 6, round(18 * font_scale))
        text_x = max(0, round(gap.x1) + 2)
        cv2.putText(
            canvas,
            label,
            (text_x, text_y),
            font,
            font_scale * 0.75,
            GAP_COLOR,
            text_thickness,
            cv2.LINE_AA,
        )

    # Optional per-row fill-rate labels along the left margin
    if rows:
        for row in rows:
            tag = f"R{row.index}: {row.fill_rate * 100:.0f}%"
            ty = max(round(20 * font_scale), min(h - 6, round(0.5 * (row.y1 + row.y2))))
            cv2.putText(
                canvas,
                tag,
                (8, ty),
                font,
                font_scale * 0.7,
                (0, 0, 0),
                text_thickness + 2,
                cv2.LINE_AA,
            )
            cv2.putText(
                canvas,
                tag,
                (8, ty),
                font,
                font_scale * 0.7,
                ROW_TEXT_COLOR,
                text_thickness,
                cv2.LINE_AA,
            )

    # HUD summary & legend banner at top-left
    lines = [f"Products: {len(boxes)} | Gaps: {len(gaps)}"]
    if fill_rate is not None:
        status = ""
        if alert is not None:
            status = " [ALERT: LOW STOCK]" if alert else " [OK]"
        lines.append(f"Fill Rate: {fill_rate * 100:.1f}%{status}")
    lines.append("Legend: Green=Product  Red=Empty Gap")

    pad = max(8, round(10 * font_scale))
    line_gap = max(6, round(8 * font_scale))
    sizes = [cv2.getTextSize(line, font, font_scale, text_thickness)[0] for line in lines]
    banner_w = min(w - 2 * pad, max(sz[0] for sz in sizes) + 2 * pad)
    banner_h = min(h - 2 * pad, sum(sz[1] for sz in sizes) + line_gap * (len(lines) - 1) + 2 * pad)

    if banner_w > 0 and banner_h > 0:
        hud_overlay = canvas.copy()
        cv2.rectangle(hud_overlay, (pad, pad), (pad + banner_w, pad + banner_h), HUD_BG_COLOR, -1)
        cv2.addWeighted(hud_overlay, 0.72, canvas, 0.28, 0.0, dst=canvas)

        cursor_y = pad + pad
        for idx, (line, (_, lh)) in enumerate(zip(lines, sizes, strict=True)):
            cursor_y += lh
            color = ROW_TEXT_COLOR
            if idx == 1 and alert is not None:
                color = ALERT_COLOR if alert else OK_COLOR
            cv2.putText(
                canvas,
                line,
                (pad + pad, cursor_y),
                font,
                font_scale,
                color,
                text_thickness,
                cv2.LINE_AA,
            )
            cursor_y += line_gap

    return canvas
