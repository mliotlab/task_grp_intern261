from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.document import Document
    from app.models.research import ResearchJob


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # Stored lowercase (api/v1/auth.py), so the unique index also blocks "A@x.com" vs "a@x.com".
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # bcrypt hash, never the plain password (NFR-05). See core/security.py.
    password_hash: Mapped[str] = mapped_column(String(128))

    # Deleting a user deletes everything they own. The database does it (ON DELETE CASCADE);
    # passive_deletes stops the ORM from loading the children first.
    collections: Mapped[list[Collection]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    research_jobs: Mapped[list[ResearchJob]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
