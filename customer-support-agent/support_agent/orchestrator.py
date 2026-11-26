"""Ground ShopX policy answers in retrieved text."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from support_agent.guardrails import check_input
from support_agent.llm.base import LLMClient, LLMError, LLMResponse, Message
from support_agent.memory import SessionStore
from support_agent.retrieval.retriever import RetrievedChunk, Retriever
from support_agent.schemas import ChatRequest, ChatResponse, Citation
from support_agent.tools.registry import ToolRegistry
from support_agent.tracing import TurnTrace

ORDER_ID = re.compile(r"\bSX-[0-9]{6}\b", re.IGNORECASE)
EMAIL = re.compile(r"\b[\w.!#$%&'*+/=?^_~-]+@[\w-]+(?:\.[\w-]+)+\b")


class PolicyEvidence(BaseModel):
    source: str
    quote: str = Field(min_length=1)


class PolicyReply(BaseModel):
    answer: str
    evidence: list[PolicyEvidence]


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
