"""Focused unit tests for PDF parsing, chunking and document ingestion.

1. PDF extraction, page metadata, and unsupported content types.
2. Chunking (baseline fixed-size, advanced recursive) keeps page metadata.
3. Successful parse -> chunk -> embed -> persist flow.
4. Empty-PDF failure handling and FAILED status transition.

PyMuPDF creates temporary PDFs. Embeddings and SQLAlchemy sessions are faked,
so these tests do not need Gemini, PostgreSQL, Redis, or Docker.

Run from backend/:
    pytest -q tests/unit/test_ingestion.py
"""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

pymupdf = pytest.importorskip(
    "pymupdf",
    reason="Install ingestion dependencies: pip install -e '.[ingest,dev]'",
)

from langchain_core.documents import Document as LCDocument  # noqa: E402

from app.models.document import Chunk, DocumentStatus  # noqa: E402
from workers.ingestion import tasks  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_pdf(path: Path, pages: list[str]) -> Path:
    """Create a small PDF; an empty string creates a blank page."""
    pdf = pymupdf.open()
    try:
        for text in pages:
            page = pdf.new_page()
            if text:
                page.insert_text((72, 72), text)
        pdf.save(path)
    finally:
        pdf.close()
    return path


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _FakeSession:
    """Minimal SQLAlchemy session fake for the ingestion worker."""

    def __init__(self, results: list[Any] | None = None) -> None:
        self._results = list(results or [])
        self.added: list[Any] = []
        self.executed: list[Any] = []
        self.commits = 0

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        return False

    def execute(self, statement: Any) -> _ScalarResult:
        self.executed.append(statement)
        value = self._results.pop(0) if self._results else None
        return _ScalarResult(value)

    def add_all(self, records: list[Any]) -> None:
        self.added.extend(records)

    def commit(self) -> None:
        self.commits += 1


def _install_sessions(
    monkeypatch: pytest.MonkeyPatch,
    *sessions: _FakeSession,
) -> None:
    session_iter = iter(sessions)
    session_factory = lambda: next(session_iter)  # noqa: E731
    monkeypatch.setattr(tasks, "get_sessionmaker", lambda: session_factory)


def _document(storage_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=DocumentStatus.QUEUED,
        storage_path=str(storage_path),
        content_type="application/pdf",
        error=None,
    )


def _settings(strategy: str = "advanced", size: int = 1000, overlap: int = 150):
    return SimpleNamespace(chunk_strategy=strategy, chunk_size=size, chunk_overlap=overlap)


@pytest.fixture(autouse=True)
def _default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never read the real .env: chunking settings are fixed for these tests."""
    monkeypatch.setattr(tasks, "get_settings", lambda: _settings())
    tasks._get_splitter.cache_clear()


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def test_parse_pdf_extracts_text_and_preserves_page_metadata(tmp_path: Path) -> None:
    """Extract non-empty pages, retain 1-based page numbers, reject unsupported types."""
    pdf_path = _write_pdf(
        tmp_path / "multi-page.pdf",
        ["Introduction content", "", "Conclusion content"],
    )

    docs = tasks.parse_document(str(pdf_path), "application/pdf")

    assert [d.page_content for d in docs] == [
        "Introduction content",
        "Conclusion content",
    ]
    assert [d.metadata["page"] for d in docs] == [1, 3]
    # The parser does not infer PDF headings.
    assert [d.metadata.get("section") for d in docs] == [None, None]

    with pytest.raises(ValueError, match="Unsupported content type"):
        tasks.parse_document(str(pdf_path), "text/plain")


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------


def test_chunk_baseline_preserves_overlap_and_page_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fixed-size windows per page, overlapping, never crossing pages."""
    monkeypatch.setattr(tasks, "get_settings", lambda: _settings("baseline", size=6, overlap=2))
    docs = [
        LCDocument(page_content="ABCDEFGHIJ", metadata={"page": 1, "section": "Introduction"}),
        LCDocument(page_content="UVWXYZ12", metadata={"page": 2, "section": "Conclusion"}),
    ]

    chunks = tasks.chunk_baseline(docs)

    assert [c.page_content for c in chunks] == ["ABCDEF", "EFGHIJ", "UVWXYZ", "YZ12"]
    assert [c.metadata["page"] for c in chunks] == [1, 1, 2, 2]
    assert [c.metadata["section"] for c in chunks] == [
        "Introduction",
        "Introduction",
        "Conclusion",
        "Conclusion",
    ]
    assert chunks[0].page_content[-2:] == chunks[1].page_content[:2]
    assert chunks[2].page_content[-2:] == chunks[3].page_content[:2]


