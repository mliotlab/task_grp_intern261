"""Ingestion pipeline: read kb/ → chunk → embed → store (FR-02).

A naive baseline is provided for loading Markdown and fixed-size chunking so the pipeline runs
end-to-end from day one. Improving it (heading-aware chunks, PDF support, idempotent re-index)
is part of the project.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SourceDocument:
    doc_id: str
    path: Path
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


def load_documents(kb_dir: Path) -> list[SourceDocument]:
    """Load every Markdown file in `kb_dir`. The file stem is the `doc_id` used in citations."""
    docs = []
    for path in sorted(kb_dir.glob("**/*.md")):
        if path.name.lower() == "readme.md":
            continue
        docs.append(SourceDocument(doc_id=path.stem, path=path, text=path.read_text("utf-8")))
    # TODO(FR-02): support PDF files (pypdf) in addition to Markdown.
    return docs


def chunk_text(doc: SourceDocument, chunk_size: int = 800, overlap: int = 120) -> list[Chunk]:
    """Baseline fixed-size character chunking with overlap.

    TODO(FR-02): split on Markdown headings first so each chunk keeps its section title,
    and store the heading in `metadata["section"]` for better citations.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    text = doc.text.strip()
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        piece = text[start : start + chunk_size]
        digest = hashlib.sha1(f"{doc.doc_id}:{start}:{piece}".encode(), usedforsecurity=False)
        chunks.append(
            Chunk(
                chunk_id=digest.hexdigest()[:16],
                doc_id=doc.doc_id,
                text=piece,
                metadata={"source": str(doc.path.name), "offset": str(start)},
            )
        )
        if start + chunk_size >= len(text):
            break
        start += chunk_size - overlap
    return chunks


def build_index(kb_dir: Path, vector_store_dir: Path, embedding_model: str) -> int:
    """Embed all chunks and persist them in the vector store. Returns the number of chunks.

    TODO(FR-02): implement with Chroma or FAISS (`pip install -e ".[rag]"`).
      - Use a multilingual embedding model (e.g. multilingual-e5 / bge-m3), remember E5 prefixes.
      - Make re-runs idempotent: upsert by `chunk_id`, delete chunks of removed documents.
    """
    raise NotImplementedError("Vector index is not implemented yet (FR-02)")
