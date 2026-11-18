from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(chat_client: TestClient) -> None:
    resp = chat_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert "X-Request-ID" in resp.headers


def test_chat_returns_contract(chat_client: TestClient) -> None:
    resp = chat_client.post("/v1/chat", json={"session_id": "s1", "message": "Hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"session_id", "answer", "citations", "actions", "handoff", "trace_id"}
    assert body["session_id"] == "s1"


def test_chat_rejects_empty_message(chat_client: TestClient) -> None:
    resp = chat_client.post("/v1/chat", json={"session_id": "s1", "message": ""})
    assert resp.status_code == 422
