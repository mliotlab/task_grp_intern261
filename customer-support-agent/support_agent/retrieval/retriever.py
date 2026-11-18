"""Retriever interface (FR-03)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RetrievedChunk:
    doc_id: str
    text: str
    score: float


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 4) -> list[RetrievedChunk]: ...


class NullRetriever:
    """Returns nothing. Used until the vector store is implemented, and in tests."""

    def search(self, query: str, top_k: int = 4) -> list[RetrievedChunk]:
        return []


# TODO(FR-03): implement `VectorRetriever` backed by the store built in ingest.build_index.
