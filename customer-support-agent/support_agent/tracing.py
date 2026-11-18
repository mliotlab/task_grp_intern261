"""Per-turn trace: tokens, cost, latency per step, tools called, retrieved chunks (NFR-07)."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field

logger = logging.getLogger("support_agent.trace")


@dataclass
class TurnTrace:
    session_id: str
    prompt_version: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    step_latency_ms: dict[str, float] = field(default_factory=dict)
    tools_called: list[str] = field(default_factory=list)
    retrieved_doc_ids: list[str] = field(default_factory=list)

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        """Time a named step: `with trace.step("retrieve"): ...`."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            self.step_latency_ms[name] = self.step_latency_ms.get(name, 0.0) + elapsed

    def add_usage(
        self, tokens_in: int, tokens_out: int, price_in_per_m: float, price_out_per_m: float
    ) -> None:
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.cost_usd += (tokens_in * price_in_per_m + tokens_out * price_out_per_m) / 1_000_000

    def emit(self) -> None:
        logger.info("turn_trace", extra={"trace": asdict(self)})
