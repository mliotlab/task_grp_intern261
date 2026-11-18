"""Shared FastAPI dependencies: authentication and ownership checks (FR-01, FR-07, NFR-05)."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> uuid.UUID:
    """Validate the bearer token and return the user id. No DB access."""
    if credentials is None:
        raise UNAUTHORIZED
    try:
        return uuid.UUID(decode_access_token(credentials.credentials))
    except (InvalidTokenError, ValueError) as exc:
        raise UNAUTHORIZED from exc


def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id), db: Session = Depends(get_db)
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise UNAUTHORIZED
    return user


def not_implemented(requirement: str) -> HTTPException:
    return HTTPException(status_code=501, detail=f"Not implemented yet ({requirement})")
