"""S2-01 / FR-01 / NFR-05: register, login, JWT and protected endpoints on real PostgreSQL."""

# ruff: noqa: S105, S106 - fake credentials in tests

from __future__ import annotations

import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import User

pytestmark = pytest.mark.integration

EMAIL = "an.nguyen@example.com"
PASSWORD = "S3cure-pass"


def _register(client: TestClient, email: str = EMAIL, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return client.post("/v1/auth/register", json={"email": email, "password": password})


def _login(client: TestClient, email: str = EMAIL, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return client.post("/v1/auth/login", json={"email": email, "password": password})


def test_register_stores_only_a_bcrypt_hash(db_client: TestClient, migrated_engine) -> None:  # type: ignore[no-untyped-def]
    resp = _register(db_client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == EMAIL
    uuid.UUID(body["id"])
    assert "password" not in resp.text

    with Session(migrated_engine) as db:
        stored = db.scalars(select(User)).one().password_hash
    assert stored != PASSWORD
    assert PASSWORD not in stored
    assert stored.startswith("$2b$")


def test_duplicate_email_is_409_even_with_other_case(db_client: TestClient) -> None:
    assert _register(db_client).status_code == 201
    resp = _register(db_client, email=EMAIL.upper())
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


def test_login_returns_jwt_with_expiry(db_client: TestClient) -> None:
    user_id = _register(db_client).json()["id"]
    resp = _login(db_client, email=EMAIL.upper())
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 60 * 60

    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["sub"] == user_id
    assert claims["exp"] - claims["iat"] == body["expires_in"]


def test_wrong_password_and_unknown_email_get_the_same_401(db_client: TestClient) -> None:
    _register(db_client)
    wrong_password = _login(db_client, password="not-the-password")
    unknown_email = _login(db_client, email="nobody@example.com")
    for resp in (wrong_password, unknown_email):
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthorized"
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]


def test_long_unicode_password_works(db_client: TestClient) -> None:
    """128 Vietnamese characters is far more than bcrypt's 72-byte limit."""
    password = "mậtkhẩu" * 18 + "ẩẩ"
    assert len(password) == 128
    assert _register(db_client, password=password).status_code == 201
    assert _login(db_client, password=password).status_code == 200
    assert _login(db_client, password=password[:-1]).status_code == 401


def test_protected_endpoint_accepts_token_and_rejects_bad_ones(db_client: TestClient) -> None:
    _register(db_client)
    token = _login(db_client).json()["access_token"]

    ok = db_client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200
    assert ok.json()["email"] == EMAIL

    user_id = ok.json()["id"]
    bad_tokens = {
        "missing": None,
        "garbage": "not-a-jwt",
        "expired": create_access_token(user_id, expires_minutes=-1),
        "unknown user": create_access_token(str(uuid.uuid4())),
    }
    for case, bad in bad_tokens.items():
        headers = {"Authorization": f"Bearer {bad}"} if bad else {}
        resp = db_client.get("/v1/auth/me", headers=headers)
        assert resp.status_code == 401, case
        assert resp.json()["error"]["code"] == "unauthorized", case
