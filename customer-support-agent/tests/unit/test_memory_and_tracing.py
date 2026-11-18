from __future__ import annotations

from support_agent.llm import Message
from support_agent.memory import InMemorySessionStore
from support_agent.tracing import TurnTrace


def test_history_is_limited_to_last_turns() -> None:
    store = InMemorySessionStore()
    for i in range(5):
        store.append("s", Message("user", f"q{i}"), Message("assistant", f"a{i}"))
    hist = store.history("s", max_turns=2)
    assert [m.content for m in hist] == ["q3", "a3", "q4", "a4"]


def test_trace_accumulates_cost_and_latency() -> None:
    trace = TurnTrace(session_id="s", prompt_version="v1")
    with trace.step("llm"):
        pass
    trace.add_usage(1_000_000, 500_000, price_in_per_m=0.15, price_out_per_m=0.60)
    assert trace.tokens_in == 1_000_000
    assert round(trace.cost_usd, 4) == 0.45
    assert "llm" in trace.step_latency_ms
