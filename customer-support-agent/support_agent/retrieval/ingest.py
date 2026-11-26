"""Ingest ShopX Markdown/PDF and publish an embedding snapshot (FR-02)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from support_agent.retrieval.index import Embedder, write_index

HEADING = re.compile(r"^ {0,3}#{1,6}[ \t]+(.+?)$", re.MULTILINE)


@dataclass(frozen=True)
class SourceDocument:
    doc_id: str
    path: Path
    text: str
    pages: tuple[str, ...] = ()


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


def load_documents(kb_dir: Path) -> list[SourceDocument]:
    """Read Markdown and text-layer PDF sources with unique document IDs."""
    if not kb_dir.is_dir():
        raise ValueError(f"Knowledge base directory does not exist: {kb_dir}")
    docs = []
    seen = set()
    for path in sorted(kb_dir.rglob("*")):
        extension = path.suffix.lower()
        if not path.is_file() or extension not in {".md", ".pdf"}:
            continue
        if path.name.lower() == "readme.md":
            continue
        if path.stem.casefold() in seen:
            raise ValueError(f"Duplicate document ID: {path.stem}")
        seen.add(path.stem.casefold())
        if extension == ".pdf":
            from pypdf import PdfReader

            with path.open("rb") as stream:
                pages = tuple(page.extract_text() or "" for page in PdfReader(stream).pages)
            text = "\n\n".join(pages)
            if not text.strip():
                raise ValueError(f"PDF has no extractable text: {path.name}")
            docs.append(SourceDocument(path.stem, path, text, pages))
        else:
            docs.append(SourceDocument(path.stem, path, path.read_text("utf-8")))
    return docs


def _sections(doc: SourceDocument) -> list[tuple[str, dict[str, str]]]:
    if doc.pages:
        return [(text, {"page": str(number)}) for number, text in enumerate(doc.pages, 1)]
    headings = list(HEADING.finditer(doc.text))
    if not headings:
        return [(doc.text, {})]
    blocks = [(doc.text[: headings[0].start()], {})]
    ends = [match.start() for match in headings[1:]] + [len(doc.text)]
    for match, end in zip(headings, ends, strict=True):
        blocks.append((doc.text[match.start() : end], {"section": match.group(1).strip()}))
    return blocks


def chunk_text(doc: SourceDocument, chunk_size: int = 800, overlap: int = 120) -> list[Chunk]:
    """Split by heading or page and apply overlapping windows inside long blocks."""
    if not 0 <= overlap < chunk_size:
        raise ValueError("Expected 0 <= overlap < chunk_size")
    chunks: list[Chunk] = []
    for section_index, (block, metadata) in enumerate(_sections(doc)):
        text = block.strip()
        for start in range(0, len(text), chunk_size - overlap):
            piece = text[start : start + chunk_size]
            identity = f"{doc.doc_id}:{section_index}:{start}:{piece}"
            chunks.append(
                Chunk(
                    chunk_id=hashlib.sha256(identity.encode()).hexdigest(),
                    doc_id=doc.doc_id,
                    text=piece,
                    metadata={"source": doc.path.name, "offset": str(start), **metadata},
                )
            )
            if start + chunk_size >= len(text):
                break
    return chunks


def build_index(
    kb_dir: Path,
    vector_store_dir: Path,
    embedding_model: str,
    *,
    embedding_revision: str | None = None,
    chunk_size: int = 800,
    overlap: int = 120,
    embedder: Embedder | None = None,
) -> int:
    """Build and publish a complete snapshot, replacing stale or deleted chunks."""
    if not 0 <= overlap < chunk_size:
        raise ValueError("Expected 0 <= overlap < chunk_size")
    chunks = [
        chunk for doc in load_documents(kb_dir) for chunk in chunk_text(doc, chunk_size, overlap)
    ]
    write_index(vector_store_dir, chunks, embedding_model, embedding_revision, embedder)
    return len(chunks)
