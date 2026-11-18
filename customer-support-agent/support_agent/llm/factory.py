"""Create the configured LLM client."""

from __future__ import annotations

from support_agent.config import Settings
from support_agent.llm.base import LLMClient
from support_agent.llm.mock import MockLLM


def create_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "mock":
        return MockLLM()

    # TODO(Sprint 1, ADR-0002): implement an OpenAI-compatible client (`pip install -e ".[llm]"`).
    #   - The same client works for the mentor API and for Ollama (base_url=http://<host>:11434/v1).
    #   - Map `Message` / tool schemas to the provider format and back to `LLMResponse`.
    #   - Return token usage so `TurnTrace.add_usage` can estimate cost (NFR-07).
    raise NotImplementedError(f"LLM provider '{settings.llm_provider}' is not implemented yet")
