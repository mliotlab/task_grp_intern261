from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789")


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)
