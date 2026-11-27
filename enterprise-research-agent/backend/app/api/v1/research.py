"""Research jobs (FR-03, FR-04, FR-08, FR-10)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import PageParams, get_current_user_id, not_implemented, page_params
from app.api.errors import error_responses
from app.schemas.common import Page
from app.schemas.research import ResearchAccepted, ResearchCreate, ResearchOut

router = APIRouter(prefix="/research", tags=["research"], responses=error_responses(401, 422))


@router.post(
    "",
    response_model=ResearchAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(404),
)
def create_research(
    body: ResearchCreate, user_id: uuid.UUID = Depends(get_current_user_id)
) -> ResearchAccepted:
    """TODO(FR-03): check collection ownership, insert ResearchJob, enqueue run_research(job_id)."""
    raise not_implemented("FR-03")


@router.get("/{job_id}", response_model=ResearchOut, responses=error_responses(404))
def get_research(
    job_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)
) -> ResearchOut:
    """TODO(FR-04): status + completed steps; the UI polls this (or use SSE)."""
    raise not_implemented("FR-04")


@router.get("", response_model=Page[ResearchOut])
def list_research(
    q: str | None = Query(default=None, description="Search in questions (FR-08)"),
    page: PageParams = Depends(page_params),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Page[ResearchOut]:
    raise not_implemented("FR-08")


@router.post(
    "/{job_id}/cancel",
    response_model=ResearchOut,
    responses=error_responses(404, 409, messages={409: "Job has already finished"}),
)
def cancel_research(
    job_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)
) -> ResearchOut:
    raise not_implemented("FR-10")


@router.post(
    "/{job_id}/retry",
    response_model=ResearchAccepted,
    status_code=202,
    responses=error_responses(404, 409, messages={409: "Only failed jobs can be retried"}),
)
def retry_research(
    job_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)
) -> ResearchAccepted:
    raise not_implemented("FR-10")
