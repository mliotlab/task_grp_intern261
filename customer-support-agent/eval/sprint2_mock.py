"""Deterministic Sprint 2 fixtures for the real Chat API route."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from scripts.generate_orders import make_order
from support_agent.llm import LLMResponse, MockLLM, ToolCall
from support_agent.memory import InMemorySessionStore
from support_agent.orchestrator import ORDER_TOOL, AgentOrchestrator
from support_agent.prompts import load_system_prompt
from support_agent.retrieval.retriever import RetrievedChunk
from support_agent.tools.order_status import GetOrderStatusArgs
from support_agent.tools.registry import Tool, ToolRegistry

CI_IDS = (
    "pol-001",
    "pol-002",
    "pol-101",
    "pol-102",
    "pol-106",
    "pol-108",
    "ord-001",
    "ord-002",
    "ord-104",
    "ord-105",
)
POLICIES = {
    "pol-001": (
        "shipping-policy",
        "1–2 business days",
        "Standard delivery takes 1–2 business days.",
    ),
    "pol-002": (
        "shipping-policy",
        "25,000 VND standard shipping fee",
        "Phí giao tiêu chuẩn 25.000đ.",
    ),
    "pol-101": ("return-policy", "7 ngày lịch", "Khách có 7 ngày lịch, đến hết ngày 17."),
    "pol-102": ("refund-process", "1–3 ngày làm việc", "Hoàn về ví trong 1–3 ngày làm việc."),
    "pol-106": ("voucher-rules", "tối đa 1 mã ưu đãi", "Mỗi đơn áp dụng tối đa 1 mã ưu đãi."),
}
LOOKUPS = {
    "ord-001": ("SX-000001", "customer001@example.com"),
    "ord-104": ("SX-000003", "wronguser@example.com"),
    "ord-105": ("SX-999999", "customer001@example.com"),
}


@dataclass
class EvalRetriever:
    chunks: list[RetrievedChunk]

    def search(self, query: str, top_k: int = 4) -> list[RetrievedChunk]:
        return self.chunks[:top_k]


@dataclass
class EvalOrderTool:
    records: dict
    calls: list[dict[str, str]] = field(default_factory=list)

    def lookup(self, order_id: str, email: str) -> dict:
        self.calls.append({"order_id": order_id, "email": email})
        order = self.records.get(order_id)
        if not order or order["email"] != email:
            return {"error": "not_found"}
        return {
            field: order[field] for field in ("order_id", "status", "estimated_delivery", "carrier")
        }


def ci_orchestrator(
    case_id: str, kb_dir: Path, params: dict
) -> tuple[AgentOrchestrator, EvalOrderTool]:
    rng = random.Random(42)  # noqa: S311 - reproducible synthetic orders
    records = [make_order(i, rng, date(2026, 11, 30)) for i in range(1, 101)]
    order_tool = EvalOrderTool({row["order_id"]: row for row in records})
    registry = ToolRegistry()
    registry.register(
        Tool(ORDER_TOOL, "Verify a synthetic ShopX order.", GetOrderStatusArgs, order_tool.lookup)
    )
    chunks = []
    scripted = []
    if case_id in POLICIES or case_id == "pol-108":
        doc_id, quote, answer = POLICIES.get(case_id, ("refund-process", "", ""))
        policy_lines = (kb_dir / f"{doc_id}.md").read_text(encoding="utf-8").splitlines()
        snippet = next((line for line in policy_lines if quote and quote in line), "")
        if quote and not snippet:
            raise ValueError(f"{case_id}: expected fixture evidence is absent from {doc_id}")
        if not quote:
            snippet = next(line for line in policy_lines if "COD" in line)
        chunks.append(RetrievedChunk(doc_id, snippet, 1.0, f"mock-{doc_id}"))
        evidence = [{"source": "S1", "quote": quote}] if quote else []
        scripted.append(LLMResponse(json.dumps({"answer": answer, "evidence": evidence})))
    elif case_id in LOOKUPS:
        order_id, email = LOOKUPS[case_id]
        arguments = {"order_id": order_id, "email": email}
        scripted.append(LLMResponse(tool_calls=[ToolCall("mock-call", ORDER_TOOL, arguments)]))

    return AgentOrchestrator(
        llm=MockLLM(scripted),
        retriever=EvalRetriever(chunks),
        tools=registry,
        sessions=InMemorySessionStore(),
        system_prompt=load_system_prompt("v2"),
        params=params,
        prompt_version="v2",
        model="mock",
    ), order_tool
