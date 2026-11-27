"""Authentication endpoints (FR-01)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.errors import error_responses
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    dummy_password_hash,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_TAKEN = "Email already registered"
INVALID_CREDENTIALS = "Invalid email or password"


def _normalize(email: str) -> str:
    # "An@Example.com" and "an@example.com" are the same account.
    return email.strip().lower()


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422, messages={409: EMAIL_TAKEN}),
)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    """Create an account. The password is stored only as a bcrypt hash (NFR-05)."""
    email = _normalize(body.email)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)

    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:  # two requests registered the same email at once
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN) from exc
    return UserOut(id=user.id, email=user.email)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses=error_responses(401, 422, messages={401: INVALID_CREDENTIALS}),
)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Return a JWT that expires after `JWT_EXPIRE_MINUTES`.

    Unknown email and wrong password give the same 401 (registered emails are not revealed).
    """
    user = db.scalar(select(User).where(User.email == _normalize(body.email)))
    password_hash = user.password_hash if user else dummy_password_hash()
    if not verify_password(body.password, password_hash) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)

    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserOut, responses=error_responses(401))
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email)
