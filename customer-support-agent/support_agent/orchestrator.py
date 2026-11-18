"""Agent Orchestrator: prompt assembly, guardrails, tool-calling loop, handoff decision.

The orchestrator decides *what* to call; business data lives behind the Order API and Ticket
Service. It depends only on interfaces (LLMClient, Retriever, ToolRegistry, SessionStore), so every
part can be replaced by a fake in tests.
"""

from __future__ import annotations

import logging
from typing import Any

from support_agent.guardrails import check_input
from support_agent.llm.base import LLMClient, Message
from support_agent.memory import SessionStore
from support_agent.retrieval.retriever import Retriever
from support_agent.schemas import ChatRequest, ChatResponse
from support_agent.tools.registry import ToolRegistry
from support_agent.tracing import TurnTrace

logger = logging.getLogger(__name__)

FALLBACK_ANSWER = (
    "Sorry, I can't help with that request yet. Would you like me to connect you with a "
    "support agent?"
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
        prompt_version: str = "v1",
    ) -> None:
        self.llm = llm
        self.retriever = retriever
        self.tools = tools
        self.sessions = sessions
        self.system_prompt = system_prompt
        self.params = params
        self.prompt_version = prompt_version

    def handle(self, request: ChatRequest) -> ChatResponse:
        trace = TurnTrace(session_id=request.session_id, prompt_version=self.prompt_version)

        with trace.step("guardrail_in"):
            verdict = check_input(request.message)
        if not verdict.allowed:
            trace.emit()
            return ChatResponse(
                session_id=request.session_id,
                answer=FALLBACK_ANSWER,
                handoff=verdict.suggest_handoff,
                trace_id=trace.trace_id,
            )

        # TODO(FR-01, FR-03, FR-04..06): implement the tool-calling loop. Suggested shape:
        #
        #   agent    = self.params["agent"]
        #   history  = self.sessions.history(session_id, max_turns=agent["max_history_turns"])
        #   chunks   = self.retriever.search(message, top_k=params["retrieval"]["top_k"])
        #   messages = [system(self.system_prompt + context(chunks)), *history, user(message)]
        #   for _ in range(params["agent"]["max_tool_steps"]):
        #       resp = self.llm.complete(messages, tools=self.tools.schemas(), ...)
        #       trace.add_usage(...)
        #       if not resp.tool_calls: break
        #       for call in resp.tool_calls:
        #           result = self.tools.call(call.name, call.arguments)   # validated arguments
        #           messages.append(Message("tool", json.dumps(result), tool_call_id=call.id))
        #   apply check_output(...), build citations + actions, save history, trace.emit()
        with trace.step("llm"):
            response = self.llm.complete(
                [Message("system", self.system_prompt), Message("user", request.message)]
            )
        trace.add_usage(response.usage.prompt_tokens, response.usage.completion_tokens, 0.0, 0.0)
        self.sessions.append(
            request.session_id,
            Message("user", request.message),
            Message("assistant", response.content),
        )
        trace.emit()
        return ChatResponse(
            session_id=request.session_id, answer=response.content, trace_id=trace.trace_id
        )
