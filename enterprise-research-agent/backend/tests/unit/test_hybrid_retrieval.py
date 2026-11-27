"""Unit tests for ERA-39 Hybrid Retrieval."""

import uuid
from types import SimpleNamespace

import pytest

from workers.research import hybrid_retrieval as retrieval

# ============================================================
# Helpers
# ============================================================


def make_chunk(
    chunk_id: str,
    text: str,
) -> dict:
    """Create a minimal chunk fixture for retrieval tests."""

    return {
        "chunk_id": chunk_id,
        "document_id": f"doc-{chunk_id}",
        "filename": "test.pdf",
        "ordinal": 0,
        "text": text,
        "page": 1,
        "section": None,
    }


def mock_settings(
    monkeypatch,
    top_k: int = 5,
    candidate_k: int = 20,
    rrf_k: int = 60,
) -> None:
    """Provide retrieval settings without reading the real environment."""

    settings = SimpleNamespace(
        retrieval_top_k=top_k,
        retrieval_candidate_k=candidate_k,
        retrieval_rrf_k=rrf_k,
    )

    monkeypatch.setattr(
        retrieval,
        "get_settings",
        lambda: settings,
    )


# ============================================================
# Tokenization tests
# ============================================================


def test_tokenize_normalizes_case():
    assert retrieval._tokenize("NIST Security Controls") == [
        "nist",
        "security",
        "controls",
    ]


def test_tokenize_preserves_technical_terms():
    assert retrieval._tokenize("SP 800-53, CVE-2024-1234, MFA!") == [
        "sp",
        "800-53",
        "cve-2024-1234",
        "mfa",
    ]


def test_tokenize_preserves_vietnamese_unicode():
    assert retrieval._tokenize("Kiểm soát truy cập") == [
        "kiểm",
        "soát",
        "truy",
        "cập",
    ]


def test_tokenize_empty_string():
    assert retrieval._tokenize("") == []


def test_tokenize_rejects_non_string():
    with pytest.raises(TypeError, match="Text must be a string"):
        retrieval._tokenize(None)


# ============================================================
# Configuration tests
# ============================================================


def test_resolve_retrieval_params_uses_settings(monkeypatch):
    mock_settings(
        monkeypatch,
        top_k=5,
        candidate_k=20,
        rrf_k=60,
    )

    assert retrieval._resolve_retrieval_params() == (5, 20, 60)


def test_resolve_retrieval_params_supports_overrides(monkeypatch):
    mock_settings(
        monkeypatch,
        top_k=5,
        candidate_k=20,
        rrf_k=60,
    )

    assert retrieval._resolve_retrieval_params(
        top_k=10,
        candidate_k=50,
        rrf_k=30,
    ) == (10, 50, 30)


@pytest.mark.parametrize(
    ("kwargs", "invalid_value"),
    [
        ({"top_k": 0}, "top_k"),
        ({"candidate_k": -1}, "candidate_k"),
        ({"rrf_k": 0}, "rrf_k"),
        ({"top_k": True}, "top_k"),
    ],
)
def test_resolve_retrieval_params_rejects_invalid_values(
    monkeypatch,
    kwargs,
    invalid_value,
):
    mock_settings(monkeypatch)

    with pytest.raises(ValueError, match=invalid_value):
        retrieval._resolve_retrieval_params(**kwargs)


# ============================================================
# BM25 tests
# ============================================================


def test_bm25_search_returns_only_matching_chunks():
    chunks = [
        make_chunk(
            "chunk-1",
            "Zero trust architecture zero trust policy",
        ),
        make_chunk(
            "chunk-2",
            "Zero trust network security",
        ),
        make_chunk(
            "chunk-3",
            "Multi factor authentication",
        ),
        make_chunk(
            "chunk-4",
            "Firewall monitoring and logging",
        ),
        make_chunk(
            "chunk-5",
            "Incident response and recovery",
        ),
    ]

    results = retrieval._bm25_search(
        chunks=chunks,
        query="zero trust",
        candidate_k=5,
    )

    result_ids = {result["chunk_id"] for result in results}

    assert result_ids == {"chunk-1", "chunk-2"}


