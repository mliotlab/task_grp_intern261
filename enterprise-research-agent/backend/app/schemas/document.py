from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"name": "NIST SP 800", "description": "Bộ tài liệu bảo mật NIST SP 800"}]
        }
    )


class CollectionOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    document_count: int = 0
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "5d1e7f20-3b4a-4c8d-8e9f-0a1b2c3d4e5f",
                    "name": "NIST SP 800",
                    "description": "Bộ tài liệu bảo mật NIST SP 800",
                    "document_count": 3,
                    "created_at": "2026-11-20T09:15:00Z",
                }
            ]
        }
    )


class DocumentOut(BaseModel):
    id: uuid.UUID
    collection_id: uuid.UUID
    filename: str
    size_bytes: int
    status: DocumentStatus
    error: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "77c1a9e4-2f6b-4d3c-9b8a-1e2f3a4b5c6d",
                    "collection_id": "5d1e7f20-3b4a-4c8d-8e9f-0a1b2c3d4e5f",
                    "filename": "NIST.SP.800-53r5.pdf",
                    "size_bytes": 482133,
                    "status": "queued",
                    "error": None,
                    "created_at": "2026-11-20T09:15:00Z",
                }
            ]
        }
    )


class ChunkOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    section: str | None
    text: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "c9e0f1a2-b3c4-4d5e-8f6a-7b8c9d0e1f2a",
                    "document_id": "77c1a9e4-2f6b-4d3c-9b8a-1e2f3a4b5c6d",
                    "filename": "NIST.SP.800-53r5.pdf",
                    "page": 18,
                    "section": "AC-2 Account Management",
                    "text": "Define and document the types of accounts allowed...",
                }
            ]
        }
    )
