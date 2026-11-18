from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Collection(IdMixin, TimestampMixin, Base):
    __tablename__ = "collections"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000))
