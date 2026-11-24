"""Gemini embedding with batching and conservative rate limiting."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 32
MAX_TEXTS_PER_MINUTE = 80
RATE_WINDOW_SECONDS = 60.0
MAX_RETRIES = 2

# Track embedding inputs within a rolling 60-second window.
# This limiter is local to the current Python process.
_embedding_timestamps: deque[float] = deque()
_embedding_lock = threading.Lock()


def _reserve_embedding_quota(text_count: int) -> None:
    """Wait until this process has enough embedding quota."""

    if text_count > MAX_TEXTS_PER_MINUTE:
        raise ValueError("Requested batch exceeds the local embedding quota.")

    while True:
        with _embedding_lock:
            now = time.monotonic()

            while _embedding_timestamps and now - _embedding_timestamps[0] >= RATE_WINDOW_SECONDS:
                _embedding_timestamps.popleft()

            if len(_embedding_timestamps) + text_count <= MAX_TEXTS_PER_MINUTE:
                _embedding_timestamps.extend([now] * text_count)
                return

            wait_seconds = _embedding_timestamps[0] + RATE_WINDOW_SECONDS - now

        logger.info(
            "Embedding quota reached; waiting %.1f seconds",
            wait_seconds,
        )
        time.sleep(max(wait_seconds, 0.1))


def _get_retry_delay(exc: APIError) -> float:
    """Read RetryInfo.retryDelay from a Gemini API error."""

    details = getattr(exc, "details", None)

    if not isinstance(details, dict):
        return 30.0

    error = details.get("error", details)

    for item in error.get("details", []):
        if item.get("@type", "").endswith("RetryInfo"):
            retry_delay = item.get("retryDelay", "")

            if isinstance(retry_delay, str) and retry_delay.endswith("s"):
                try:
                    return float(retry_delay[:-1])
                except ValueError:
                    pass

    return 30.0


def embed_chunks(texts: list[str]) -> list[list[float]]:
    """Generate one Gemini embedding per input text."""

    if not texts:
        return []

    settings = get_settings()

    if settings.gemini_api_key is None:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())

    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[start : start + BATCH_SIZE]

        _reserve_embedding_quota(len(batch_texts))

        contents = [types.Content(parts=[types.Part.from_text(text=text)]) for text in batch_texts]

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = client.models.embed_content(
                    model=settings.embedding_model,
                    contents=contents,
                    config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dim),
                )

                batch_embeddings = [
                    [float(value) for value in embedding.values]
                    for embedding in response.embeddings
                ]

                if len(batch_embeddings) != len(batch_texts):
                    raise RuntimeError(
                        "Chunk and embedding counts do not match: "
                        f"{len(batch_texts)} inputs, "
                        f"{len(batch_embeddings)} embeddings."
                    )

                for embedding in batch_embeddings:
                    if len(embedding) != settings.embedding_dim:
                        raise RuntimeError(
                            "Unexpected embedding dimension: "
                            f"expected {settings.embedding_dim}, "
                            f"got {len(embedding)}."
                        )

                all_embeddings.extend(batch_embeddings)

                logger.info(
                    "Embedding batch completed",
                    extra={
                        "batch_size": len(batch_texts),
                        "total_embedded": len(all_embeddings),
                    },
                )

                break

            except APIError as exc:
                if exc.code != 429 or attempt >= MAX_RETRIES:
                    raise

                retry_delay = _get_retry_delay(exc) + 1.0

                logger.warning(
                    "Gemini returned 429; retrying in %.1f seconds",
                    retry_delay,
                )

                time.sleep(retry_delay)

    return all_embeddings
