"""Runtime settings (environment variables / .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

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

    # Post-processing (FR-03, FR-04, ADR-0002, ADR-0003)
    conf_threshold: float = Field(0.25, ge=0, le=1)
    gap_width_multiplier: float = Field(
        1.5,
        gt=0,
        description=(
            "A gap is reported if wider than k × local median width of 4–5 neighboring products"
        ),
    )
    fill_rate_alert_threshold: float = Field(0.80, ge=0, le=1)
    row_clustering_method: Literal["center_y", "dbscan_1d"] = "center_y"
    row_y_tolerance_ratio: float = Field(0.45, gt=0)
    shelf_bound_mode: Literal["outer_products", "neighbor_median", "row_extent", "image_width"] = (
        "neighbor_median"
    )
    tilt_deadband_deg: float = Field(1.5, ge=0)
    empty_tier_kv: float = Field(1.2, gt=0)
    gap_neighbor_count: int = Field(5, ge=1)

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
