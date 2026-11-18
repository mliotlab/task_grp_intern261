"""Measure per-step latency for structured logs (NFR-05)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager


class StepTimer:
    def __init__(self) -> None:
        self.timings_ms: dict[str, float] = {}

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.timings_ms[name] = round((time.perf_counter() - start) * 1000, 2)
