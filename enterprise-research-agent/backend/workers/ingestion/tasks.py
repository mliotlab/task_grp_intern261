
"""Ingestion worker: parse → chunk → embed → index (FR-02, NFR-03, NFR-04)."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from sqlalchemy import delete, select

from app.core.logging import job_id_var
from app.db.session import get_sessionmaker
from app.models.document import Chunk, Document, DocumentStatus
from workers.embedding import embed_chunks

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedSection:
    text: str
    page: int | None = None
    section: str | None = None


@dataclass(frozen=True)
class EmbeddedChunk:
    ordinal: int
    text: str
    page: int | None
    section: str | None
    embedding: list[float]


def parse_document(
    path: str,
    content_type: str,
) -> list[ParsedSection]:
    """Extract text from a PDF, preserving page information."""

    if content_type.lower() not in {"application/pdf", "pdf"}:
        raise ValueError(f"Unsupported content type: {content_type}")

    sections: list[ParsedSection] = []

    with pymupdf.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            if not text:
                continue

            sections.append(
                ParsedSection(
                    text=text,
                    page=page_number,
                )
            )

    return sections


def chunk_sections(
    sections: list[ParsedSection],
    size: int = 1000,
    overlap: int = 150,
) -> list[ParsedSection]:
    """Split sections into chunks without crossing page boundaries."""

    if size <= 0:
        raise ValueError("size must be greater than 0")

    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")

    chunks: list[ParsedSection] = []
    step = size - overlap

    for section in sections:
        text = section.text

        for start in range(0, len(text), step):
            chunk_text = text[start : start + size]

            if not chunk_text:
                continue

            chunks.append(
                ParsedSection(
                    text=chunk_text,
                    page=section.page,
                    section=section.section,
                )
            )

            if start + size >= len(text):
                break

    return chunks



def process_file(
    path: str,
    content_type: str,
) -> list[EmbeddedChunk]:
    """Parse, chunk and embed a local document."""

    # Parse
    sections = parse_document(path, content_type)

    # Chunk
    chunks = chunk_sections(sections)

    if not chunks:
        return []

    # Embed all chunks in one batch
    embeddings = embed_chunks(
        [chunk.text for chunk in chunks]
    )

    if len(chunks) != len(embeddings):
        raise RuntimeError(
            "Chunk and embedding counts do not match."
        )

    # Combine chunk metadata with embedding vectors
    return [
        EmbeddedChunk(
            ordinal=index,
            text=chunk.text,
            page=chunk.page,
            section=chunk.section,
            embedding=embedding,
        )
        for index, (chunk, embedding) in enumerate(
            zip(chunks, embeddings, strict=True)
        )
    ]


def _mark_document_failed(
    document_id: uuid.UUID,
    error: Exception,
) -> None:
    """Persist failure status in a separate database transaction."""

    with get_sessionmaker()() as db:
        document = db.execute(
            select(Document)
            .where(Document.id == document_id)
            .with_for_update()
        ).scalar_one_or_none()

        if document is None:
            return

        # Do not overwrite a successful result.
        if document.status == DocumentStatus.READY:
            return

        document.status = DocumentStatus.FAILED
        document.error = f"{type(error).__name__}: {error}"

        db.commit()


def process_document(document_id: str) -> None:
    """Execute the complete ingestion pipeline for one document."""

    job_id_var.set(document_id)

    started_at = time.perf_counter()
    claimed = False

    # --------------------------------------------------------
    # Validate document ID
    # --------------------------------------------------------

    try:
        document_uuid = uuid.UUID(document_id)
    except ValueError as exc:
        raise ValueError(
            f"Invalid document ID: {document_id}"
        ) from exc

    try:
        # ----------------------------------------------------
        # Step 1: Load and claim Document
        # ----------------------------------------------------

        with get_sessionmaker()() as db:
            document = db.execute(
                select(Document)
                .where(Document.id == document_uuid)
                .with_for_update()
            ).scalar_one_or_none()

            if document is None:
                raise LookupError(
                    f"Document not found: {document_id}"
                )

            # Idempotency: already successfully ingested.
            if document.status == DocumentStatus.READY:
                logger.info(
                    "Document already processed, skipping",
                    extra={"step": "skip"},
                )
                return

            # Prevent two workers from processing the same document
            # simultaneously.
            if document.status == DocumentStatus.PROCESSING:
                logger.info(
                    "Document is already being processed, skipping",
                    extra={"step": "skip"},
                )
                return

            document.status = DocumentStatus.PROCESSING
            document.error = None

            storage_path = document.storage_path
            content_type = document.content_type

            db.commit()
            claimed = True

        logger.info(
            "Document processing started",
            extra={"step": "start"},
        )

        # ----------------------------------------------------
        # Step 2: Read raw document from Docker Volume
        # ----------------------------------------------------

        file_path = Path(storage_path)

        if not file_path.is_file():
            raise FileNotFoundError(
                f"Document file not found: {storage_path}"
            )

        logger.info(
            "Document file found",
            extra={"step": "load_file"},
        )

        # ----------------------------------------------------
        # Step 3: Parse → Chunk → Embed
        # ----------------------------------------------------

        embedded_chunks = process_file(
            str(file_path),
            content_type,
        )

        if not embedded_chunks:
            raise ValueError(
                "No extractable text found in the document."
            )

        logger.info(
            "Document processing completed",
            extra={
                "step": "process_file",
                "chunk_count": len(embedded_chunks),
            },
        )

        # ----------------------------------------------------
        # Step 4: Persist chunks and update Document status
        # ----------------------------------------------------

        with get_sessionmaker()() as db:
            document = db.execute(
                select(Document)
                .where(Document.id == document_uuid)
                .with_for_update()
            ).scalar_one_or_none()

            if document is None:
                raise LookupError(
                    f"Document was deleted during processing: {document_id}"
                )

            if document.status != DocumentStatus.PROCESSING:
                raise RuntimeError(
                    "Document status changed unexpectedly during processing."
                )

            # Remove previous chunks to support safe reprocessing.
            # This deletion and the new inserts belong to the same
            # transaction.
            db.execute(
                delete(Chunk).where(
                    Chunk.document_id == document_uuid
                )
            )

            chunk_records = [
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

            db.add_all(chunk_records)

            # Mark READY only when chunk persistence succeeds.
            document.status = DocumentStatus.READY
            document.error = None

            # One transaction for:
            # - deleting old chunks
            # - inserting new chunks
            # - updating document status
            db.commit()

        elapsed_ms = round(
            (time.perf_counter() - started_at) * 1000,
            1,
        )

        logger.info(
            "Document ingestion succeeded",
            extra={
                "step": "done",
                "chunk_count": len(embedded_chunks),
                "duration_ms": elapsed_ms,
            },
        )

    except Exception as exc:
        # ----------------------------------------------------
        # Step 5: Handle failure
        # ----------------------------------------------------

        if claimed:
            try:
                _mark_document_failed(
                    document_uuid,
                    exc,
                )
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
