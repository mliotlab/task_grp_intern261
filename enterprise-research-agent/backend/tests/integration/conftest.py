from __future__ import annotations

import hashlib
import os
import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models.collection import Collection
from app.models.document import EMBEDDING_DIM, Chunk, Document, DocumentStatus
from app.models.user import User
from workers.embedding import embed_chunks


@pytest.fixture
def seeded_gemini_retrieval_data():
    """Create temporary PostgreSQL/pgvector data for live Gemini retrieval."""

    # Do not call Gemini or touch the database unless explicitly enabled.
    if os.getenv("ERA_RUN_GEMINI_TESTS") != "1":
        pytest.skip("Set ERA_RUN_GEMINI_TESTS=1 to enable live Gemini tests")

    settings = get_settings()

    # Protect development and production databases.
    database_name = (make_url(settings.database_url).database or "").lower()
    if "test" not in database_name:
        raise RuntimeError(
            "Refusing to seed integration data into a non-test database. "
            "Set DATABASE_URL to a dedicated database whose name contains 'test'."
        )

    if settings.embedding_dim != EMBEDDING_DIM:
        raise RuntimeError(
            f"Database expects {EMBEDDING_DIM}-dimensional vectors, "
            f"but embedding_dim is {settings.embedding_dim}."
        )

    token = uuid.uuid4().hex
    filename = f"gemini-retrieval-{token}.pdf"

    text = (
        "The main objectives of this research are to identify the key factors, "
        "evaluate their impact, and propose practical recommendations."
    )

    # Use the real Gemini embedding model to seed pgvector.
    embeddings = embed_chunks([text])

    if len(embeddings) != 1 or len(embeddings[0]) != EMBEDDING_DIM:
        raise RuntimeError("Gemini returned an unexpected embedding.")

    embedding = embeddings[0]

    # Create isolated records.
    with get_sessionmaker()() as db:
        owner = User(
            email=f"gemini-retrieval-{token}@example.test",
            password_hash=hashlib.sha256(f"integration-test:{token}".encode()).hexdigest(),
        )
        db.add(owner)
        db.flush()

        collection = Collection(
            owner_id=owner.id,
            name=f"Gemini retrieval test {token}",
            description="Temporary integration-test collection.",
        )
        db.add(collection)
        db.flush()

        document = Document(
            owner_id=owner.id,
            collection_id=collection.id,
            filename=filename,
            content_type="application/pdf",
            size_bytes=len(text.encode("utf-8")),
            sha256=hashlib.sha256(f"{token}:{text}".encode()).hexdigest(),
            storage_path=f"integration-tests/{token}/{filename}",
            status=DocumentStatus.READY,
        )
        db.add(document)
        db.flush()

        chunk = Chunk(
            document_id=document.id,
            ordinal=0,
            text=text,
            page=1,
            section="Research objectives",
            embedding=embedding,
        )
        db.add(chunk)
        db.flush()

        # Commit so retrieve_top_k() can see the records using its own sessions.
        data = {
            "owner_id": owner.id,
            "collection_id": collection.id,
            "document_id": document.id,
            "chunk_id": chunk.id,
            "filename": filename,
            "text": text,
        }
        db.commit()

    try:
        yield data

    finally:
        # Delete in foreign-key dependency order.
        with get_sessionmaker()() as db:
            db.execute(delete(Chunk).where(Chunk.document_id == data["document_id"]))
            db.execute(delete(Document).where(Document.id == data["document_id"]))
            db.execute(delete(Collection).where(Collection.id == data["collection_id"]))
            db.execute(delete(User).where(User.id == data["owner_id"]))
            db.commit()


# --- S2-01: throwaway PostgreSQL database with the Alembic schema -----------------------------


def _alembic_config(connection):  # type: ignore[no-untyped-def]
    from pathlib import Path

    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.attributes["connection"] = connection
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture
def make_database():
    """Factory: create an empty database next to DATABASE_URL, drop it after the test.

    Never touches the database in DATABASE_URL itself, so a dev database is safe.
    """
    from sqlalchemy import create_engine, text

    settings = get_settings()
    if settings.app_env != "test":
        raise RuntimeError("Integration DB fixtures only run with APP_ENV=test.")
    admin = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    created: list[str] = []

    def _make():  # type: ignore[no-untyped-def]
        name = f"era_s201_{uuid.uuid4().hex[:12]}"
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        created.append(name)
        return create_engine(make_url(settings.database_url).set(database=name))

    try:
        yield _make
    finally:
        with admin.connect() as conn:
            for name in created:
                conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def run_alembic():
    """run_alembic(engine, "upgrade", "head") / run_alembic(engine, "downgrade", "base")."""
    from alembic import command

    def _run(engine, action: str, revision: str) -> None:  # type: ignore[no-untyped-def]
        with engine.begin() as connection:
            getattr(command, action)(_alembic_config(connection), revision)

    return _run


@pytest.fixture
def migrated_engine(make_database, run_alembic):  # type: ignore[no-untyped-def]
    """A fresh database at Alembic head."""
    engine = make_database()
    run_alembic(engine, "upgrade", "head")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_client(migrated_engine):  # type: ignore[no-untyped-def]
    """TestClient whose API sessions use the migrated throwaway database."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.db.session import get_db
    from app.main import app

    factory = sessionmaker(bind=migrated_engine, expire_on_commit=False)

    def _get_db():  # type: ignore[no-untyped-def]
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = _get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
