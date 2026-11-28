"""S2-01: model structure matches Design Doc Section 6 (no database needed)."""

from __future__ import annotations

from sqlalchemy.orm import configure_mappers

from app.core.config import get_settings
from app.models import Base, Chunk, Collection, Document, ResearchJob, User
from app.models.document import EMBEDDING_DIM


def test_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "collections",
        "documents",
        "chunks",
        "research_jobs",
    }


def test_every_foreign_key_cascades_on_delete() -> None:
    expected = {
        ("collections", "owner_id", "users"),
        ("documents", "owner_id", "users"),
        ("documents", "collection_id", "collections"),
        ("chunks", "document_id", "documents"),
        ("research_jobs", "owner_id", "users"),
        ("research_jobs", "collection_id", "collections"),
    }
    found = set()
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            assert fk.ondelete == "CASCADE", fk
            found.add((table.name, fk.parent.name, fk.column.table.name))
    assert found == expected


def test_constraints() -> None:
    assert User.__table__.c.email.unique
    unique = {
        tuple(c.columns.keys())
        for c in Document.__table__.constraints
        if c.__class__.__name__ == "UniqueConstraint"
    }
    assert ("collection_id", "sha256") in unique


def test_enums_store_lowercase_values() -> None:
    assert Document.__table__.c.status.type.enums == ["queued", "processing", "ready", "failed"]
    assert ResearchJob.__table__.c.status.type.enums == [
        "queued",
        "running",
        "succeeded",
        "failed",
        "cancelled",
    ]


def test_embedding_dimension_matches_settings() -> None:
    assert Chunk.__table__.c.embedding.type.dim == EMBEDDING_DIM == get_settings().embedding_dim


def test_relationships() -> None:
    configure_mappers()
    assert Collection.owner.property.mapper.class_ is User
    assert Document.chunks.property.mapper.class_ is Chunk
    owned = set(User.__mapper__.relationships.keys())
    assert {"collections", "documents", "research_jobs"} <= owned
