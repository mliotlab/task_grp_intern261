"""Mock Order API (FR-04): a separate REST service backed by synthetic orders.

Generate data first:
    python scripts/generate_orders.py --n 100 --seed 42 --today 2026-11-30 --out var/orders.json
Run locally:
    uvicorn services.order_api.main:app --reload --port 8001
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr, ValidationError

from support_agent import __version__
from support_agent.config import get_settings

logger = logging.getLogger(__name__)
_EMAIL_QUERY_RE = re.compile(r"(email=)[^&\s]+", re.IGNORECASE)


class OrderFixtureError(RuntimeError):
    """Raised when the synthetic order fixture is missing or unreadable."""


class RedactEmailFilter(logging.Filter):
    """Mask email query params in uvicorn access logs (NFR-03)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _EMAIL_QUERY_RE.sub(r"\1[REDACTED]", record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    (_EMAIL_QUERY_RE.sub(r"\1[REDACTED]", arg) if isinstance(arg, str) else arg)
                    for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: (_EMAIL_QUERY_RE.sub(r"\1[REDACTED]", v) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
        return True


def _install_access_log_filter() -> None:
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactEmailFilter) for f in access_logger.filters):
        access_logger.addFilter(RedactEmailFilter())


_install_access_log_filter()


class Order(BaseModel):
    order_id: str
    email: EmailStr
    status: Literal["pending", "confirmed", "shipped", "delivered", "cancelled", "returned"]
    items: list[str]
    total_vnd: int
    placed_on: date
    estimated_delivery: date | None = None
    carrier: str | None = None


class OrderStatus(BaseModel):
    order_id: str
    status: str
    estimated_delivery: date | None = None
    carrier: str | None = None


def normalize_email(email: str) -> str:
    """Normalize email consistently across fixture comparison and API input."""
    return email.strip().lower()


@lru_cache
def load_orders() -> dict[str, Order]:
    path = get_settings().orders_file
    if not path.exists():
        logger.error("Order fixture file not found: %s", path)
        raise OrderFixtureError(f"Order fixture not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Order fixture must be a JSON list")
        return {o["order_id"]: Order.model_validate(o) for o in raw}
    except (
        OSError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        logger.error("Failed to load order fixture: %s", type(exc).__name__)
        raise OrderFixtureError("Order fixture is invalid") from exc


app = FastAPI(title="ShopX Order API (mock)", version=__version__)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str | int]:
    try:
        orders_loaded = len(load_orders())
    except OrderFixtureError:
        orders_loaded = 0
    return {"status": "ok", "orders_loaded": orders_loaded}


@app.get("/v1/orders/{order_id}", response_model=OrderStatus, tags=["orders"])
def get_order(order_id: str, email: EmailStr = Query(...)) -> OrderStatus:
    """Return the order status only if `order_id` and `email` match (FR-04, NFR-03)."""
    try:
        orders = load_orders()
    except OrderFixtureError as exc:
        raise HTTPException(status_code=503, detail="Order data unavailable") from exc

    order = orders.get(order_id)
    if order is None or normalize_email(str(order.email)) != normalize_email(str(email)):
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderStatus(
        order_id=order.order_id,
        status=order.status,
        estimated_delivery=order.estimated_delivery,
        carrier=order.carrier,
    )
