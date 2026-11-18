"""Chat API (FR-01): receive a message, run the orchestrator, return answer + citations + actions.

Run locally:  uvicorn services.chat_api.main:app --reload --port 8000
OpenAPI docs: http://localhost:8000/docs
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from functools import lru_cache

from fastapi import Depends, FastAPI, Request, Response

from support_agent import __version__
from support_agent.config import get_settings
from support_agent.llm import create_llm
from support_agent.logging_config import configure_logging
from support_agent.memory import InMemorySessionStore
from support_agent.orchestrator import AgentOrchestrator
from support_agent.prompts import load_system_prompt
from support_agent.retrieval.retriever import NullRetriever
from support_agent.schemas import ChatRequest, ChatResponse
from support_agent.tools.defaults import default_registry


@lru_cache
def get_orchestrator() -> AgentOrchestrator:
    settings = get_settings()
    return AgentOrchestrator(
        llm=create_llm(settings),
        retriever=NullRetriever(),  # TODO(FR-03): replace with VectorRetriever
        tools=default_registry(),
        sessions=InMemorySessionStore(),
        system_prompt=load_system_prompt(settings.prompt_version),
        params=settings.agent_params(),
        prompt_version=settings.prompt_version,
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="ShopX Customer Support Agent – Chat API", version=__version__)

    @app.middleware("http")
    async def add_request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/v1/chat", response_model=ChatResponse, tags=["chat"])
    def chat(
        body: ChatRequest, orchestrator: AgentOrchestrator = Depends(get_orchestrator)
    ) -> ChatResponse:
        return orchestrator.handle(body)

    return app


app = create_app()
