"""Research pipeline: plan → retrieve → extract → write → verify citations (FR-05).

Each step is a small, separately testable function. The runner records progress after every step
so the UI can show it (FR-04) and a restarted worker can resume (NFR-04).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from workers.research.hybrid_retrieval import retrieve_hybrid


@dataclass
class Evidence:
    """A retrieved chunk associated with the sub-question that retrieved it."""

    sub_question: str
    chunk_id: str
    document_id: str
    filename: str
    text: str
    page: int | None = None
    section: str | None = None
    rrf_score: float = 0.0


@dataclass
class ResearchState:
    """State shared between Research Pipeline steps."""

    question: str
    collection_id: uuid.UUID
    owner_id: uuid.UUID
    sub_questions: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    report_markdown: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)


# ============================================================
# Step 1: Plan
# ============================================================


def plan(state: ResearchState) -> ResearchState:
    """TODO: ask the LLM to split the question into 3–5 sub-questions (JSON output, validated)."""
    raise NotImplementedError


# ============================================================
# Step 2: Hybrid Retrieval
# ============================================================


def retrieve(state: ResearchState) -> ResearchState:
    """Retrieve Hybrid Top-K evidence for every sub-question."""

    # 1. Validate required state.
    if not isinstance(state.collection_id, uuid.UUID):
        raise ValueError("Invalid collection_id.")

    if not isinstance(state.owner_id, uuid.UUID):
        raise ValueError("Invalid owner_id.")

    if not state.sub_questions:
        raise ValueError("No sub-questions available. Run plan() before retrieve().")

    # 2. Retrieve evidence for each sub-question.
    retrieved_evidence: list[Evidence] = []

    for sub_question in state.sub_questions:
        if not isinstance(sub_question, str) or not sub_question.strip():
            raise ValueError("Sub-questions must not be empty.")

        results = retrieve_hybrid(
            question=sub_question.strip(),
            collection_id=state.collection_id,
            owner_id=state.owner_id,
        )

        # 3. Convert retrieval results into Evidence objects.
        for result in results:
            retrieved_evidence.append(
                Evidence(
                    sub_question=sub_question,
                    chunk_id=result["chunk_id"],
                    document_id=result["document_id"],
                    filename=result["filename"],
                    text=result["text"],
                    page=result["page"],
                    section=result.get("section"),
                    rrf_score=float(result["rrf_score"]),
                )
            )

    # 4. Replace previous evidence to avoid duplicates
    # when the retrieval step is executed again.
    state.evidence = retrieved_evidence

    return state


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

        duration_ms = round(
            (time.perf_counter() - start) * 1000,
            1,
        )

        on_progress(name, "done", duration_ms)

    return state
