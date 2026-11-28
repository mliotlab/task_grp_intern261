"""SQLAlchemy engine and session lifecycle."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from shelfmon.config import get_settings
from shelfmon.persistence.models import Base


@lru_cache(maxsize=8)
def get_engine(database_url: str) -> Engine:
    options: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **options)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection: object, _: object) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_schema(engine: Engine) -> None:
    """Create missing MVP tables at application startup; this is not a migration system."""
    Base.metadata.create_all(engine)


@lru_cache(maxsize=8)
def get_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(database_url), expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    database_url = get_settings().database_url
    with get_session_factory(database_url)() as session:
        yield session
