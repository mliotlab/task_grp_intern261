"""Integration tests run against real PostgreSQL + Redis (CI services / docker compose)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="TODO(FR-07, NFR-05): enable once auth + collections are implemented")
def test_user_cannot_read_another_users_collection() -> None:
    """Register A and B; A creates a collection; B gets 404 on GET/DELETE of it."""


@pytest.mark.skip(reason="TODO(NFR-04): enable once upload is implemented")
def test_uploading_same_file_twice_is_idempotent() -> None:
    """Upload the same PDF twice into one collection → same document id, one row."""
