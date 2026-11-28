from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateTable

from shelfmon.config import Settings
from shelfmon.persistence import database
from shelfmon.persistence.image_storage import ArtifactAlreadyExistsError, ImageStorage
from shelfmon.persistence.models import AlertRecord, AnalysisRecord, Base
from shelfmon.persistence.repository import PersistenceRepository
from shelfmon.schemas import AnalysisResult, BoundingBox, ShelfRow


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db_session:
        yield db_session
    engine.dispose()


def make_result(
    analysis_id: str,
    *,
    alert: bool = False,
    product_count: int = 1,
    rows: list[ShelfRow] | None = None,
) -> AnalysisResult:
    boxes = [BoundingBox(x1=0, y1=0, x2=10, y2=20, confidence=0.9)] if product_count else []
    if rows is None:
        rows = [ShelfRow(index=0, y1=0, y2=20, boxes=boxes, fill_rate=0.5)] if boxes else []
    return AnalysisResult(
        analysis_id=analysis_id,
        store_id="S001",
        created_at=datetime(2026, 11, 26, 12, tzinfo=UTC),
        model_version="test-model",
        product_count=product_count,
        boxes=boxes,
        rows=rows,
        gaps=[],
        fill_rate=0.5 if alert else 1.0,
        alert=alert,
        timings_ms={"inference": 2.0},
    )


def persist(repository: PersistenceRepository, result: AnalysisResult) -> AlertRecord | None:
    return repository.save_analysis(
        result,
        f"S001/{result.analysis_id}_original.png",
        f"S001/{result.analysis_id}_annotated.png",
        {"fill_rate_alert_threshold": 0.8},
    )


def test_save_analysis_stores_complete_json_and_relative_paths(session: Session) -> None:
    repository = PersistenceRepository(session)
    result = make_result("analysis-1")

    assert persist(repository, result) is None
    stored = repository.get_analysis("analysis-1")

    assert stored is not None
    assert stored.result_json == result.model_dump(mode="json")
    assert stored.original_image_path == "S001/analysis-1_original.png"
    assert stored.config_snapshot["fill_rate_alert_threshold"] == 0.8
    assert session.scalar(select(func.count()).select_from(AlertRecord)) == 0


@pytest.mark.parametrize(
    ("product_count", "expected_reason"), [(2, "low_fill"), (0, "no_detection")]
)
def test_save_analysis_creates_one_unresolved_alert(
    session: Session, product_count: int, expected_reason: str
) -> None:
    repository = PersistenceRepository(session)
    result = make_result("analysis-alert", alert=True, product_count=product_count)

    alert = persist(repository, result)

    assert alert is not None
    assert alert.status == "unresolved"
    assert alert.resolved_at is None
    assert alert.reason == expected_reason
    assert alert.created_at.tzinfo == UTC
    assert session.scalar(select(func.count()).select_from(AlertRecord)) == 1


def test_save_analysis_with_empty_row_creates_low_fill_alert(session: Session) -> None:
    repository = PersistenceRepository(session)
    empty_row = ShelfRow(index=0, y1=0, y2=20, boxes=[], fill_rate=0.0)
    result = make_result(
        "analysis-empty-row",
        alert=True,
        product_count=0,
        rows=[empty_row],
    )

    alert = persist(repository, result)

    assert alert is not None
    assert alert.reason == "low_fill"
    assert alert.status == "unresolved"
    assert alert.resolved_at is None


def test_list_and_resolve_alert_removes_it_from_unresolved_filter(session: Session) -> None:
    repository = PersistenceRepository(session)
    persist(repository, make_result("analysis-alert", alert=True))
    alert = repository.list_unresolved_alerts()[0]

    resolved = repository.resolve_alert(alert.alert_id)

    assert resolved is not None
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None
    assert resolved.resolved_at.tzinfo == UTC
    assert repository.list_unresolved_alerts() == []


def test_unresolved_alert_repository_applies_requested_limit(session: Session) -> None:
    repository = PersistenceRepository(session)
    for index in range(4):
        persist(repository, make_result(f"analysis-limit-{index}", alert=True))

    assert len(repository.list_unresolved_alerts(limit=2)) == 2
    assert len(repository.list_unresolved_alerts()) == 4
    with pytest.raises(ValueError, match="limit must be between 1"):
        repository.list_unresolved_alerts(limit=501)


def test_resolve_unknown_alert_returns_none(session: Session) -> None:
    assert PersistenceRepository(session).resolve_alert("missing") is None


