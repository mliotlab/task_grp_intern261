"""Persistent, exact cosine vector index for the small Sprint 2 corpus."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from support_agent.retrieval.ingest import Chunk

INDEX_FILENAME = "policy-index.npz"
INDEX_VERSION = 1


class Embedder(Protocol):
    def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]: ...


class SentenceEmbedder:
    def __init__(self, model_id: str, revision: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_id, revision=revision)
        self.is_e5 = "e5-" in model_id.rsplit("/", 1)[-1].lower()

    def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        if self.is_e5:
            prefix = "query: " if query else "passage: "
            texts = [prefix + text for text in texts]
        return self.model.encode(texts, show_progress_bar=False).tolist()


def normalized_vectors(vectors: list[list[float]], expected: int) -> NDArray:
    import numpy as np

    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] != expected or not matrix.shape[1]:
        raise ValueError("Embedder returned an incompatible vector matrix.")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms == 0):
        raise ValueError("Embedder returned a non-finite or zero vector.")
    return matrix / norms


def write_index(
    directory: Path,
    chunks: list[Chunk],
    model: str,
    revision: str | None,
    embedder: Embedder | None,
) -> None:
    import numpy as np

    if chunks:
        embedder = embedder or SentenceEmbedder(model, revision)
        passages = []
        for chunk in chunks:
            section = chunk.metadata.get("section")
            passages.append(f"{section}\n{chunk.text}" if section else chunk.text)
        vectors = normalized_vectors(embedder.encode(passages), len(chunks))
    else:
        vectors = np.empty((0, 0), dtype=np.float32)

    payload = json.dumps(
        {
            "version": INDEX_VERSION,
            "model": model,
            "revision": revision,
            "chunks": [asdict(chunk) for chunk in chunks],
        },
        ensure_ascii=False,
    )
    directory.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=directory, suffix=".npz", delete=False) as stream:
        pending = Path(stream.name)
    try:
        np.savez_compressed(pending, metadata=payload, vectors=vectors)
        os.replace(pending, directory / INDEX_FILENAME)
    finally:
        pending.unlink(missing_ok=True)
