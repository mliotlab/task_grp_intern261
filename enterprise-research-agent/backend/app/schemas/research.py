from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.research import JobStatus


class ResearchCreate(BaseModel):
    question: str = Field(min_length=10, max_length=2000)
    collection_id: uuid.UUID
    web_search: bool = Field(default=False, description="FR-11 (Could)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "NIST SP 800-53 yêu cầu gì về quản lý tài khoản người dùng?",
                    "collection_id": "5d1e7f20-3b4a-4c8d-8e9f-0a1b2c3d4e5f",
                    "web_search": False,
                }
            ]
        }
    )


class ResearchAccepted(BaseModel):
    job_id: uuid.UUID
    status: JobStatus = JobStatus.QUEUED

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"job_id": "a4b5c6d7-e8f9-4a0b-9c1d-2e3f4a5b6c7d", "status": "queued"}]
        }
    )


class StepOut(BaseModel):
    name: str
    status: str
    duration_ms: float | None = None


class CitationOut(BaseModel):
    marker: str = Field(examples=["[1]"])
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    filename: str
    page: int | None = None
    section: str | None = None


class ResearchOut(BaseModel):
    job_id: uuid.UUID
    question: str
    status: JobStatus
    steps: list[StepOut] = []
    report_markdown: str | None = None
    citations: list[CitationOut] = []
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "job_id": "a4b5c6d7-e8f9-4a0b-9c1d-2e3f4a5b6c7d",
                    "question": "NIST SP 800-53 yêu cầu gì về quản lý tài khoản người dùng?",
                    "status": "succeeded",
                    "steps": [
                        {"name": "plan", "status": "done", "duration_ms": 812.4},
                        {"name": "retrieve", "status": "done", "duration_ms": 95.1},
                    ],
                    "report_markdown": "Tổ chức phải xác định các loại tài khoản được phép [1]...",
                    "citations": [
                        {
                            "marker": "[1]",
                            "document_id": "77c1a9e4-2f6b-4d3c-9b8a-1e2f3a4b5c6d",
                            "chunk_id": "c9e0f1a2-b3c4-4d5e-8f6a-7b8c9d0e1f2a",
                            "filename": "NIST.SP.800-53r5.pdf",
                            "page": 18,
                            "section": "AC-2 Account Management",
                        }
                    ],
                    "error": None,
                    "created_at": "2026-11-20T09:15:00Z",
                    "updated_at": "2026-11-20T09:15:00Z",
                }
            ]
        }
    )