def test_analysis_json_column_compiles_as_postgresql_jsonb() -> None:
    ddl = str(CreateTable(AnalysisRecord.__table__).compile(dialect=postgresql.dialect()))
    assert "JSONB" in ddl


def test_list_analyses_filters_store_and_time(session: Session) -> None:
    repository = PersistenceRepository(session)
    first = make_result("analysis-a")
    second = make_result("analysis-b").model_copy(update={"store_id": "S002"})
    persist(repository, first)
    repository.save_analysis(second, "S002/original.png", "S002/annotated.png", {})

    matches = repository.list_analyses(
        store_id="S001", since=datetime(2026, 11, 26, 11, tzinfo=UTC), limit=10
    )
    assert [analysis.analysis_id for analysis in matches] == ["analysis-a"]


def test_analysis_and_alert_insert_roll_back_together(session: Session) -> None:
    def reject_alert(_: object, __: object, ___: AlertRecord) -> None:
        raise RuntimeError("simulated alert insert failure")

    event.listen(AlertRecord, "before_insert", reject_alert)
    try:
        with pytest.raises(RuntimeError, match="simulated alert insert failure"):
            persist(
                PersistenceRepository(session),
                make_result("analysis-rollback", alert=True),
            )
    finally:
        event.remove(AlertRecord, "before_insert", reject_alert)

    assert session.get(AnalysisRecord, "analysis-rollback") is None


def test_image_storage_writes_relative_paths_and_rejects_traversal(tmp_path: Path) -> None:
    storage = ImageStorage(tmp_path / "images")
    original_path, annotated_path = storage.save(
        "S001", "analysis-1", b"source", np.zeros((4, 4, 3), dtype=np.uint8), ".png"
    )

    assert original_path == "S001/analysis-1_original.png"
    assert annotated_path == "S001/analysis-1_annotated.png"
    assert (tmp_path / "images" / original_path).read_bytes() == b"source"
    with pytest.raises(ValueError, match="store_id"):
        storage.save(
            "../outside",
            "analysis-2",
            b"source",
            np.zeros((1, 1, 3), dtype=np.uint8),
            ".png",
        )


def test_image_storage_duplicate_id_preserves_existing_artifacts(tmp_path: Path) -> None:
    storage = ImageStorage(tmp_path / "images")
    original_path, annotated_path = storage.save(
        "S001", "analysis-duplicate", b"first-original", np.zeros((4, 4, 3)), ".png"
    )
    original_file = tmp_path / "images" / original_path
    annotated_file = tmp_path / "images" / annotated_path

    with pytest.raises(ArtifactAlreadyExistsError):
        storage.save("S001", "analysis-duplicate", b"second-original", np.ones((4, 4, 3)), ".png")

    assert original_file.read_bytes() == b"first-original"
    assert annotated_file.exists()


def test_duplicate_database_insert_cleans_only_current_attempt_artifacts(
    session: Session, tmp_path: Path
) -> None:
    storage = ImageStorage(tmp_path / "images")
    repository = PersistenceRepository(session)
    result = make_result("analysis-db-duplicate")
    first_paths = storage.save(
        "S001", result.analysis_id, b"first-original", np.zeros((4, 4, 3)), ".png"
    )
    repository.save_analysis(result, *first_paths, {})

    retry_paths = storage.save(
        "S001", result.analysis_id, b"retry-original", np.ones((4, 4, 3)), ".jpg"
    )
    with pytest.raises(IntegrityError):
        repository.save_analysis(result, *retry_paths, {})
    storage.remove(*retry_paths)

    image_dir = tmp_path / "images" / "S001"
    assert (image_dir / f"{result.analysis_id}_original.png").read_bytes() == b"first-original"
    assert (image_dir / f"{result.analysis_id}_annotated.png").exists()
    assert not (image_dir / f"{result.analysis_id}_original.jpg").exists()
    assert not (image_dir / f"{result.analysis_id}_annotated.jpg").exists()


def test_request_session_creation_does_not_create_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = "sqlite+pysqlite:///:memory:?phase1-session-test"
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: Settings(database_url=database_url),
    )
    monkeypatch.setattr(
        database,
        "create_schema",
        lambda _: pytest.fail("schema creation must not run on request"),
    )

    session_generator = database.get_db_session()
    session = next(session_generator)
    assert isinstance(session, Session)
    session_generator.close()