def test_bm25_search_respects_candidate_k():
    chunks = [
        make_chunk("chunk-1", "MFA authentication access"),
        make_chunk("chunk-2", "MFA authentication security"),
        make_chunk("chunk-3", "MFA authentication controls"),
        make_chunk("chunk-4", "Firewall network monitoring"),
        make_chunk("chunk-5", "Incident response recovery"),
    ]

    results = retrieval._bm25_search(
        chunks=chunks,
        query="MFA authentication",
        candidate_k=1,
    )

    assert len(results) <= 1


def test_bm25_search_returns_empty_for_no_matching_tokens():
    chunks = [
        make_chunk("chunk-1", "Firewall network monitoring"),
        make_chunk("chunk-2", "Incident response recovery"),
    ]

    results = retrieval._bm25_search(
        chunks=chunks,
        query="multifactor authentication",
        candidate_k=5,
    )

    assert results == []


def test_bm25_search_handles_empty_corpus():
    results = retrieval._bm25_search(
        chunks=[],
        query="MFA authentication",
        candidate_k=5,
    )

    assert results == []


# ============================================================
# Dense Retrieval reuse tests
# ============================================================


def test_dense_search_reuses_era11_baseline(monkeypatch):
    collection_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    baseline_results = [
        {
            "rank": 1,
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "filename": "nist.pdf",
            "text": "MFA is required.",
            "page": 10,
            "score": 0.91,
        },
        {
            "rank": 2,
            "chunk_id": "chunk-2",
            "document_id": "doc-2",
            "filename": "security.pdf",
            "text": "Access control policy.",
            "page": 20,
            "score": 0.85,
        },
    ]

    calls = {}

    def fake_retrieve_top_k(**kwargs):
        calls.update(kwargs)
        return baseline_results

    monkeypatch.setattr(
        retrieval,
        "retrieve_top_k",
        fake_retrieve_top_k,
    )

    results = retrieval._dense_search(
        question="What is MFA?",
        collection_id=collection_id,
        owner_id=owner_id,
        candidate_k=2,
    )

    assert calls == {
        "question": "What is MFA?",
        "collection_id": collection_id,
        "owner_id": owner_id,
        "top_k": 2,
    }

    assert len(results) == 2
    assert results[0]["dense_rank"] == 1
    assert results[0]["dense_score"] == 0.91
    assert results[1]["dense_rank"] == 2

    assert "rank" not in results[0]
    assert "score" not in results[0]


# ============================================================
# RRF tests
# ============================================================


def test_rrf_merges_dense_and_bm25_rankings():
    dense_results = [
        {"chunk_id": "A", "dense_rank": 1},
        {"chunk_id": "B", "dense_rank": 2},
        {"chunk_id": "C", "dense_rank": 3},
    ]

    bm25_results = [
        {"chunk_id": "B", "bm25_rank": 1},
        {"chunk_id": "D", "bm25_rank": 2},
        {"chunk_id": "A", "bm25_rank": 3},
    ]

    results = retrieval._reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        rrf_k=60,
    )

    # B is ranked highly by both methods.
    assert results[0]["chunk_id"] == "B"

    # A appears in both rankings and must be deduplicated.
    chunk_ids = [result["chunk_id"] for result in results]

    assert len(chunk_ids) == len(set(chunk_ids))
    assert set(chunk_ids) == {"A", "B", "C", "D"}


def test_rrf_calculates_fused_score_correctly():
    dense_results = [
        {"chunk_id": "A"},
    ]

    bm25_results = [
        {"chunk_id": "A"},
    ]

    results = retrieval._reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        rrf_k=60,
    )

    expected_score = (1 / 61) + (1 / 61)

    assert results[0]["rrf_score"] == pytest.approx(
        expected_score,
        abs=1e-6,
    )


