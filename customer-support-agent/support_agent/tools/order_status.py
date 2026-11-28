"""Tool `get_order_status(order_id, email)` (FR-04)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel, EmailStr, Field

from support_agent.config import get_settings
from support_agent.tools.registry import Tool

logger = logging.getLogger(__name__)

DEFAULT_ORDER_API_URL = "http://localhost:8001"
DEFAULT_TIMEOUT_SECONDS = 5.0


class GetOrderStatusArgs(BaseModel):
    order_id: str = Field(pattern=r"^SX-\d{6}$", description="Order id, e.g. SX-000123")
    email: EmailStr = Field(description="Email used when placing the order")


def _resolve_order_api_url() -> str:
    env_url = os.getenv("ORDER_API_URL")
    if env_url:
        return env_url.rstrip("/")
    settings_url = getattr(get_settings(), "order_api_url", DEFAULT_ORDER_API_URL)
    return str(settings_url).rstrip("/")


def _resolve_timeout() -> float:
    raw = os.getenv("ORDER_API_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def get_order_status(order_id: str, email: str) -> dict[str, Any]:
    """Call the mock Order API. Only return data when order_id AND email match (FR-04, NFR-03)."""
    base_url = _resolve_order_api_url()
    timeout = _resolve_timeout()
    normalized_email = email.strip().lower()

    try:
        response = httpx.get(
            f"{base_url}/v1/orders/{order_id}",
            params={"email": normalized_email},
            timeout=timeout,
        )
    except httpx.TimeoutException:
        logger.warning("Order API timeout for order_id=%s", order_id)
        return {"error": "upstream_timeout"}
    except httpx.HTTPError as exc:
        logger.warning(
            "Order API request failed for order_id=%s (%s)",
            order_id,
            type(exc).__name__,
        )
        return {"error": "upstream_error"}

    if response.status_code in (403, 404):
        return {"error": "not_found"}

    if response.status_code >= 400:
        logger.warning(
            "Order API returned status=%s for order_id=%s",
            response.status_code,
            order_id,
        )
        return {"error": "upstream_error"}

    try:
        data = response.json()
        return {
            "order_id": data["order_id"],
            "status": data["status"],
            "estimated_delivery": data.get("estimated_delivery"),
            "carrier": data.get("carrier"),
        }
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning(
            "Invalid Order API response for order_id=%s (%s)",
            order_id,
            type(exc).__name__,
        )
        return {"error": "upstream_error"}


TOOL = Tool(
    name="get_order_status",
    description="Look up the status of an order after verifying the customer's email.",
    args_model=GetOrderStatusArgs,
    func=get_order_status,
)
