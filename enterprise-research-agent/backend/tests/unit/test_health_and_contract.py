from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_is_public(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.headers["X-Request-ID"]


def test_request_id_is_propagated(client: TestClient) -> None:
    resp = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers["X-Request-ID"] == "abc123"


def test_openapi_exposes_required_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/v1/auth/register",
        "/v1/auth/login",
        "/v1/collections",
        "/v1/collections/{collection_id}/documents",
        "/v1/research",
        "/v1/research/{job_id}",
    ):
        assert path in paths, path
