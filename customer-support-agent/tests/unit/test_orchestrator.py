from __future__ import annotations

import json
from unittest.mock import Mock

import httpx
import pytest

from support_agent.llm import LLMResponse, MockLLM, ToolCall, Usage
from support_agent.llm.base import LLMError
from support_agent.memory import InMemorySessionStore
from support_agent.orchestrator import ORDER_TOOL, AgentOrchestrator
from support_agent.retrieval.retriever import RetrievedChunk
from support_agent.schemas import ChatRequest
from support_agent.tools.order_status import GetOrderStatusArgs
from support_agent.tools.registry import Tool, ToolRegistry

ORDER_ARGS = {"order_id": "SX-000001", "email": "customer001@example.com"}
ORDER_QUESTION = "What is the status of order SX-000001? Email: customer001@example.com."
EVIDENCE = "Free shipping from 300,000 VND."


def _orchestrator(
    llm: MockLLM, lookup: Mock | None = None, chunks: list[RetrievedChunk] | None = None
) -> AgentOrchestrator:
    registry = ToolRegistry()
    if lookup is not None:
        registry.register(Tool(ORDER_TOOL, "Look up the order.", GetOrderStatusArgs, lookup))
    return AgentOrchestrator(
        llm=llm,
        retriever=Mock(search=Mock(return_value=chunks or [])),
        tools=registry,
        sessions=InMemorySessionStore(),
        system_prompt="Policy context: {context}",
        params={
            "llm": {"price_per_million_input_tokens": 1.0, "price_per_million_output_tokens": 2.0}
        },
    )


def _ask(orch: AgentOrchestrator, message: str):
    return orch.handle(ChatRequest(session_id="s", message=message))


def _scripted_lookup(args: dict[str, str] = ORDER_ARGS) -> MockLLM:
    return MockLLM([LLMResponse(tool_calls=[ToolCall("call-1", ORDER_TOOL, args)])])


def test_policy_answer_has_verbatim_citation_and_trace(caplog: pytest.LogCaptureFixture) -> None:
    llm = MockLLM(
        [
            LLMResponse(
                json.dumps({"answer": EVIDENCE, "evidence": [{"source": "S1", "quote": EVIDENCE}]}),
                usage=Usage(10, 3, available=True),
            )
        ]
    )
    orch = _orchestrator(llm, chunks=[RetrievedChunk("shipping", EVIDENCE, 0.95, "chunk-1")])
    with caplog.at_level("INFO", logger="support_agent.trace"):
        response = _ask(orch, "Shipping fee?")
    assert response.answer == EVIDENCE
    assert len(orch.sessions.history("s", max_turns=5)) == 2
    assert response.citations[0].doc_id == "shipping"
    assert response.citations[0].snippet == EVIDENCE
    assert "chunk-1" in caplog.records[0].trace["retrieved_chunk_ids"]
    assert caplog.records[0].trace["tokens_in"] == 10
    assert caplog.records[0].trace["cost_usd"] == pytest.approx(16 / 1_000_000)


@pytest.mark.parametrize("source,quote", [("S9", EVIDENCE), ("S1", "invented"), ("S1", "")])
def test_bad_policy_citation_returns_fallback(source: str, quote: str) -> None:
    llm = MockLLM(
        [
            LLMResponse(
                json.dumps(
                    {
                        "answer": "An unsupported price",
                        "evidence": [{"source": source, "quote": quote}],
                    }
                )
            )
        ]
    )
    orch = _orchestrator(llm, chunks=[RetrievedChunk("shipping", EVIDENCE, 0.8)])
    response = _ask(orch, "Shipping fee?")
    assert "could not find" in response.answer
    assert not response.citations
    assert not response.handoff


def test_empty_retrieval_does_not_invoke_model() -> None:
    llm = MockLLM()
    response = _ask(_orchestrator(llm), "Phí giao hàng là bao nhiêu?")
    assert "chưa tìm thấy" in response.answer
    assert not llm.calls


@pytest.mark.parametrize(
    "email", ["", " Email: invalid-email.", " Email: a@b.", " Email: two.example."]
)
def test_order_lookup_requires_valid_email(email: str) -> None:
    lookup = Mock()
    llm = _scripted_lookup()
    response = _ask(_orchestrator(llm, lookup), f"Where is order SX-000001?{email}")
    assert "email" in response.answer
    assert response.actions == []
    assert not llm.calls
    lookup.assert_not_called()


def test_order_lookup_declines_model_supplied_different_arguments() -> None:
    lookup = Mock()
    llm = _scripted_lookup({**ORDER_ARGS, "email": "other@example.com"})
    response = _ask(_orchestrator(llm, lookup), ORDER_QUESTION)
    assert response.actions == []
    lookup.assert_not_called()


def test_order_lookup_uses_only_verified_fields() -> None:
    lookup = Mock(return_value={**ORDER_ARGS, "status": "confirmed", "total_vnd": 999999})
    orch = _orchestrator(_scripted_lookup(), lookup)
    response = _ask(orch, ORDER_QUESTION)
    lookup.assert_called_once_with(**ORDER_ARGS)
    assert response.answer == "Order SX-000001 is confirmed."
    assert response.actions[0].ok
    assert response.actions[0].arguments == {"order_id": "SX-000001"}
    assert "customer001" not in response.model_dump_json()
    assert "customer001" not in orch.sessions.history("s", max_turns=5)[0].content


def test_order_denial_and_timeout_have_safe_responses() -> None:
    request = httpx.Request("GET", "http://localhost:8001")
    error = httpx.HTTPStatusError("denied", request=request, response=httpx.Response(404))
    first = _ask(_orchestrator(_scripted_lookup(), Mock(side_effect=error)), ORDER_QUESTION)
    second = _ask(
        _orchestrator(
            _scripted_lookup(), Mock(return_value={"error": "not_found", "status": "confirmed"})
        ),
        ORDER_QUESTION,
    )
    timeout = _ask(
        _orchestrator(_scripted_lookup(), Mock(side_effect=httpx.ReadTimeout("retry"))),
        ORDER_QUESTION,
    )
    assert first.answer == second.answer
    assert first.actions[0].summary == second.actions[0].summary == "not_found"
    assert not first.actions[0].ok and not second.actions[0].ok
    assert "confirmed" not in second.model_dump_json()
    assert timeout.actions[0].summary == "unavailable"


def test_provider_error_returns_safe_response(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = MockLLM()
    monkeypatch.setattr(llm, "complete", Mock(side_effect=LLMError("internal detail")))
    orch = _orchestrator(llm, chunks=[RetrievedChunk("shipping", EVIDENCE, 0.8)])
    response = _ask(orch, "Shipping fee?")
    assert "try again" in response.answer
    assert "internal detail" not in response.model_dump_json()


@pytest.mark.skip(reason="TODO(FR-06): enable when handoff rules are implemented")
def test_handoff_when_customer_asks_for_human() -> None: ...
