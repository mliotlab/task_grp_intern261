"""Embedding service: Gemini (API) or local multilingual-e5 (sentence-transformers)."""

from __future__ import annotations

import logging
import re
import time
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 32
MAX_RETRIES = 8


# ============================================================
# Gemini
# ============================================================


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Gemini embedding model (cached)."""

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    settings = get_settings()

    if settings.gemini_api_key is None:
        raise ValueError("GEMINI_API_KEY is not configured.")

    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.gemini_api_key.get_secret_value(),
        output_dimensionality=settings.embedding_dim,
    )


def _is_rate_limited(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


def _retry_delay(exc: Exception) -> float:
    m = re.search(r"retry in ([\d.]+)s", str(exc))
    return float(m.group(1)) + 2 if m else 60.0


def _gemini_batch(embeddings: Embeddings, batch: list[str]) -> list[list[float]]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return embeddings.embed_documents(batch)
        except Exception as exc:
            if not _is_rate_limited(exc) or attempt == MAX_RETRIES:
                raise
            delay = _retry_delay(exc)
            logger.warning("Embedding rate-limited, sleeping %.0fs (attempt %d)", delay, attempt)
            time.sleep(delay)
    raise RuntimeError("unreachable")


def _gemini_chunks(texts: list[str]) -> list[list[float]]:
    embeddings = get_embeddings()
    per_minute = get_settings().embedding_max_texts_per_minute
    vectors: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        started = time.monotonic()
        vectors.extend(_gemini_batch(embeddings, batch))

        remaining = len(batch) * 60.0 / per_minute - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)

    return vectors


# ============================================================
# Local (multilingual-e5)
# ============================================================


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().local_embedding_model)


def _local_chunks(texts: list[str]) -> list[list[float]]:
    vecs = _local_model().encode(
        [f"passage: {t}" for t in texts],
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vecs.tolist()


def _local_query(text: str) -> list[float]:
    return _local_model().encode(f"query: {text}", normalize_embeddings=True).tolist()


# ============================================================
# Public API
# ============================================================


def embed_chunks(texts: list[str]) -> list[list[float]]:
    """Embed document chunks with the configured provider."""

    if not texts:
        return []

    if get_settings().embedding_provider == "local":
        return _local_chunks(texts)
    return _gemini_chunks(texts)


def embed_query(text: str) -> list[float]:
    """Embed a retrieval query with the SAME provider used for ingestion."""

    if get_settings().embedding_provider == "local":
        return _local_query(text)
    return get_embeddings().embed_query(text)
