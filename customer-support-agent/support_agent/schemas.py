"""Public data contracts of the Chat API (FR-01)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)


class Citation(BaseModel):
    doc_id: str = Field(description="Source document id, e.g. 'shipping-policy'")
    snippet: str = Field(description="The retrieved passage the answer relies on")
    score: float | None = None


class AgentAction(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    summary: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    handoff: bool = False
    ticket_id: str | None = None
    trace_id: str
