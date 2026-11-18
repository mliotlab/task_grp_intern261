from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_health(api_client: TestClient) -> None:
    resp = api_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "model_version" in body


def test_analyze_requires_image_and_store_id(api_client: TestClient) -> None:
    assert api_client.post("/v1/analyze").status_code == 422


@pytest.mark.skip(reason="TODO(FR-06, NFR-04): enable when input validation is implemented")
@pytest.mark.parametrize(
    ("filename", "content", "content_type", "expected"),
    [
        ("a.gif", b"GIF89a", "image/gif", 415),
        ("a.jpg", b"not an image", "image/jpeg", 422),
        ("a.jpg", b"0" * (11 * 1024 * 1024), "image/jpeg", 413),
    ],
)
def test_bad_inputs_return_4xx(
    api_client: TestClient, filename: str, content: bytes, content_type: str, expected: int
) -> None:
    resp = api_client.post(
        "/v1/analyze",
        files={"image": (filename, content, content_type)},
        data={"store_id": "S001"},
    )
    assert resp.status_code == expected
    assert "detail" in resp.json()
