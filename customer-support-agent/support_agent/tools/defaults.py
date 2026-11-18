"""Build the default tool registry used by the Chat API."""

from __future__ import annotations

from support_agent.tools import order_status, ticket
from support_agent.tools.registry import ToolRegistry


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(order_status.TOOL)
    registry.register(ticket.CREATE_TICKET)
    registry.register(ticket.HANDOFF)
    return registry
