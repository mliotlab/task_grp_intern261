"""Requirement 9.5: unified error format and pagination for every list endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

LIST_PATHS = ("/v1/collections", "/v1/collections/{collection_id}/documents", "/v1/research")


def _assert_error(resp, status: int, code: str) -> dict:  # type: ignore[no-untyped-def]
    assert resp.status_code == status
    error = resp.json()["error"]
    assert error["code"] == code
    assert error["message"]
    assert error["request_id"] == resp.headers["X-Request-ID"]
    return error


def test_unauthorized_uses_error_format(client: TestClient) -> None:
    resp = client.get("/v1/collections", headers={"X-Request-ID": "req-401"})
    error = _assert_error(resp, 401, "unauthorized")
    assert error["request_id"] == "req-401"
    assert resp.headers["WWW-Authenticate"] == "Bearer"


def test_validation_error_lists_fields_without_echoing_input(client: TestClient) -> None:
    resp = client.post(
        "/v1/auth/register", json={"email": "not-an-email", "password": "secret-value-123"}
    )
    error = _assert_error(resp, 422, "validation_error")
    assert error["details"][0]["loc"] == ["body", "email"]
    assert "secret-value-123" not in resp.text


def test_unknown_route_uses_error_format(client: TestClient) -> None:
    _assert_error(client.get("/v1/does-not-exist"), 404, "not_found")


def test_not_implemented_uses_error_format(client: TestClient) -> None:
    resp = client.post(
        "/v1/auth/register", json={"email": "an@example.com", "password": "S3cure-pass"}
    )
    _assert_error(resp, 501, "not_implemented")


def test_contract_errors_and_pagination(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    for path, ops in spec["paths"].items():
        if not path.startswith("/v1"):
            continue
        for method, op in ops.items():
            for status, resp in op["responses"].items():
                if not status.startswith("2"):
                    ref = resp["content"]["application/json"]["schema"]["$ref"]
                    assert ref.endswith("/ErrorResponse"), (method, path, status)
            ok = op["responses"].get("200", {}).get("content", {}).get("application/json", {})
            assert ok.get("schema", {}).get("type") != "array", f"bare list: {path}"
    for path in LIST_PATHS:
        op = spec["paths"][path]["get"]
        params = {p["name"] for p in op["parameters"] if p["in"] == "query"}
        assert {"limit", "offset"} <= params, path
        ref = op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        assert "Page" in ref, path
