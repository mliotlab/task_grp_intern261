"""Build or inspect the policy index: python -m scripts.ingest_kb [--dry-run]."""

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
    if args.dry_run:
        docs = load_documents(settings.kb_dir)
        total = 0
        for doc in docs:
            count = len(chunk_text(doc, params["chunk_size"], params["chunk_overlap"]))
            total += count
            print(f"{doc.doc_id:<40} {count:>3} chunks")
        print(f"{len(docs)} documents, {total} chunks")
        return
    count = build_index(
        settings.kb_dir,
        settings.vector_store_dir,
        settings.embedding_model,
        embedding_revision=settings.embedding_revision or None,
        chunk_size=params["chunk_size"],
        overlap=params["chunk_overlap"],
    )
    print(f"Indexed {count} chunks into {settings.vector_store_dir}")


if __name__ == "__main__":
    main()