def test_rrf_preserves_ranks_from_both_methods():
    dense_results = [
        {"chunk_id": "A", "dense_rank": 1},
    ]

    bm25_results = [
        {"chunk_id": "A", "bm25_rank": 2},
    ]

    results = retrieval._reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        rrf_k=60,
    )

    assert results[0]["dense_rank"] == 1
    assert results[0]["bm25_rank"] == 1


def test_rrf_handles_empty_results():
    assert (
        retrieval._reciprocal_rank_fusion(
            dense_results=[],
            bm25_results=[],
            rrf_k=60,
        )
        == []
    )


def test_rrf_rejects_invalid_constant():
    with pytest.raises(ValueError, match="rrf_k"):
        retrieval._reciprocal_rank_fusion(
            dense_results=[],
            bm25_results=[],
            rrf_k=0,
        )


# ============================================================
# Hybrid Retrieval integration tests
# ============================================================


def test_retrieve_hybrid_combines_dense_and_bm25(monkeypatch):
    collection_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    mock_settings(monkeypatch)

    chunks = [
        make_chunk("A", "MFA authentication"),
        make_chunk("B", "Access control"),
    ]

    dense_results = [
        {
            "chunk_id": "A",
            "dense_rank": 1,
            "dense_score": 0.9,
        },
        {
            "chunk_id": "B",
            "dense_rank": 2,
            "dense_score": 0.8,
        },
    ]

    bm25_results = [
        {
            "chunk_id": "B",
            "bm25_rank": 1,
            "bm25_score": 4.5,
        },
        {
            "chunk_id": "C",
            "bm25_rank": 2,
            "bm25_score": 2.5,
        },
    ]

    monkeypatch.setattr(
        retrieval,
        "_load_authorized_chunks",
        lambda **kwargs: chunks,
    )

    monkeypatch.setattr(
        retrieval,
        "_dense_search",
        lambda **kwargs: dense_results,
    )

    monkeypatch.setattr(
        retrieval,
        "_bm25_search",
        lambda **kwargs: bm25_results,
    )

    results = retrieval.retrieve_hybrid(
        question="What is access control?",
        collection_id=collection_id,
        owner_id=owner_id,
    )

    assert len(results) == 3

    # B receives a contribution from both methods.
    assert results[0]["chunk_id"] == "B"

    # Final results must be sorted by RRF score.
    scores = [result["rrf_score"] for result in results]

    assert scores == sorted(scores, reverse=True)


def test_retrieve_hybrid_returns_empty_for_empty_corpus(monkeypatch):
    collection_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    mock_settings(monkeypatch)

    monkeypatch.setattr(
        retrieval,
        "_load_authorized_chunks",
        lambda **kwargs: [],
    )

    def unexpected_call(**kwargs):
        raise AssertionError("Search should not run for an empty corpus.")

    monkeypatch.setattr(
        retrieval,
        "_dense_search",
        unexpected_call,
    )

    monkeypatch.setattr(
        retrieval,
        "_bm25_search",
        unexpected_call,
    )

    results = retrieval.retrieve_hybrid(
        question="What is MFA?",
        collection_id=collection_id,
        owner_id=owner_id,
    )

    assert results == []


def test_retrieve_hybrid_propagates_authorization_error(monkeypatch):
    collection_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    mock_settings(monkeypatch)

    def unauthorized_collection(**kwargs):
        raise PermissionError("Access denied.")

    monkeypatch.setattr(
        retrieval,
        "_load_authorized_chunks",
        unauthorized_collection,
    )

    with pytest.raises(PermissionError, match="Access denied"):
        retrieval.retrieve_hybrid(
            question="What is MFA?",
            collection_id=collection_id,
            owner_id=owner_id,
        )