def test_chunk_advanced_respects_size_and_keeps_page_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recursive splitting: sizes bounded, page metadata kept, no chunk crosses pages."""
    monkeypatch.setattr(tasks, "get_settings", lambda: _settings("advanced", size=60, overlap=10))
    tasks._get_splitter.cache_clear()
    page1 = "First sentence here. Second sentence follows. Third sentence ends the page."
    page2 = "Other page text. It has two sentences."
    docs = [
        LCDocument(page_content=page1, metadata={"page": 1}),
        LCDocument(page_content=page2, metadata={"page": 2}),
    ]

    chunks = tasks.chunk_advanced(docs)

    assert len(chunks) > 2
    assert all(len(c.page_content) <= 60 for c in chunks)
    assert {c.metadata["page"] for c in chunks} == {1, 2}
    assert all(c.page_content in (page1 if c.metadata["page"] == 1 else page2) for c in chunks)


# ---------------------------------------------------------------------------
# process_document
# ---------------------------------------------------------------------------


def test_process_document_success_runs_pdf_ingestion_and_persists_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise real PDF parsing/chunking and mocked embedding/database persistence."""
    pdf_path = _write_pdf(
        tmp_path / "research.pdf",
        ["First page research content", "Second page research content"],
    )
    document = _document(pdf_path)

    claim_session = _FakeSession([document])
    persist_session = _FakeSession([document, None])
    _install_sessions(monkeypatch, claim_session, persist_session)

    embedded_texts: list[str] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        embedded_texts.extend(texts)
        return [[0.1] * 384 for _ in texts]

    monkeypatch.setattr(tasks, "embed_chunks", fake_embed)

    tasks.process_document(str(document.id))

    assert embedded_texts == [
        "First page research content",
        "Second page research content",
    ]
    assert document.status == DocumentStatus.READY
    assert document.error is None
    assert claim_session.commits == 1
    assert persist_session.commits == 1
    assert len(persist_session.added) == 2
    assert all(isinstance(chunk, Chunk) for chunk in persist_session.added)
    assert [chunk.ordinal for chunk in persist_session.added] == [0, 1]
    assert [chunk.page for chunk in persist_session.added] == [1, 2]
    assert [chunk.text for chunk in persist_session.added] == embedded_texts
    assert all(len(chunk.embedding) == 384 for chunk in persist_session.added)


def test_process_document_empty_pdf_is_marked_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not embed an empty PDF; mark its document FAILED with an explanatory error."""
    pdf_path = _write_pdf(tmp_path / "empty.pdf", ["", "   "])
    document = _document(pdf_path)

    claim_session = _FakeSession([document])
    failure_session = _FakeSession([document])
    _install_sessions(monkeypatch, claim_session, failure_session)

    def unexpected_embedding_call(_texts: list[str]) -> list[list[float]]:
        pytest.fail("Embedding must not be called when the PDF contains no text")

    monkeypatch.setattr(tasks, "embed_chunks", unexpected_embedding_call)

    with pytest.raises(ValueError, match="No extractable text found"):
        tasks.process_document(str(document.id))

    assert document.status == DocumentStatus.FAILED
    assert document.error is not None
    assert document.error.startswith("ValueError:")
    assert claim_session.commits == 1
    assert failure_session.commits == 1
