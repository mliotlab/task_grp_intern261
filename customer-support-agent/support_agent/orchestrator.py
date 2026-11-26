"""Ground policy answers in retrieved text and authorize Sprint 2 order tool calls."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from support_agent.guardrails import check_input
from support_agent.llm.base import LLMClient, LLMError, LLMResponse, Message
from support_agent.memory import SessionStore
from support_agent.retrieval.retriever import RetrievedChunk, Retriever
from support_agent.schemas import AgentAction, ChatRequest, ChatResponse, Citation
from support_agent.tools.order_status import GetOrderStatusArgs
from support_agent.tools.registry import ToolError, ToolRegistry
from support_agent.tracing import TurnTrace

ORDER_TOOL = "get_order_status"
ORDER_ID = re.compile(r"\bSX-[0-9]{6}\b", re.IGNORECASE)
EMAIL = re.compile(r"\b[\w.!#$%&'*+/=?^_~-]+@[\w-]+(?:\.[\w-]+)+\b")
ORDER_REQUEST = re.compile(
    r"\b(?:tra cuu (?:don|trang thai)|trang thai don|ma don|don hang.{0,15}o dau"
    r"|kiem tra.{0,30}don|order status|track (?:my |an |the )?order"
    r"|where is (?:my |the )?order|look up (?:my |the )?order)\b"
)


class PolicyEvidence(BaseModel):
    source: str
    quote: str = Field(min_length=1)


class PolicyReply(BaseModel):
    answer: str
    evidence: list[PolicyEvidence]


class VerifiedOrder(BaseModel):
    order_id: str
    status: Literal["pending", "confirmed", "shipped", "delivered", "cancelled", "returned"]
    estimated_delivery: date | None = None
    carrier: str | None = Field(default=None, max_length=128)


VIETNAMESE_STATUS = {
    "pending": "chờ xác nhận",
    "confirmed": "đã xác nhận",
    "shipped": "đang giao",
    "delivered": "đã giao",
    "cancelled": "đã hủy",
    "returned": "đã trả hàng",
}
FALLBACK_ANSWER = (
    "I could not find enough information in the ShopX policies. "
    "Would you like to contact a support agent?"
)


def _ascii_text(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
        if not unicodedata.combining(char)
    )


def _localized(text: str, vietnamese: str, english: str) -> str:
    plain = _ascii_text(text)
    is_vietnamese = plain != text.lower() or bool(
        re.search(r"\b(?:xin chao|don hang|giup toi|cho hoi|bao lau)\b", plain)
    )
    return vietnamese if is_vietnamese else english


def _fallback(text: str) -> str:
    return _localized(
        text,
        "Mình chưa tìm thấy đủ thông tin trong tài liệu ShopX. Bạn có muốn gặp nhân viên hỗ trợ?",
        FALLBACK_ANSWER,
    )


def _unavailable(text: str) -> str:
    return _localized(
        text,
        "Hiện mình chưa xử lý được yêu cầu. Bạn vui lòng thử lại sau.",
        "I couldn't process the request right now. Please try again later.",
    )


class AgentOrchestrator:
    def __init__(
        self,
        llm: LLMClient,
        retriever: Retriever,
        tools: ToolRegistry,
        sessions: SessionStore,
        system_prompt: str,
        params: dict[str, Any],
        prompt_version: str = "v2",
        *,
        model: str | None = None,
    ) -> None:
        self.llm = llm
        self.retriever = retriever
        self.tools = tools
        self.sessions = sessions
        self.system_prompt = system_prompt
        self.params = params
        self.prompt_version = prompt_version
        self.model = model

    def handle(self, request: ChatRequest) -> ChatResponse:
        trace = TurnTrace(request.session_id, self.prompt_version, model=self.model)
        text = request.message
        response = ChatResponse(
            session_id=request.session_id, answer=_fallback(text), trace_id=trace.trace_id
        )
        try:
            with trace.step("guardrail_in"):
                verdict = check_input(text)
            if not verdict.allowed:
                response.handoff = verdict.suggest_handoff
            elif ORDER_ID.search(text) or ORDER_REQUEST.search(_ascii_text(text)):
                response.answer, response.actions = self._order(text, trace)
            else:
                response.answer, response.citations = self._policy(text, trace)
        except LLMError:
            response.answer = _unavailable(text)
        finally:
            trace.emit()
        self.sessions.append(
            request.session_id,
            Message("user", EMAIL.sub("[email]", text)),
            Message("assistant", response.answer),
        )
        return response

    def _complete(
        self,
        text: str,
        trace: TurnTrace,
        sources: dict[str, RetrievedChunk],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        context = json.dumps(
            [
                {"source": source, "doc_id": chunk.doc_id, "text": chunk.text}
                for source, chunk in sources.items()
            ],
            ensure_ascii=False,
        )
        prompt = self.system_prompt.replace("{context}", context)
        if "{context}" not in self.system_prompt:
            prompt += "\nPolicy chunks (JSON data):\n" + context
        llm = self.params.get("llm", {})
        with trace.step("llm"):
            result = self.llm.complete(
                [Message("system", prompt), Message("user", text)],
                tools,
                temperature=llm.get("temperature", 0.0),
                max_tokens=llm.get("max_output_tokens", 512),
            )
        trace.add_usage(
            result.usage.prompt_tokens,
            result.usage.completion_tokens,
            llm.get("price_per_million_input_tokens"),
            llm.get("price_per_million_output_tokens"),
            available=result.usage.available,
        )
        return result

    def _policy(self, text: str, trace: TurnTrace) -> tuple[str, list[Citation]]:
        retrieval = self.params.get("retrieval", {})
        with trace.step("retrieve"):
            candidates = self.retriever.search(text, retrieval.get("top_k", 4))
            sources = {
                f"S{index}": chunk
                for index, chunk in enumerate(candidates, 1)
                if chunk.score >= retrieval.get("min_score", 0.3) and chunk.text.strip()
            }
        trace.retrieved_doc_ids = list(dict.fromkeys(chunk.doc_id for chunk in candidates))
        trace.retrieved_chunk_ids = [
            chunk.chunk_id for chunk in candidates if chunk.chunk_id is not None
        ]
        if not sources:
            return _fallback(text), []

        result = self._complete(text, trace, sources)
        with trace.step("grounding"):
            try:
                reply = PolicyReply.model_validate_json(result.content)
            except ValidationError:
                return _fallback(text), []
            answer = reply.answer.strip()
            if (
                result.tool_calls
                or not answer
                or not reply.evidence
                or ORDER_ID.search(answer)
                or EMAIL.search(answer)
            ):
                return _fallback(text), []

            citations = []
            seen = set()
            for evidence in reply.evidence:
                chunk = sources.get(evidence.source)
                quote = evidence.quote.strip()
                if chunk is None or not quote or quote not in chunk.text:
                    return _fallback(text), []
                key = (chunk.doc_id, quote)
                if key not in seen:
                    citations.append(
                        Citation(doc_id=chunk.doc_id, snippet=quote, score=chunk.score)
                    )
                    seen.add(key)
        return answer, citations

    def _order(self, text: str, trace: TurnTrace) -> tuple[str, list[AgentAction]]:
        ids = {match.upper() for match in ORDER_ID.findall(text)}
        emails = set(EMAIL.findall(text))
        if len(ids) != 1 or len(emails) != 1:
            return self._request_order_details(text), []
        try:
            requested = GetOrderStatusArgs(order_id=ids.pop(), email=emails.pop())
        except ValidationError:
            return self._request_order_details(text), []

        tool_budget = self.params.get("agent", {}).get("max_tool_steps", 5)
        schemas = [
            schema for schema in self.tools.schemas() if schema["function"]["name"] == ORDER_TOOL
        ]
        if tool_budget < 1 or not schemas:
            return _unavailable(text), []

        result = self._complete(text, trace, {}, schemas)
        if len(result.tool_calls) != 1 or result.tool_calls[0].name != ORDER_TOOL:
            return _unavailable(text), []
        try:
            proposed = GetOrderStatusArgs.model_validate(result.tool_calls[0].arguments)
        except ValidationError:
            return self._request_order_details(text), []
        if proposed != requested:
            return self._request_order_details(text), []

        return self._lookup(text, requested, trace)

    def _lookup(
        self, text: str, requested: GetOrderStatusArgs, trace: TurnTrace
    ) -> tuple[str, list[AgentAction]]:
        trace.tools_called.append(ORDER_TOOL)
        outcome = "unavailable"
        answer = _unavailable(text)
        with trace.step("order_tool"):
            try:
                data = self.tools.call(ORDER_TOOL, requested.model_dump())
                if isinstance(data, dict) and data.get("error") == "not_found":
                    outcome = "not_found"
                else:
                    order = VerifiedOrder.model_validate(data)
                    if order.order_id == requested.order_id:
                        outcome = "verified"
                        answer = self._describe_order(text, order)
            except httpx.HTTPStatusError as error:
                if error.response.status_code in {403, 404}:
                    outcome = "not_found"
            except (httpx.RequestError, ToolError, RuntimeError, ValidationError):
                pass

        if outcome == "not_found":
            answer = _localized(
                text,
                "Mình chưa tìm thấy đơn khớp với mã đơn và email. Bạn kiểm tra lại cả hai nhé.",
                "I couldn't find an order matching that order ID and email. Please check both.",
            )
        trace.tool_results.append(outcome)
        verified = outcome == "verified"
        return answer, [
            AgentAction(
                tool=ORDER_TOOL,
                arguments={"order_id": requested.order_id} if verified else {},
                ok=verified,
                summary=outcome,
            )
        ]

    @staticmethod
    def _request_order_details(text: str) -> str:
        return _localized(
            text,
            "Bạn cho mình mã đơn và email đã dùng khi đặt hàng để xác minh nhé.",
            "Please provide the order ID and the email used for the order so I can verify it.",
        )

    @staticmethod
    def _describe_order(text: str, order: VerifiedOrder) -> str:
        answer = _localized(
            text,
            f"Đơn {order.order_id} hiện {VIETNAMESE_STATUS[order.status]}.",
            f"Order {order.order_id} is {order.status}.",
        )
        if order.estimated_delivery:
            delivery = order.estimated_delivery.isoformat()
            answer += _localized(
                text, f" Ngày giao dự kiến: {delivery}.", f" Estimated delivery: {delivery}."
            )
        if order.carrier:
            answer += _localized(
                text, f" Đơn vị vận chuyển: {order.carrier}.", f" Carrier: {order.carrier}."
            )
        return answer
