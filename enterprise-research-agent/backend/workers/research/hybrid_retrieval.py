"""Hybrid retrieval: Dense Search + BM25 + Reciprocal Rank Fusion (ERA-39)."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models.collection import Collection
from app.models.document import (
    Chunk,
    Document,
    DocumentStatus,
)
from workers.research.retrieve import retrieve_top_k

logger = logging.getLogger(__name__)

# Preserve technical terms such as 800-53, MFA and CVE-2024-1234.
TOKEN_PATTERN = re.compile(r"(?u)\b\w+(?:[-./]\w+)*\b")


# ============================================================
# Step 1: Tokenization
# ============================================================


def _tokenize(text: str) -> list[str]:
    """Normalize and tokenize text for BM25."""

    if not isinstance(text, str):
        raise TypeError("Text must be a string.")

    return TOKEN_PATTERN.findall(text.casefold())


# ============================================================
# Step 2: Resolve retrieval configuration
# ============================================================


def _resolve_retrieval_params(
    top_k: int | None = None,
    candidate_k: int | None = None,
    rrf_k: int | None = None,
) -> tuple[int, int, int]:
    """Resolve retrieval parameters from explicit arguments or Settings."""

    settings = get_settings()

    resolved = (
        settings.retrieval_top_k if top_k is None else top_k,
        settings.retrieval_candidate_k if candidate_k is None else candidate_k,
        settings.retrieval_rrf_k if rrf_k is None else rrf_k,
    )

    names = ("top_k", "candidate_k", "rrf_k")

    for name, value in zip(names, resolved, strict=True):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")

    return resolved


# ============================================================
# Step 3: Load authorized corpus
# ============================================================


def _load_authorized_chunks(
    collection_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Load READY chunks from a collection owned by the requesting user."""

    with get_sessionmaker()() as db:
        # Verify collection ownership before retrieving its contents.
        collection_exists = db.execute(
            select(Collection.id).where(
                Collection.id == collection_id,
                Collection.owner_id == owner_id,
            )
        ).scalar_one_or_none()

        if collection_exists is None:
            raise PermissionError("Collection does not exist or does not belong to this owner.")

        stmt = (
            select(Chunk, Document)
            .join(
                Document,
                Chunk.document_id == Document.id,
            )
            .join(
                Collection,
                Document.collection_id == Collection.id,
            )
            .where(
                Document.collection_id == collection_id,
                Document.owner_id == owner_id,
                Collection.owner_id == owner_id,
                Document.status == DocumentStatus.READY,
            )
            .order_by(Chunk.id)
        )

        rows = db.execute(stmt).all()

        return [
            {
                "chunk_id": str(chunk.id),
                "document_id": str(document.id),
                "filename": document.filename,
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "page": chunk.page,
                "section": chunk.section,
            }
            for chunk, document in rows
        ]


# ============================================================
# Step 4: Dense Retrieval
# ============================================================


def _dense_search(
    question: str,
    collection_id: uuid.UUID,
    owner_id: uuid.UUID,
    candidate_k: int,
) -> list[dict[str, Any]]:
    """Retrieve dense candidates using the ERA-11 baseline."""

    baseline_results = retrieve_top_k(
        question=question,
        collection_id=collection_id,
        owner_id=owner_id,
        top_k=candidate_k,
    )

    results: list[dict[str, Any]] = []

    for item in baseline_results:
        result = {key: value for key, value in item.items() if key not in {"rank", "score"}}

        result["dense_rank"] = item["rank"]
        result["dense_score"] = item["score"]

        results.append(result)

    return results


# ============================================================
# Step 5: BM25 Retrieval
# ============================================================


