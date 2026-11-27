"""Settings loaded from environment variables (12-factor). Secrets are never hard-coded."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    database_url: str = "postgresql+psycopg://era:era@localhost:5432/era"
    redis_url: str = "redis://localhost:6379/0"

    # Auth (FR-01, NFR-05)
    jwt_secret: SecretStr = SecretStr("change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Uploads (FR-02)
    upload_dir: Path = Path("var/uploads")
    max_upload_mb: int = 20
    allowed_extensions: tuple[str, ...] = (".pdf", ".docx", ".md")

    # AI (FR-05)
    llm_provider: Literal["mock", "openai", "ollama", "gemini"] = "mock"
    llm_model: str = "gemini-3.5-flash-lite"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None

    gemini_api_key: SecretStr | None = None

    # Embedding (ERA-11)
    embedding_provider: Literal["gemini", "local"] = "gemini"
    embedding_model: str = "gemini-embedding-2"  # gemini only
    local_embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384  # must match Vector(384)
    embedding_max_texts_per_minute: int = 80  # gemini only

    # Jobs (NFR-04)
    job_max_retries: int = 2

    # Jobs (NFR-04)
    job_max_retries: int = 2

    chunk_strategy: Literal["baseline", "advanced"] = "advanced"
    chunk_size: int = 1000
    chunk_overlap: int = 150

    @model_validator(mode="after")
    def _check_chunk_params(self) -> Settings:
        if self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE must be > 0")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be >= 0 and < CHUNK_SIZE")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
