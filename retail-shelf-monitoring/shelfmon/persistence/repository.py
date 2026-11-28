"""Transactional repository methods for analysis and alert records."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from shelfmon.persistence.models import AlertRecord, AnalysisRecord
from shelfmon.schemas import AnalysisResult

DEFAULT_UNRESOLVED_ALERT_LIMIT = 100
MAX_UNRESOLVED_ALERT_LIMIT = 500


class PersistenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_analysis(
        self,
        result: AnalysisResult,
        original_image_path: str,
        annotated_image_path: str,
        config_snapshot: dict[str, Any],
    ) -> AlertRecord | None:
        alert = None
        try:
            self.session.add(
                AnalysisRecord(
                    analysis_id=result.analysis_id,
                    store_id=result.store_id,
                    created_at=result.created_at,
                    model_version=result.model_version,
                    product_count=result.product_count,
                    fill_rate=result.fill_rate,
                    alert=result.alert,
                    result_json=result.model_dump(mode="json"),
                    config_snapshot=config_snapshot,
                    original_image_path=original_image_path,
                    annotated_image_path=annotated_image_path,
                )
            )
            if result.alert:
                alert = AlertRecord(
                    alert_id=uuid.uuid4().hex,
                    analysis_id=result.analysis_id,
                    reason="no_detection" if result.product_count == 0 else "low_fill",
                    status="unresolved",
                    created_at=datetime.now(UTC),
                )
                self.session.add(alert)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return alert

    def get_analysis(self, analysis_id: str) -> AnalysisRecord | None:
        return self.session.get(AnalysisRecord, analysis_id)

    def list_analyses(
        self,
        store_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
    ) -> list[AnalysisRecord]:
        statement = select(AnalysisRecord)
        if store_id is not None:
            statement = statement.where(AnalysisRecord.store_id == store_id)
        if since is not None:
            statement = statement.where(AnalysisRecord.created_at >= since)
        if until is not None:
            statement = statement.where(AnalysisRecord.created_at <= until)
        statement = statement.order_by(AnalysisRecord.created_at.desc()).limit(limit)
        return list(self.session.scalars(statement))

    def list_unresolved_alerts(
        self, limit: int = DEFAULT_UNRESOLVED_ALERT_LIMIT
    ) -> list[AlertRecord]:
        if not 1 <= limit <= MAX_UNRESOLVED_ALERT_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_UNRESOLVED_ALERT_LIMIT}")
        statement = (
            select(AlertRecord)
            .where(AlertRecord.status == "unresolved")
            .order_by(AlertRecord.created_at.desc(), AlertRecord.alert_id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def resolve_alert(self, alert_id: str) -> AlertRecord | None:
        try:
            alert = self.session.scalar(
                select(AlertRecord).where(AlertRecord.alert_id == alert_id).with_for_update()
            )
            if alert is None:
                self.session.rollback()
                return None
            alert.status = "resolved"
            alert.resolved_at = datetime.now(UTC)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return alert
