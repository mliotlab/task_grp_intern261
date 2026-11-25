"""Create the configured LLM client."""

from __future__ import annotations

from support_agent.config import Settings
from support_agent.llm.base import LLMClient
from support_agent.llm.compatible import CompatibleLLM
from support_agent.llm.mock import MockLLM


def create_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "mock":
        return MockLLM()

    api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    if settings.llm_provider == "openai" and not api_key:
        raise ValueError("LLM_API_KEY is required for the configured API provider.")
    default_url = (
        "http://localhost:11434/v1"
        if settings.llm_provider == "ollama"
        else "https://api.openai.com/v1"
    )
    return CompatibleLLM(
        settings.llm_model,
        settings.llm_base_url or default_url,
        api_key,
        settings.llm_timeout_seconds,
    )
