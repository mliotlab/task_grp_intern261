from __future__ import annotations

from pathlib import Path

import pytest

from support_agent.retrieval import SourceDocument, chunk_text, load_documents


def test_load_documents_skips_readme(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("index")
    (tmp_path / "return-policy.md").write_text("# Returns\n30 days.")
    docs = load_documents(tmp_path)
    assert [d.doc_id for d in docs] == ["return-policy"]


def test_chunking_covers_text_with_overlap() -> None:
    doc = SourceDocument("d", Path("d.md"), "x" * 2000)
    chunks = chunk_text(doc, chunk_size=800, overlap=100)
    assert len(chunks) == 3
    assert all(len(c.text) <= 800 for c in chunks)
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_chunking_rejects_bad_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_text(SourceDocument("d", Path("d.md"), "abc"), chunk_size=10, overlap=10)


def test_repository_kb_is_loadable() -> None:
    docs = load_documents(Path("kb"))
    assert any(d.doc_id == "shipping-policy" for d in docs)
