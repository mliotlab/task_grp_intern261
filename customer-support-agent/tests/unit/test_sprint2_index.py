from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from support_agent.config import Settings
from support_agent.llm import LLMResponse, MockLLM
from support_agent.retrieval.ingest import build_index, chunk_text, load_documents
from support_agent.retrieval.retriever import VectorRetriever


class TinyEmbedder:
    def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        return [[1.0, 0.0] if "refund" in text.lower() else [0.0, 2.0] for text in texts]


class FailingEmbedder(TinyEmbedder):
    def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        raise RuntimeError("embedder unavailable")


def test_index_refresh_removes_old_chunks_and_keeps_old_index_on_error(tmp_path: Path) -> None:
    pytest.importorskip("numpy")
    kb = tmp_path / "kb"
    kb.mkdir()
    refund = kb / "refund.md"
    policy = kb / "shipping.md"
    refund.write_text("## Refund timeline\nFive days.", encoding="utf-8")
    policy.write_text("## Shipping\nFree shipping.", encoding="utf-8")
    out = tmp_path / "index"
    embedder = TinyEmbedder()

    def rebuild() -> int:
        return build_index(kb, out, "tiny", embedder=embedder)

    assert rebuild() == rebuild() == 2
    old = VectorRetriever(out, "tiny", embedder=embedder)
    found = old.search("refund", top_k=1)[0]
    assert found.doc_id == "refund" and found.score == pytest.approx(1)
    assert "Five days" in found.text and found.chunk_id
    with pytest.raises(ValueError, match="rebuild"):
        VectorRetriever(out, "other", embedder=embedder)

    refund.write_text("## Refund timeline\nTen days.", encoding="utf-8")
    policy.unlink()
    with pytest.raises(RuntimeError, match="embedder unavailable"):
        build_index(kb, out, "tiny", embedder=FailingEmbedder())
    still_published = VectorRetriever(out, "tiny", embedder=embedder)
    assert still_published.search("refund")[0] == found

    assert rebuild() == 1
    latest = VectorRetriever(out, "tiny", embedder=embedder)
    (updated,) = latest.search("refund", top_k=4)
    assert "Ten days" in updated.text and updated.chunk_id != found.chunk_id
    assert old.search("refund", top_k=1)[0] == found
    refund.unlink()
    assert rebuild() == 0
    assert VectorRetriever(out, "tiny").search("refund") == []


def test_pdf_ingestion_uses_page_metadata(tmp_path: Path) -> None:
    pdf = pytest.importorskip("pypdf")
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = pdf.PdfWriter()
    writer.add_blank_page(300, 300)
    page = writer.add_blank_page(300, 300)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 40 Td (Refund within 5 days) Tj ET")
    page.replace_contents(stream)
    path = tmp_path / "policy.pdf"
    with path.open("wb") as target:
        writer.write(target)
    (doc,) = load_documents(tmp_path)
    (chunk,) = chunk_text(doc)
    assert chunk.metadata["page"] == "2"
    assert "Refund within 5 days" in chunk.text


def test_markdown_headings_and_duplicate_document_ids(tmp_path: Path) -> None:
    (tmp_path / "rules.md").write_text(
        "## Returns\nSeven days.\n## Refunds\nTen days.\n", encoding="utf-8"
    )
    (doc,) = load_documents(tmp_path)
    chunks = chunk_text(doc)
    assert [chunk.metadata["section"] for chunk in chunks] == ["Returns", "Refunds"]
    assert all(chunk.metadata["source"] == "rules.md" for chunk in chunks)
    subdir = tmp_path / "other"
    subdir.mkdir()
    (subdir / "rules.md").write_text("Other policy", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate document ID"):
        load_documents(tmp_path)


def test_chat_uses_the_published_policy_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("numpy")
    from services.chat_api import main as api

    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "refund.md").write_text("## Refund\nRefunds take five days.", encoding="utf-8")
    index_dir = tmp_path / "index"
    embedder = TinyEmbedder()
    build_index(kb, index_dir, "tiny", embedder=embedder)

    settings = Settings(vector_store_dir=index_dir, embedding_model="tiny", prompt_version="v2")
    llm = MockLLM(
        [
            LLMResponse(
                '{"answer":"Refunds take five days.",'
                '"evidence":[{"source":"S1","quote":"Refunds take five days."}]}'
            )
        ]
    )
    monkeypatch.setattr(api, "get_settings", lambda: settings)
    monkeypatch.setattr(api, "create_llm", lambda settings: llm)
    monkeypatch.setattr(
        api,
        "VectorRetriever",
        lambda path, model, **kwargs: VectorRetriever(path, model, embedder=embedder, **kwargs),
    )
    api.get_orchestrator.cache_clear()
    try:
        with TestClient(api.create_app()) as client:
            response = client.post(
                "/v1/chat", json={"session_id": "index-test", "message": "How long is the refund?"}
            )
        assert response.status_code == 200
        (citation,) = response.json()["citations"]
        assert citation["doc_id"] == "refund"
        assert citation["snippet"] == "Refunds take five days."
    finally:
        api.get_orchestrator.cache_clear()