def _bm25_search(
    chunks: list[dict[str, Any]],
    query: str,
    candidate_k: int,
) -> list[dict[str, Any]]:
    """Retrieve candidates using BM25Okapi."""

    query_tokens = _tokenize(query)

    if not query_tokens or not chunks:
        return []

    # Tokenize all authorized documents.
    tokenized_documents = [_tokenize(chunk["text"]) for chunk in chunks]

    # Exclude documents without searchable tokens.
    valid_documents = [
        (chunk, tokens)
        for chunk, tokens in zip(
            chunks,
            tokenized_documents,
            strict=True,
        )
        if tokens
    ]

    if not valid_documents:
        return []

    valid_chunks, corpus = zip(
        *valid_documents,
        strict=True,
    )

    valid_chunks = list(valid_chunks)
    corpus = list(corpus)

    # Build BM25 index for the authorized corpus.
    bm25 = BM25Okapi(corpus)

    scores = bm25.get_scores(query_tokens)

    # Only keep chunks sharing at least one query token.
    # A non-positive BM25 score does not necessarily mean no match.
    query_token_set = set(query_tokens)

    ranked_indices = [
        index for index, tokens in enumerate(corpus) if query_token_set.intersection(tokens)
    ]

    # Sort by BM25 score descending.
    # Use chunk_id as deterministic tie-breaker.
    ranked_indices.sort(
        key=lambda index: (
            -float(scores[index]),
            valid_chunks[index]["chunk_id"],
        )
    )

    results: list[dict[str, Any]] = []

    for rank, index in enumerate(
        ranked_indices[:candidate_k],
        start=1,
    ):
        results.append(
            {
                **valid_chunks[index],
                "bm25_rank": rank,
                "bm25_score": round(float(scores[index]), 6),
            }
        )

    return results


# ============================================================
# Step 6: Reciprocal Rank Fusion
# ============================================================


def _reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    bm25_results: list[dict[str, Any]],
    rrf_k: int,
) -> list[dict[str, Any]]:
    """Merge Dense and BM25 rankings using Reciprocal Rank Fusion."""

    if isinstance(rrf_k, bool) or not isinstance(rrf_k, int) or rrf_k <= 0:
        raise ValueError("rrf_k must be a positive integer.")

    fused: dict[str, dict[str, Any]] = {}

    rankings = [
        ("dense", dense_results),
        ("bm25", bm25_results),
    ]

    for method, ranking in rankings:
        for rank, result in enumerate(ranking, start=1):
            chunk_id = result["chunk_id"]

            # Create or update the candidate.
            if chunk_id not in fused:
                fused[chunk_id] = dict(result)
                fused[chunk_id]["rrf_score"] = 0.0
            else:
                fused[chunk_id].update(result)

            # RRF contribution = 1 / (k + rank).
            fused[chunk_id]["rrf_score"] += 1.0 / (rrf_k + rank)

            fused[chunk_id][f"{method}_rank"] = rank

    # Sort by fused score descending.
    ranked_results = sorted(
        fused.values(),
        key=lambda item: (
            -item["rrf_score"],
            item["chunk_id"],
        ),
    )

    results: list[dict[str, Any]] = []

    for rank, item in enumerate(ranked_results, start=1):
        results.append(
            {
                **item,
                "rank": rank,
                "rrf_score": round(item["rrf_score"], 6),
            }
        )

    return results


# ============================================================
# Step 7: Hybrid Retrieval service
# ============================================================


def retrieve_hybrid(
    question: str,
    collection_id: uuid.UUID,
    owner_id: uuid.UUID,
    top_k: int | None = None,
    candidate_k: int | None = None,
    rrf_k: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieve evidence using Dense Search + BM25 + RRF."""

    # 1. Validate inputs.
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must not be empty.")

    if not isinstance(collection_id, uuid.UUID):
        raise ValueError("Invalid collection_id.")

    if not isinstance(owner_id, uuid.UUID):
        raise ValueError("Invalid owner_id.")

    # 2. Resolve parameters from Settings or explicit arguments.
    top_k, candidate_k, rrf_k = _resolve_retrieval_params(
        top_k=top_k,
        candidate_k=candidate_k,
        rrf_k=rrf_k,
    )

    question = question.strip()

    # 3. Load the authorized corpus.
    authorized_chunks = _load_authorized_chunks(
        collection_id=collection_id,
        owner_id=owner_id,
    )

    if not authorized_chunks:
        return []

    # 5. Dense Retrieval.
    dense_results = _dense_search(
        question=question,
        collection_id=collection_id,
        owner_id=owner_id,
        candidate_k=candidate_k,
    )

    # 6. BM25 Retrieval.
    bm25_results = _bm25_search(
        chunks=authorized_chunks,
        query=question,
        candidate_k=candidate_k,
    )

    # 7. Merge both rankings using RRF.
    fused_results = _reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        rrf_k=rrf_k,
    )

    # 8. Return final Top-K.
    return fused_results[:top_k]
