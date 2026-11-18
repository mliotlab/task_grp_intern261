"""Tool `get_order_status(order_id, email)` (FR-04)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field

from support_agent.tools.registry import Tool


class GetOrderStatusArgs(BaseModel):
    order_id: str = Field(pattern=r"^SX-\d{6}$", description="Order id, e.g. SX-000123")
    email: EmailStr = Field(description="Email used when placing the order")


def get_order_status(order_id: str, email: str) -> dict[str, Any]:
    """Call the mock Order API. Only return data when order_id AND email match.

    TODO(FR-04):
      - GET {ORDER_API_URL}/v1/orders/{order_id}?email=... with httpx and a short timeout.
      - Map 404/403 to a safe message that does not reveal whether the order exists (NFR-03).
    """
    raise NotImplementedError("get_order_status is not implemented yet (FR-04)")


TOOL = Tool(
    name="get_order_status",
    description="Look up the status of an order after verifying the customer's email.",
    args_model=GetOrderStatusArgs,
    func=get_order_status,
)
