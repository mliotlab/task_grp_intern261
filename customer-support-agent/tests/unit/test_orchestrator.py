from __future__ import annotations

import pytest

from support_agent.llm import LLMResponse, MockLLM
from support_agent.memory import InMemorySessionStore
from support_agent.orchestrator import AgentOrchestrator
from support_agent.retrieval.retriever import NullRetriever
from support_agent.schemas import ChatRequest
from support_agent.tools.defaults import default_registry


def _orchestrator(llm: MockLLM) -> AgentOrchestrator:
    return AgentOrchestrator(
        llm=llm,
        retriever=NullRetriever(),
        tools=default_registry(),
        sessions=InMemorySessionStore(),
        system_prompt="system",
        params={},
    )


def test_returns_llm_answer_and_stores_history() -> None:
    llm = MockLLM([LLMResponse(content="Free shipping from 300,000 VND.")])
    orch = _orchestrator(llm)
    resp = orch.handle(ChatRequest(session_id="s", message="Shipping fee?"))
    assert resp.answer == "Free shipping from 300,000 VND."
    assert len(orch.sessions.history("s", max_turns=5)) == 2


@pytest.mark.skip(reason="TODO(FR-03): enable when RAG + citations are implemented")
def test_policy_answer_has_citation() -> None: ...


@pytest.mark.skip(reason="TODO(FR-04): enable when the tool-calling loop is implemented")
def test_order_lookup_requires_email() -> None: ...


@pytest.mark.skip(reason="TODO(FR-06): enable when handoff rules are implemented")
def test_handoff_when_customer_asks_for_human() -> None: ...
