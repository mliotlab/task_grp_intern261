"""Password hashing (bcrypt) and JWT access tokens (FR-01, NFR-05)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes),
    }
    return jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> str:
    """Return the subject (user id) or raise InvalidTokenError (bad signature, expired, ...)."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret.get_secret_value(), algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    return str(payload["sub"])
