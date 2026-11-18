"""Runtime settings (environment variables / .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    log_level: str = "INFO"

    # Model registry (NFR-06): models/<version>/weights.pt + MODEL_CARD.md + SHA256SUMS
    model_dir: Path = Path("models")
    model_version: str = "yolov8n-pretrained"
    device: str = "cpu"
    imgsz: int = 1024

    # Post-processing (FR-03, FR-04)
    conf_threshold: float = Field(0.25, ge=0, le=1)
    gap_width_multiplier: float = Field(
        1.5, gt=0, description="A gap is reported if wider than k × mean product width in the row"
    )
    fill_rate_alert_threshold: float = Field(0.80, ge=0, le=1)

    # Input validation (FR-01, FR-06)
    max_upload_mb: int = 10
    max_image_side: int = 1920

    # Storage (FR-05)
    database_url: str = "sqlite:///var/shelfmon.db"
    image_dir: Path = Path("var/images")

    # Alerts (FR-09)
    alert_webhook_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
