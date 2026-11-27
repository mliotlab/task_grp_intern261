from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.research import ResearchJob
    from app.models.user import User


class Collection(IdMixin, TimestampMixin, Base):
    __tablename__ = "collections"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000))

    owner: Mapped[User] = relationship(back_populates="collections")
    documents: Mapped[list[Document]] = relationship(
        back_populates="collection", cascade="all, delete-orphan", passive_deletes=True
    )
    research_jobs: Mapped[list[ResearchJob]] = relationship(
        back_populates="collection", cascade="all, delete-orphan", passive_deletes=True
    )
