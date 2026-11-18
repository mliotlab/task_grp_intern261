"""Mock Order API (FR-04): a separate REST service backed by synthetic orders.

Generate data first:  python scripts/generate_orders.py --out var/orders.json
Run locally:          uvicorn services.order_api.main:app --reload --port 8001
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr

from support_agent import __version__
from support_agent.config import get_settings


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


@lru_cache
def load_orders() -> dict[str, Order]:
    path = get_settings().orders_file
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {o["order_id"]: Order.model_validate(o) for o in raw}


app = FastAPI(title="ShopX Order API (mock)", version=__version__)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str | int]:
    return {"status": "ok", "orders_loaded": len(load_orders())}


@app.get("/v1/orders/{order_id}", response_model=OrderStatus, tags=["orders"])
def get_order(order_id: str, email: EmailStr = Query(...)) -> OrderStatus:
    """Return the order status only if `order_id` and `email` match.

    TODO(FR-04, NFR-03): look the order up in `load_orders()`; return the SAME 404 response
    for "order not found" and "email does not match" so callers cannot probe which orders exist.
    """
    raise HTTPException(status_code=501, detail="Not implemented yet (FR-04)")
