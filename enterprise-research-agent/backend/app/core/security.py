"""Password hashing (bcrypt) and JWT access tokens (FR-01, NFR-05)."""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import bcrypt
import jwt

from app.core.config import get_settings


class InvalidTokenError(Exception):
    pass


def _prehash(password: str) -> bytes:
    """SHA-256 then base64 (44 bytes) before bcrypt.

    bcrypt only reads the first 72 bytes and bcrypt>=5 raises on longer input. Passwords may be
    up to 128 characters, and Vietnamese characters take 2-3 bytes each in UTF-8, so without this
    step long passwords would crash (500) or be silently truncated.
    """
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """False for a wrong password or a malformed stored hash (never raises)."""
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


@lru_cache
def dummy_password_hash() -> str:
    """A valid hash to check against when the email is unknown.

    Login then costs one bcrypt check whether or not the account exists, so response time does
    not reveal which emails are registered.
    """
    return hash_password("dummy-password-for-timing")


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    if expires_minutes is None:
        expires_minutes = settings.jwt_expire_minutes
    now = datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    return jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> str:
    """Return the subject (user id) or raise InvalidTokenError (bad signature, expired, ...)."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            # A token without an expiry would be valid forever: reject it.
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    return str(payload["sub"])
