"""Research pipeline: plan → retrieve → extract → write → verify citations (FR-05).

Each step is a small, separately testable function. The runner records progress after every step
so the UI can show it (FR-04) and a restarted worker can resume (NFR-04).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    sub_question: str
    chunk_id: str
    document_id: str
    text: str
    page: int | None = None
    score: float = 0.0


@dataclass
class ResearchState:
    question: str
    collection_id: str
    sub_questions: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    report_markdown: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)


def plan(state: ResearchState) -> ResearchState:
    """TODO: ask the LLM to split the question into 3–5 sub-questions (JSON output, validated)."""
    raise NotImplementedError


def retrieve(state: ResearchState) -> ResearchState:
    """TODO: pgvector similarity search per sub-question, filtered by collection + owner (FR-07)."""
    raise NotImplementedError


def extract(state: ResearchState) -> ResearchState:
    """TODO: extract key points from evidence, each tied to a chunk_id."""
    raise NotImplementedError


def write(state: ResearchState) -> ResearchState:
    """TODO: write the report (Summary / Findings / Conclusion) with [n] citation markers."""
    raise NotImplementedError


def verify_citations(state: ResearchState) -> ResearchState:
    """TODO(NFR-01): drop or flag claims whose cited chunk does not support them."""
    raise NotImplementedError


STEPS: list[tuple[str, Callable[[ResearchState], ResearchState]]] = [
    ("plan", plan),
    ("retrieve", retrieve),
    ("extract", extract),
    ("write", write),
    ("verify_citations", verify_citations),
]

ProgressCallback = Callable[[str, str, float | None], None]


def run_pipeline(
    state: ResearchState,
    on_progress: ProgressCallback,
    steps: list[tuple[str, Callable[[ResearchState], ResearchState]]] = STEPS,
    is_cancelled: Callable[[], bool] = lambda: False,
) -> ResearchState:
    """Run steps in order, reporting (step, status, duration_ms) after each one."""
    for name, step in steps:
        if is_cancelled():
            on_progress(name, "cancelled", None)
            break
        on_progress(name, "running", None)
        start = time.perf_counter()
        state = step(state)
        on_progress(name, "done", round((time.perf_counter() - start) * 1000, 1))
    return state
