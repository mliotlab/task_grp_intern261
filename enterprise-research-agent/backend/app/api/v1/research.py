"""Research jobs (FR-03, FR-04, FR-08, FR-10)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user_id, not_implemented
from app.schemas.research import ResearchAccepted, ResearchCreate, ResearchOut

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_research(
    body: ResearchCreate, user_id: uuid.UUID = Depends(get_current_user_id)
) -> ResearchAccepted:
    """TODO(FR-03): check collection ownership, insert ResearchJob, enqueue run_research(job_id)."""
    raise not_implemented("FR-03")


@router.get("/{job_id}", response_model=ResearchOut)
def get_research(
    job_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)
) -> ResearchOut:
    """TODO(FR-04): status + completed steps; the UI polls this (or use SSE)."""
    raise not_implemented("FR-04")


@router.get("", response_model=list[ResearchOut])
def list_research(
    q: str | None = Query(default=None, description="Search in questions (FR-08)"),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[ResearchOut]:
    raise not_implemented("FR-08")


@router.post("/{job_id}/cancel", response_model=ResearchOut)
def cancel_research(
    job_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)
) -> ResearchOut:
    raise not_implemented("FR-10")


@router.post("/{job_id}/retry", response_model=ResearchAccepted, status_code=202)
def retry_research(
    job_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)
) -> ResearchAccepted:
    raise not_implemented("FR-10")
