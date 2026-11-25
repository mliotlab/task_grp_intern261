"""Ingestion worker: parse → chunk → embed → index (FR-02, NFR-03, NFR-04)."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import pymupdf
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.logging import job_id_var
from app.db.session import get_sessionmaker
from app.models.document import Chunk, Document, DocumentStatus
from workers.embedding import embed_chunks

logger = logging.getLogger(__name__)
STALE_AFTER = timedelta(seconds=700)


@dataclass(frozen=True)
class EmbeddedChunk:
    ordinal: int
    text: str
    page: int | None
    section: str | None
    embedding: list[float]


# ============================================================
# Parse
# ============================================================


def parse_document(path: str, content_type: str) -> list[LCDocument]:
    """Extract text from a PDF, one LangChain Document per page."""

    if content_type.lower() not in {"application/pdf", "pdf"}:
        raise ValueError(f"Unsupported content type: {content_type}")

    with pymupdf.open(path) as pdf:
        return [
            LCDocument(page_content=text, metadata={"page": n})
            for n, page in enumerate(pdf, start=1)
            if (text := page.get_text("text").strip())
        ]


# ============================================================
# Chunk (baseline vs advanced)
# ============================================================


@lru_cache(maxsize=1)
def _get_splitter() -> RecursiveCharacterTextSplitter:
    settings = get_settings()
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


def chunk_baseline(docs: list[LCDocument]) -> list[LCDocument]:
    """Fixed-size character windows; ignores paragraph/sentence boundaries.

    Never crosses page boundaries (each page is chunked separately).
    """

    settings = get_settings()
    size = settings.chunk_size
    step = size - settings.chunk_overlap
    chunks: list[LCDocument] = []

    for doc in docs:
        text = doc.page_content

        for start in range(0, len(text), step):
            chunks.append(
                LCDocument(
                    page_content=text[start : start + size],
                    metadata=dict(doc.metadata),
                )
            )

            if start + size >= len(text):
                break

    return chunks


def chunk_advanced(docs: list[LCDocument]) -> list[LCDocument]:
    """Recursive split: paragraph → line → sentence → word."""

    return _get_splitter().split_documents(docs)


CHUNKERS: dict[str, Callable[[list[LCDocument]], list[LCDocument]]] = {
    "baseline": chunk_baseline,
    "advanced": chunk_advanced,
}


# ============================================================
# Parse → Chunk → Embed
# ============================================================


def process_file(path: str, content_type: str) -> list[EmbeddedChunk]:
    """Parse, chunk (per CHUNK_STRATEGY) and embed a local document."""

    strategy = get_settings().chunk_strategy

    t0 = time.perf_counter()
    docs = parse_document(path, content_type)
    t1 = time.perf_counter()
    chunks = CHUNKERS[strategy](docs)
    t2 = time.perf_counter()

    if not chunks:
        return []

    embeddings = embed_chunks([c.page_content for c in chunks])
    t3 = time.perf_counter()

    logger.info(
        "timing parse=%.2fs chunk=%.2fs embed=%.2fs chunks=%d (%.1f chunk/s embed)",
        t1 - t0,
        t2 - t1,
        t3 - t2,
        len(chunks),
        len(chunks) / max(t3 - t2, 1e-9),
    )

    return [
        EmbeddedChunk(
            ordinal=i,
            text=c.page_content,
            page=c.metadata.get("page"),
            section=c.metadata.get("section"),
            embedding=emb,
        )
        for i, (c, emb) in enumerate(zip(chunks, embeddings, strict=True))
    ]


# ============================================================
# Failure handling
# ============================================================


def _mark_document_failed(
    document_id: uuid.UUID,
    error: Exception,
) -> None:
    """Persist failure status in a separate database transaction."""

    with get_sessionmaker()() as db:
        document = db.execute(
            select(Document).where(Document.id == document_id).with_for_update()
        ).scalar_one_or_none()

        if document is None:
            return

        # Do not overwrite a successful result.
        if document.status == DocumentStatus.READY:
            return

        document.status = DocumentStatus.FAILED
        document.error = f"{type(error).__name__}: {error}"

        db.commit()


# ============================================================
# RQ entrypoint
# ============================================================


def process_document(document_id: str) -> None:
    """Execute the complete ingestion pipeline for one document."""

    job_id_var.set(document_id)

    started_at = time.perf_counter()
    claimed = False
    strategy = get_settings().chunk_strategy

    try:
        document_uuid = uuid.UUID(document_id)
    except ValueError as exc:
        raise ValueError(f"Invalid document ID: {document_id}") from exc

    try:
        # Step 1: Load and claim Document
        with get_sessionmaker()() as db:
            document = db.execute(
                select(Document).where(Document.id == document_uuid).with_for_update()
            ).scalar_one_or_none()

            if document is None:
                raise LookupError(f"Document not found: {document_id}")

            if document.status == DocumentStatus.READY:
                logger.info(
                    "Document already processed, skipping",
                    extra={"step": "skip"},
                )
                return

            if document.status == DocumentStatus.PROCESSING:
                age = datetime.now(UTC) - document.updated_at
                if age < STALE_AFTER:
                    logger.info(
                        "Document is already being processed, skipping",
                        extra={"step": "skip"},
                    )
                    return
                logger.warning("Reclaiming stale PROCESSING document", extra={"step": "reclaim"})

            document.status = DocumentStatus.PROCESSING
            document.error = None

            storage_path = document.storage_path
            content_type = document.content_type

            db.commit()
            claimed = True

        logger.info(
            "Document processing started",
            extra={"step": "start", "strategy": strategy},
        )

        # Step 2: Locate file on Docker volume
        file_path = Path(storage_path)

        if not file_path.is_file():
            raise FileNotFoundError(f"Document file not found: {storage_path}")

        # Step 3: Parse → Chunk → Embed
        embedded_chunks = process_file(str(file_path), content_type)

        if not embedded_chunks:
            raise ValueError("No extractable text found in the document.")

        logger.info(
            "Document processing completed",
            extra={
                "step": "process_file",
                "strategy": strategy,
                "chunk_count": len(embedded_chunks),
            },
        )

        # Step 4: Persist chunks + mark READY (single transaction)
        with get_sessionmaker()() as db:
            document = db.execute(
                select(Document).where(Document.id == document_uuid).with_for_update()
            ).scalar_one_or_none()

            if document is None:
                raise LookupError(f"Document was deleted during processing: {document_id}")

            if document.status != DocumentStatus.PROCESSING:
                raise RuntimeError("Document status changed unexpectedly during processing.")

            db.execute(delete(Chunk).where(Chunk.document_id == document_uuid))

            db.add_all(
                [
                    Chunk(
                        document_id=document_uuid,
                        ordinal=item.ordinal,
                        text=item.text,
                        page=item.page,
                        section=item.section,
                        embedding=item.embedding,
                    )
                    for item in embedded_chunks
                ]
            )

            document.status = DocumentStatus.READY
            document.error = None

            db.commit()

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 1)

        logger.info(
            "Document ingestion succeeded",
            extra={
                "step": "done",
                "strategy": strategy,
                "chunk_count": len(embedded_chunks),
                "duration_ms": elapsed_ms,
            },
        )

    except Exception as exc:
        # Step 5: Handle failure
        if claimed:
            try:
                _mark_document_failed(document_uuid, exc)
            except Exception:
                logger.exception(
                    "Failed to update document failure status",
                    extra={"step": "mark_failed"},
                )

        logger.exception(
            "Document ingestion failed",
            extra={"step": "failed"},
        )

        # Re-raise so RQ can apply its retry policy.
        raise
