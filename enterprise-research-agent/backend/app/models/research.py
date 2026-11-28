from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.user import User


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchJob(IdMixin, TimestampMixin, Base):
    """A research request and its result. State is persisted so a worker restart loses nothing."""

    __tablename__ = "research_jobs"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), index=True
    )
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[JobStatus] = mapped_column(
        enum_column(JobStatus, "job_status"), default=JobStatus.QUEUED, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    # [{"name": "plan", "status": "done", "duration_ms": 1234}, ...]  (FR-04, NFR-06)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    report_markdown: Mapped[str | None] = mapped_column(Text)
    # [{"marker": "[1]", "document_id": "...", "chunk_id": "...", "page": 3}, ...]
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text)

    owner: Mapped[User] = relationship(back_populates="research_jobs")
    collection: Mapped[Collection] = relationship(back_populates="research_jobs")
