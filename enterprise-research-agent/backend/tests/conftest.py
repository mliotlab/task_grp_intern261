from __future__ import annotations

import importlib
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789")


@pytest.fixture(scope="session")
def retrieval_module():
    """Import the actual retrieval module under test."""
    module_path = os.getenv(
        "ERA_RETRIEVAL_MODULE",
        "workers.research.retrieve",
    )
    return importlib.import_module(module_path)


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)
