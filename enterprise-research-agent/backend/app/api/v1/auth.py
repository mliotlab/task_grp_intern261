"""Authentication endpoints (FR-01)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, not_implemented
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest) -> UserOut:
    """TODO(FR-01): reject duplicate emails (409), store `hash_password(body.password)`."""
    raise not_implemented("FR-01")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    """TODO(FR-01): verify_password → create_access_token(str(user.id)).

    Return the same 401 for "unknown email" and "wrong password".
    """
    raise not_implemented("FR-01")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email)
