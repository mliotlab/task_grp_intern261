"""S2-01: constraints and relationships of the models, checked on real PostgreSQL."""

# ruff: noqa: S106 - fake credentials in tests

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Chunk, Collection, Document, DocumentStatus, ResearchJob, User
from app.models.document import EMBEDDING_DIM

pytestmark = pytest.mark.integration


def _seed(db: Session) -> tuple[User, Collection, Document]:
    user = User(email="owner@example.com", password_hash="x")
    collection = Collection(owner=user, name="NIST SP 800")
    document = Document(
        owner=user,
        collection=collection,
        filename="NIST.SP.800-53r5.pdf",
        content_type="application/pdf",
        size_bytes=10,
        sha256=hashlib.sha256(b"doc").hexdigest(),
        storage_path="uploads/a.pdf",
    )
    document.chunks.append(
        Chunk(ordinal=0, text="AC-2", page=18, section="AC-2", embedding=[0.0] * EMBEDDING_DIM)
    )
    db.add_all([user, ResearchJob(owner=user, collection=collection, question="What is AC-2?")])
    db.commit()
    return user, collection, document


def test_defaults_and_enum_values_are_lowercase(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    with Session(migrated_engine) as db:
        _, _, document = _seed(db)
        job = db.scalars(select(ResearchJob)).one()
        assert document.status is DocumentStatus.QUEUED
        assert (job.attempts, job.steps, job.citations) == (0, [], [])
        assert document.created_at is not None
        # The stored value is "queued" (as in the API and FR-02), not the member name "QUEUED".
        raw = db.scalar(text("SELECT status::text FROM documents"))
        assert raw == "queued"


def test_same_file_twice_in_a_collection_is_rejected(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    with Session(migrated_engine) as db:
        user, collection, document = _seed(db)
        db.add(
            Document(
                owner=user,
                collection=collection,
                filename="copy.pdf",
                content_type="application/pdf",
                size_bytes=10,
                sha256=document.sha256,
                storage_path="uploads/b.pdf",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_email_is_unique(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    with Session(migrated_engine) as db:
        db.add_all([User(email="a@example.com", password_hash="x")])
        db.commit()
        db.add(User(email="a@example.com", password_hash="y"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_deleting_a_user_cascades_to_everything_they_own(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    with Session(migrated_engine) as db:
        user, _, _ = _seed(db)
        db.delete(user)
        db.commit()
        for model in (Collection, Document, Chunk, ResearchJob):
            assert db.scalar(select(func.count()).select_from(model)) == 0, model.__name__
