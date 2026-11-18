from __future__ import annotations

import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin

EMBEDDING_DIM = 384  # must match settings.embedding_dim and the embedding model (ADR)


class DocumentStatus(enum.StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(IdMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    # NFR-04: uploading the same file twice into a collection must not create a duplicate.
    __table_args__ = (UniqueConstraint("collection_id", "sha256", name="uq_document_content"),)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.QUEUED
    )
    error: Mapped[str | None] = mapped_column(Text)


class Chunk(IdMixin, Base):
    __tablename__ = "chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)  # citation location (FR-05)
    section: Mapped[str | None] = mapped_column(String(500))
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
