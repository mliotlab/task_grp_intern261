from __future__ import annotations

import json
import logging
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from services.order_api.main import RedactEmailFilter, app, load_orders
from support_agent.config import get_settings
from support_agent.tools.order_status import get_order_status


def _clear_caches() -> None:
    get_settings.cache_clear()
    load_orders.cache_clear()


@pytest.fixture()
def orders_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    data = [
        {
            "order_id": "SX-000001",
            "email": "customer001@example.com",
            "status": "confirmed",
            "items": ["USB-C Cable"],
            "total_vnd": 150000,
            "placed_on": "2026-11-28",
            "estimated_delivery": "2026-12-03",
            "carrier": "GHN",
        },
        {
            "order_id": "SX-000002",
            "email": "customer002@example.com",
            "status": "pending",
            "items": ["Mouse Pad"],
            "total_vnd": 90000,
            "placed_on": "2026-11-29",
            "estimated_delivery": None,
            "carrier": None,
        },
    ]
    path = tmp_path / "orders.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("ORDERS_FILE", str(path))
    _clear_caches()
    yield path
    _clear_caches()


def test_get_order_success_case_insensitive_email(orders_file: Path) -> None:
    client = TestClient(app)
    resp = client.get("/v1/orders/SX-000001", params={"email": "Customer001@Example.COM"})
    assert resp.status_code == 200
    assert resp.json() == {
        "order_id": "SX-000001",
        "status": "confirmed",
        "estimated_delivery": "2026-12-03",
        "carrier": "GHN",
    }


def test_get_order_nullable_fields(orders_file: Path) -> None:
    client = TestClient(app)
    resp = client.get("/v1/orders/SX-000002", params={"email": "customer002@example.com"})
    assert resp.status_code == 200
    assert resp.json()["estimated_delivery"] is None
    assert resp.json()["carrier"] is None


def test_uniform_404_wrong_email_vs_missing_order(orders_file: Path) -> None:
    client = TestClient(app)
    resp_wrong_email = client.get("/v1/orders/SX-000001", params={"email": "wrong@example.com"})
    resp_missing_order = client.get(
        "/v1/orders/SX-999999", params={"email": "customer001@example.com"}
    )

    assert resp_wrong_email.status_code == 404
    assert resp_missing_order.status_code == 404
    assert resp_wrong_email.json() == resp_missing_order.json()
    assert "customer001@example.com" not in resp_wrong_email.text
    assert "wrong@example.com" not in resp_wrong_email.text


def test_missing_or_invalid_email_returns_422(orders_file: Path) -> None:
    client = TestClient(app)
    assert client.get("/v1/orders/SX-000001").status_code == 422
    assert client.get("/v1/orders/SX-000001", params={"email": "not-an-email"}).status_code == 422


def test_missing_or_corrupt_fixture_returns_503(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = TestClient(app)

    monkeypatch.setenv("ORDERS_FILE", str(tmp_path / "does-not-exist.json"))
    _clear_caches()
    assert (
        client.get("/v1/orders/SX-000001", params={"email": "customer001@example.com"}).status_code
        == 503
    )

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{bad json", encoding="utf-8")
    monkeypatch.setenv("ORDERS_FILE", str(corrupt))
    _clear_caches()
    assert (
        client.get("/v1/orders/SX-000001", params={"email": "customer001@example.com"}).status_code
        == 503
    )
    _clear_caches()


def test_redact_email_filter_masks_access_log() -> None:
    log_filter = RedactEmailFilter()
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=(
            "127.0.0.1",
            "GET",
            "/v1/orders/SX-000001?email=secret@example.com",
            "1.1",
            200,
        ),
        exc_info=None,
    )
    assert log_filter.filter(record) is True
    formatted = record.getMessage()
    assert "secret@example.com" not in formatted
    assert "email=[REDACTED]" in formatted


def test_order_status_client_success_not_found_and_timeout_no_email_leak(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    secret_email = "private.user@example.com"

    def fake_200(*args, **kwargs) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "order_id": "SX-000001",
                "status": "confirmed",
                "estimated_delivery": "2026-12-03",
                "carrier": "GHN",
            },
        )

    monkeypatch.setattr(httpx, "get", fake_200)
    ok_result = get_order_status("SX-000001", f"  {secret_email.upper()}  ")
    assert ok_result == {
        "order_id": "SX-000001",
        "status": "confirmed",
        "estimated_delivery": "2026-12-03",
        "carrier": "GHN",
    }

    def fake_404(*args, **kwargs) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Order not found"})

    monkeypatch.setattr(httpx, "get", fake_404)
    with caplog.at_level(logging.INFO):
        result = get_order_status("SX-000001", secret_email)
    assert result == {"error": "not_found"}
    assert secret_email not in str(result)
    assert secret_email not in caplog.text

    def fake_timeout(*args, **kwargs):
        raise httpx.TimeoutException(f"timed out calling ?email={secret_email}")

    monkeypatch.setattr(httpx, "get", fake_timeout)
    caplog.clear()
    with caplog.at_level(logging.INFO):
        timeout_result = get_order_status("SX-000001", secret_email)
    assert timeout_result == {"error": "upstream_timeout"}
    assert secret_email not in str(timeout_result)
    assert secret_email not in caplog.text
