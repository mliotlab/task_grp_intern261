"""Ingestion worker: parse → chunk → embed → index (FR-02, NFR-03, NFR-04)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.logging import job_id_var

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedSection:
    text: str
    page: int | None = None
    section: str | None = None


def parse_document(path: str, content_type: str) -> list[ParsedSection]:
    """TODO(FR-02): PDF via PyMuPDF (one section per page), DOCX via python-docx (by heading),
    Markdown by '#' headings. Keep page / section for citations."""
    raise NotImplementedError


def chunk_sections(
    sections: list[ParsedSection], size: int = 1000, overlap: int = 150
) -> list[ParsedSection]:
    """TODO(FR-02): split long sections, never across pages; keep page/section metadata."""
    raise NotImplementedError


def process_document(document_id: str) -> None:
    """Entry point executed by `rq worker ingestion`.

    TODO(FR-02, NFR-04):
      1. load Document; if status == ready → return (idempotent re-run);
      2. status = processing; parse → chunk → embed (batch) → insert Chunk rows in ONE transaction;
      3. status = ready, or failed + error message on exception (re-raise so RQ retries);
      4. log step durations (NFR-06). Target: a 100-page PDF in ≤ 2 minutes (NFR-03).
    """
    job_id_var.set(document_id)
    logger.info("process_document called", extra={"step": "start"})
    raise NotImplementedError("Ingestion is not implemented yet (FR-02)")
