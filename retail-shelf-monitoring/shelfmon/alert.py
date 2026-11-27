"""Alerting (FR-04, FR-09)."""

from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

AlertReason = Literal["low_fill", "no_detection"]


def should_alert(fill_rate: float, threshold: float) -> bool:
    """An alert is raised when the fill rate is strictly below the threshold (default 80 %)."""
    return fill_rate < threshold


def determine_alert_reason(
    fill_rate: float,
    row_count: int,
    threshold: float,
) -> AlertReason | None:
    """Return the persisted Alert.reason per DESIGN.md & ADR-0002.

    - ``"no_detection"`` when zero valid rows exist (no detections and no ROI tiers).
    - ``"low_fill"`` when at least one row exists and ``fill_rate < threshold``.
    - ``None`` when no alert should be raised.
    """
    if row_count == 0:
        return "no_detection"
    if should_alert(fill_rate, threshold):
        return "low_fill"
    return None


def send_webhook(url: str, store_id: str, analysis_id: str, fill_rate: float) -> None:
    """TODO(FR-09): POST a JSON message to Telegram / Slack with httpx (timeout, 1 retry).
    Never let a webhook failure fail the analysis request – log and continue."""
    raise NotImplementedError("Webhook alerts are not implemented yet (FR-09)")
