"""Document upload and status (FR-02)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import get_current_user_id, not_implemented
from app.schemas.document import ChunkOut, DocumentOut

router = APIRouter(tags=["documents"])


@router.post(
    "/collections/{collection_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_document(
    collection_id: uuid.UUID,
    file: UploadFile = File(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> DocumentOut:
    """TODO(FR-02, NFR-04, NFR-05):
    1. validate extension + content type and size ≤ MAX_UPLOAD_MB (413 / 415 otherwise);
    2. compute sha256 – if the same file already exists in the collection, return it (idempotent);
    3. save to storage, insert Document(status=queued),
       enqueue `workers.ingestion.tasks.process_document`.
    """
    raise not_implemented("FR-02")


@router.get("/collections/{collection_id}/documents", response_model=list[DocumentOut])
def list_documents(
    collection_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)
) -> list[DocumentOut]:
    raise not_implemented("FR-02")


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)
) -> DocumentOut:
    raise not_implemented("FR-02")


@router.get("/chunks/{chunk_id}", response_model=ChunkOut)
def get_chunk(chunk_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)) -> ChunkOut:
    """Source passage behind a citation – the UI opens this when a citation is clicked (FR-06)."""
    raise not_implemented("FR-06")
