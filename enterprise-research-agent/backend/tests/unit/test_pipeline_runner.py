from __future__ import annotations

from uuid import uuid4

from workers.research.pipeline import ResearchState, run_pipeline


def _step(tag: str):
    def fn(state: ResearchState) -> ResearchState:
        state.sub_questions.append(tag)
        return state

    return fn


def test_runner_reports_progress_in_order() -> None:
    events: list[tuple[str, str]] = []
    state = run_pipeline(
        ResearchState(
            question="q",
            collection_id="c",
            owner_id=uuid4(),
        ),
        on_progress=lambda step, status, _ms: events.append((step, status)),
        steps=[("a", _step("a")), ("b", _step("b"))],
    )
    assert state.sub_questions == ["a", "b"]
    assert events == [("a", "running"), ("a", "done"), ("b", "running"), ("b", "done")]


def test_runner_stops_when_cancelled() -> None:
    events: list[tuple[str, str]] = []
    run_pipeline(
        ResearchState(
            question="q",
            collection_id="c",
            owner_id=uuid4(),
        ),
        on_progress=lambda step, status, _ms: events.append((step, status)),
        steps=[("a", _step("a"))],
        is_cancelled=lambda: True,
    )
    assert events == [("a", "cancelled")]
