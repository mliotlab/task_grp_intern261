"""Retriever interface (FR-03)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from support_agent.retrieval.index import (
    INDEX_FILENAME,
    INDEX_VERSION,
    Embedder,
    SentenceEmbedder,
    normalized_vectors,
)
from support_agent.retrieval.ingest import Chunk


@dataclass(frozen=True)
class RetrievedChunk:
    doc_id: str
    text: str
    score: float
    chunk_id: str | None = None


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 4) -> list[RetrievedChunk]: ...


class NullRetriever:
    """Empty retriever for the mock scaffold and tests."""

    def search(self, query: str, top_k: int = 4) -> list[RetrievedChunk]:
        return []


class VectorRetriever:
    """Load a published snapshot and rank chunks by exact cosine similarity."""

    def __init__(
        self,
        directory: Path,
        embedding_model: str,
        *,
        embedding_revision: str | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        import numpy as np

        with np.load(directory / INDEX_FILENAME, allow_pickle=False) as snapshot:
            info = json.loads(snapshot["metadata"].item())
            self.vectors = snapshot["vectors"]
        if (info["version"], info["model"], info["revision"]) != (
            INDEX_VERSION,
            embedding_model,
            embedding_revision,
        ):
            raise ValueError("Vector index and embedding settings differ; rebuild the index.")
        self.chunks = [Chunk(**chunk) for chunk in info["chunks"]]
        if self.vectors.ndim != 2 or len(self.vectors) != len(self.chunks):
            raise ValueError("Vector index and chunk metadata are inconsistent.")
        self.embedder = embedder
        if self.chunks and self.embedder is None:
            self.embedder = SentenceEmbedder(embedding_model, embedding_revision)

    def search(self, query: str, top_k: int = 4) -> list[RetrievedChunk]:
        if self.embedder is None or not query.strip() or top_k <= 0 or not self.chunks:
            return []
        query_vector = normalized_vectors(self.embedder.encode([query], query=True), 1)[0]
        if len(query_vector) != self.vectors.shape[1]:
            raise ValueError("Query embedding dimension differs from the index.")
        scores = (self.vectors @ query_vector).clip(-1.0, 1.0)
        return [
            RetrievedChunk(
                self.chunks[i].doc_id,
                self.chunks[i].text,
                float(scores[i]),
                self.chunks[i].chunk_id,
            )
            for i in (-scores).argsort(kind="stable")[:top_k]
        ]
