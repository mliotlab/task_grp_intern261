"""Deterministic fake LLM for unit tests and CI (no network, no cost)."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Any

from support_agent.llm.base import LLMResponse, Message, Usage


class MockLLM:
    """Return scripted responses in order; fall back to a fixed answer once the script is empty."""

    def __init__(self, script: Iterable[LLMResponse] = (), default: str = "[mock] answer") -> None:
        self._script: deque[LLMResponse] = deque(script)
        self._default = default
        self.calls: list[list[Message]] = []

    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        *,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> LLMResponse:
        self.calls.append(list(messages))
        if self._script:
            return self._script.popleft()
        prompt_tokens = sum(len(m.content.split()) for m in messages)
        return LLMResponse(content=self._default, usage=Usage(prompt_tokens, 3, available=True))
