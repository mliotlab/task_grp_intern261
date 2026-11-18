"""Application settings.

Secrets and environment-specific values come from environment variables / `.env`.
Versioned behaviour (temperatures, top-k, limits) comes from `configs/agent.yaml`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# All relative paths resolve against APP_ROOT (defaults to the current working directory:
# the project folder locally, /app in Docker).
PROJECT_ROOT = Path(os.environ.get("APP_ROOT", ".")).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    llm_provider: Literal["mock", "openai", "ollama"] = "mock"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None

    prompt_version: str = "v1"
    agent_config: Path = PROJECT_ROOT / "configs" / "agent.yaml"

    kb_dir: Path = PROJECT_ROOT / "kb"
    vector_store_dir: Path = PROJECT_ROOT / "var" / "vector_store"
    embedding_model: str = "intfloat/multilingual-e5-small"

    order_api_url: str = "http://localhost:8001"
    orders_file: Path = PROJECT_ROOT / "var" / "orders.json"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'var' / 'support.db'}"

    def agent_params(self) -> dict[str, Any]:
        """Load the versioned agent configuration file."""
        with self.agent_config.open(encoding="utf-8") as f:
            return yaml.safe_load(f)


@lru_cache
def get_settings() -> Settings:
    return Settings()
