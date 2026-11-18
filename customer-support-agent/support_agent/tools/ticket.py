"""Tools `create_ticket` (FR-05) and `handoff_to_human` (FR-06)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from support_agent.tools.registry import Tool


class TicketCategory(StrEnum):
    SHIPPING = "shipping"
    RETURN_REFUND = "return_refund"
    PAYMENT = "payment"
    WARRANTY = "warranty"
    ACCOUNT = "account"
    OTHER = "other"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CreateTicketArgs(BaseModel):
    category: TicketCategory
    summary: str = Field(min_length=10, max_length=1000)
    priority: TicketPriority = TicketPriority.MEDIUM


class HandoffArgs(BaseModel):
    reason: str = Field(description="Why the conversation is handed off to a human agent")
    conversation_summary: str = Field(min_length=10, max_length=2000)


def create_ticket(category: str, summary: str, priority: str) -> dict[str, Any]:
    """Persist a ticket and return its id.

    TODO(FR-05): store in SQLite via SQLAlchemy (Ticket Service); return {"ticket_id": "TCK-..."}.
    """
    raise NotImplementedError("create_ticket is not implemented yet (FR-05)")


def handoff_to_human(reason: str, conversation_summary: str) -> dict[str, Any]:
    """Create a HIGH-priority ticket with the conversation summary.

    TODO(FR-06): reuse create_ticket with priority=high and mark the session as handed off.
    """
    raise NotImplementedError("handoff_to_human is not implemented yet (FR-06)")


CREATE_TICKET = Tool(
    name="create_ticket",
    description="Create a support ticket and return its id to the customer.",
    args_model=CreateTicketArgs,
    func=create_ticket,
)

HANDOFF = Tool(
    name="handoff_to_human",
    description=(
        "Transfer the conversation to a human agent when the customer asks for a person, is very "
        "upset, the request is out of scope, or the agent could not help after 2 turns."
    ),
    args_model=HandoffArgs,
    func=handoff_to_human,
)
