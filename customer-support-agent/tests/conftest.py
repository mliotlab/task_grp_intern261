from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LLM_PROVIDER", "mock")


@pytest.fixture
def chat_client() -> TestClient:
    from services.chat_api.main import app

    return TestClient(app)
