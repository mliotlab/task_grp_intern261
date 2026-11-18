"""Alerting (FR-04, FR-09)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def should_alert(fill_rate: float, threshold: float) -> bool:
    """An alert is raised when the fill rate is strictly below the threshold (default 80 %)."""
    return fill_rate < threshold


def send_webhook(url: str, store_id: str, analysis_id: str, fill_rate: float) -> None:
    """TODO(FR-09): POST a JSON message to Telegram / Slack with httpx (timeout, 1 retry).
    Never let a webhook failure fail the analysis request – log and continue."""
    raise NotImplementedError("Webhook alerts are not implemented yet (FR-09)")
