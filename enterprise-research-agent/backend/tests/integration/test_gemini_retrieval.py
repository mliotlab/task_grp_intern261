from __future__ import annotations

import os

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.gemini]


def test_live_gemini_embedding_and_pgvector_retrieval(
    seeded_gemini_retrieval_data, retrieval_module
):
    """Call Gemini to embed a question, then retrieve the seeded chunk via pgvector.

    Enable explicitly with ERA_RUN_GEMINI_TESTS=1. The fixture creates and removes
    its own database rows, so no pre-existing collection/owner UUIDs are required.
    """
    if os.getenv("ERA_RUN_GEMINI_TESTS") != "1":
        pytest.skip("Set ERA_RUN_GEMINI_TESTS=1 to enable live Gemini tests")

    data = seeded_gemini_retrieval_data
    results = retrieval_module.retrieve_top_k(
        question="What are the main objectives of this research?",
        collection_id=data["collection_id"],
        owner_id=data["owner_id"],
        top_k=3,
    )

    assert len(results) == 1
    result = results[0]
    assert result["filename"] == data["filename"]
    assert result["document_id"] == str(data["document_id"])
    assert result["chunk_id"] == str(data["chunk_id"])
    assert result["text"] == data["text"]
    assert result["page"] == 1
    assert result["section"] == "Research objectives"
    assert isinstance(result["score"], float)
