"""Chunk and index the knowledge base (FR-02).

python scripts/ingest_kb.py            # build / refresh the vector store
python scripts/ingest_kb.py --dry-run  # only show how documents are chunked
"""

from __future__ import annotations

import argparse

from support_agent.config import get_settings
from support_agent.retrieval.ingest import build_index, chunk_text, load_documents


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    params = settings.agent_params()["retrieval"]
    docs = load_documents(settings.kb_dir)
    total = 0
    for doc in docs:
        chunks = chunk_text(doc, params["chunk_size"], params["chunk_overlap"])
        total += len(chunks)
        print(f"{doc.doc_id:<40} {len(chunks):>3} chunks")
    print(f"{len(docs)} documents, {total} chunks")

    if not args.dry_run:
        n = build_index(settings.kb_dir, settings.vector_store_dir, settings.embedding_model)
        print(f"Indexed {n} chunks into {settings.vector_store_dir}")


if __name__ == "__main__":
    main()
