from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong", hashed)


def test_token_roundtrip() -> None:
    uid = str(uuid.uuid4())
    assert decode_access_token(create_access_token(uid)) == uid


def test_expired_token_rejected() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token(create_access_token("u", expires_minutes=-1))


def test_tampered_token_rejected() -> None:
    token = create_access_token("u") + "x"
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/v1/collections"),
        ("post", "/v1/research"),
        ("get", f"/v1/research/{uuid.uuid4()}"),
        ("get", f"/v1/documents/{uuid.uuid4()}"),
    ],
)
def test_protected_endpoints_require_token(client: TestClient, method: str, path: str) -> None:
    """NFR-05: every endpoint except login/register/health requires a valid token."""
    resp = getattr(client, method)(path)
    assert resp.status_code == 401


def test_invalid_token_rejected(client: TestClient) -> None:
    resp = client.get("/v1/collections", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_long_password_beyond_bcrypt_72_bytes() -> None:
    """S2-01: up to 128 characters (multi-byte UTF-8) must hash and verify without error."""
    password = "mậtkhẩu" * 18 + "ẩẩ"
    assert len(password.encode("utf-8")) > 72
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password(password[:-1], hashed)


def test_verify_password_with_malformed_hash_is_false() -> None:
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_token_without_expiry_rejected() -> None:
    import jwt as pyjwt

    from app.core.config import get_settings

    settings = get_settings()
    token = pyjwt.encode(
        {"sub": "u"}, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
