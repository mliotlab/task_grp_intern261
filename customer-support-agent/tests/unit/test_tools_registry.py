from __future__ import annotations

import pytest
from pydantic import BaseModel

from support_agent.tools import Tool, ToolError, ToolRegistry
from support_agent.tools.defaults import default_registry


class EchoArgs(BaseModel):
    text: str


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo text", EchoArgs, lambda text: {"echo": text}))
    return reg


def test_call_validates_and_runs() -> None:
    assert _registry().call("echo", {"text": "hi"}) == {"echo": "hi"}


def test_unknown_tool_raises() -> None:
    with pytest.raises(ToolError, match="Unknown tool"):
        _registry().call("nope", {})


def test_invalid_arguments_raise() -> None:
    with pytest.raises(ToolError, match="Invalid arguments"):
        _registry().call("echo", {"text": 123})


def test_duplicate_registration_rejected() -> None:
    reg = _registry()
    with pytest.raises(ValueError):
        reg.register(Tool("echo", "dup", EchoArgs, lambda text: text))


def test_default_registry_exposes_required_tools() -> None:
    reg = default_registry()
    assert reg.names() == ["create_ticket", "get_order_status", "handoff_to_human"]
    for schema in reg.schemas():
        assert schema["type"] == "function"
        assert "parameters" in schema["function"]


def test_order_status_rejects_bad_order_id_before_calling_service() -> None:
    with pytest.raises(ToolError):
        default_registry().call(
            "get_order_status", {"order_id": "123", "email": "customer001@example.com"}
        )
