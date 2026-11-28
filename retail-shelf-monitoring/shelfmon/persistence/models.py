"""Database models for analysis history and alert lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=True)

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    pass


JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class AnalysisRecord(Base):
    __tablename__ = "analyses"
    __table_args__ = (Index("ix_analyses_store_created", "store_id", "created_at"),)

    analysis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    store_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    product_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fill_rate: Mapped[float] = mapped_column(Float, nullable=False)
    alert: Mapped[bool] = mapped_column(nullable=False)
    result_json: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    config_snapshot: Mapped[dict[str, object]] = mapped_column(JSON_DOCUMENT, nullable=False)
    original_image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    annotated_image_path: Mapped[str] = mapped_column(String(512), nullable=False)


class AlertRecord(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("analysis_id", name="uq_alerts_analysis_id"),
        CheckConstraint("reason IN ('low_fill', 'no_detection')", name="ck_alerts_reason"),
        CheckConstraint("status IN ('unresolved', 'resolved')", name="ck_alerts_status"),
        Index("ix_alerts_status_created", "status", "created_at"),
    )

    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.analysis_id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unresolved")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
