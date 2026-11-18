from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class CollectionOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    document_count: int = 0
    created_at: datetime


class DocumentOut(BaseModel):
    id: uuid.UUID
    collection_id: uuid.UUID
    filename: str
    size_bytes: int
    status: DocumentStatus
    error: str | None = None
    created_at: datetime


class ChunkOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    section: str | None
    text: str
