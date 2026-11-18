"""Collections of documents (FR-02, FR-06, FR-07)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user_id, not_implemented
from app.schemas.document import CollectionCreate, CollectionOut

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("", response_model=list[CollectionOut])
def list_collections(user_id: uuid.UUID = Depends(get_current_user_id)) -> list[CollectionOut]:
    """TODO(FR-07): only the caller's collections."""
    raise not_implemented("FR-06")


@router.post("", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def create_collection(
    body: CollectionCreate, user_id: uuid.UUID = Depends(get_current_user_id)
) -> CollectionOut:
    raise not_implemented("FR-06")


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: uuid.UUID, user_id: uuid.UUID = Depends(get_current_user_id)
) -> None:
    """TODO(FR-07): return 404 (not 403) for collections owned by someone else."""
    raise not_implemented("FR-06")
