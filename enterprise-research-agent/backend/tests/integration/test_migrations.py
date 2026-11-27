"""S2-01: the Alembic migration builds the schema of Design Doc Section 6 on a new PostgreSQL."""

from __future__ import annotations

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text

from app.models import Base

pytestmark = pytest.mark.integration

TABLES = {"users", "collections", "documents", "chunks", "research_jobs"}


def test_upgrade_creates_schema(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    insp = inspect(migrated_engine)
    assert set(insp.get_table_names()) >= TABLES
    with migrated_engine.connect() as conn:
        assert conn.scalar(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")) == 1
        dim = conn.scalar(
            text(
                "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"
            )
        )
    assert dim == "vector(384)"


def test_models_and_migration_are_in_sync(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    """Same check as `alembic check`: a model change without a migration fails here."""
    with migrated_engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_downgrade_removes_everything_and_upgrade_again(make_database, run_alembic) -> None:  # type: ignore[no-untyped-def]
    engine = make_database()
    run_alembic(engine, "upgrade", "head")
    run_alembic(engine, "downgrade", "base")

    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    with engine.connect() as conn:
        enums = conn.scalars(
            text("SELECT typname FROM pg_type WHERE typname IN ('document_status', 'job_status')")
        ).all()
    assert enums == []

    run_alembic(engine, "upgrade", "head")
    assert set(inspect(engine).get_table_names()) >= TABLES
    engine.dispose()
