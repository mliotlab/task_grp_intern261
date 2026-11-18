from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.research import JobStatus


class ResearchCreate(BaseModel):
    question: str = Field(min_length=10, max_length=2000)
    collection_id: uuid.UUID
    web_search: bool = Field(default=False, description="FR-11 (Could)")


class ResearchAccepted(BaseModel):
    job_id: uuid.UUID
    status: JobStatus = JobStatus.QUEUED


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
