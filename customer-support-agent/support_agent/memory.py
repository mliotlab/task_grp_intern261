"""Conversation memory per session (FR-07)."""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from support_agent.llm.base import Message


class SessionStore(Protocol):
    def history(self, session_id: str, max_turns: int) -> list[Message]: ...
    def append(self, session_id: str, *messages: Message) -> None: ...


class InMemorySessionStore:
    """Process-local store. Good for dev and tests; lost on restart.

    TODO(FR-07): add a SQLite-backed implementation so sessions survive restarts.
    """

    def __init__(self) -> None:
        self._data: dict[str, list[Message]] = defaultdict(list)

    def history(self, session_id: str, max_turns: int) -> list[Message]:
        # One turn ≈ one user message + everything until the next user message.
        msgs = self._data[session_id]
        user_idx = [i for i, m in enumerate(msgs) if m.role == "user"]
        if len(user_idx) <= max_turns:
            return list(msgs)
        return list(msgs[user_idx[-max_turns] :])

    def append(self, session_id: str, *messages: Message) -> None:
        self._data[session_id].extend(messages)
