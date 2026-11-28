"""Basic RAG retrieval: load questions → embed → Top-K search → evaluate."""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models.collection import Collection
from app.models.document import (
    EMBEDDING_DIM,
    Chunk,
    Document,
    DocumentStatus,
)
from workers.embedding import embed_query

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5


# ============================================================
# Step 1: Load evaluation dataset
# ============================================================


def load_questions(dataset_path: Path) -> list[dict[str, Any]]:
    """Load and validate questions from a JSONL dataset."""

    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    questions: list[dict[str, Any]] = []

    with dataset_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_number}: {exc}") from exc

            if not isinstance(record, dict):
                raise ValueError(f"Record at line {line_number} must be an object.")

            question_id = record.get("id")
            question = record.get("question")

            if not isinstance(question_id, str) or not question_id.strip():
                raise ValueError(f"Missing or invalid id at line {line_number}.")

            if not isinstance(question, str) or not question.strip():
                raise ValueError(f"Missing or invalid question at line {line_number}.")

            key_points = record.get("key_points", [])
            source_documents = record.get("source_documents", [])

            if not isinstance(key_points, list):
                raise ValueError(f"key_points must be a list at line {line_number}.")

            if not isinstance(source_documents, list):
                raise ValueError(f"source_documents must be a list at line {line_number}.")

            if not all(isinstance(item, str) for item in source_documents):
                raise ValueError(f"source_documents must contain strings at line {line_number}.")

            questions.append(
                {
                    "id": question_id.strip(),
                    "question": question.strip(),
                    "key_points": key_points,
                    "source_documents": source_documents,
                }
            )

    if not questions:
        raise ValueError("Dataset contains no questions.")

    return questions


# ============================================================
# Step 2: Top-K retrieval
# ============================================================


def retrieve_top_k(
    question: str,
    collection_id: uuid.UUID,
    owner_id: uuid.UUID,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    """Retrieve the most relevant chunks for one question."""

    # 1. Validate input
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must not be empty.")

    if not isinstance(collection_id, uuid.UUID):
        raise ValueError("Invalid collection_id.")

    if not isinstance(owner_id, uuid.UUID):
        raise ValueError("Invalid owner_id.")

    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")

    # 2. Verify collection ownership before calling embedding API
    with get_sessionmaker()() as db:
        collection_exists = db.execute(
            select(Collection.id).where(
                Collection.id == collection_id,
                Collection.owner_id == owner_id,
            )
        ).scalar_one_or_none()

        if collection_exists is None:
            raise PermissionError("Collection does not exist or does not belong to this owner.")

    # 3. Embed the query using the same embedding model
    query_vector = embed_query(question.strip())

    if len(query_vector) != EMBEDDING_DIM:
        raise RuntimeError(f"Expected {EMBEDDING_DIM} dimensions, got {len(query_vector)}.")

    # 4. Calculate cosine distance
    distance = Chunk.embedding.cosine_distance(query_vector)

    stmt = (
        select(Chunk, Document, distance)
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
        .order_by(distance.asc())
        .limit(top_k)
    )

    # 5. Execute similarity search
    with get_sessionmaker()() as db:
        rows = db.execute(stmt).all()

    # 6. Convert database records to retrieval output
    results: list[dict[str, Any]] = []

    for rank, (chunk, document, cosine_distance) in enumerate(
        rows,
        start=1,
    ):
        results.append(
            {
                "rank": rank,
                "chunk_id": str(chunk.id),
                "document_id": str(document.id),
                "filename": document.filename,
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "page": chunk.page,
                "section": chunk.section,
                "score": round(
                    1.0 - float(cosine_distance),
                    6,
                ),
            }
        )

    return results


# ============================================================
# Step 3: Process evaluation dataset
# ============================================================


def _normalize_filename(filename: str) -> str:
    """Normalize a source path for filename comparison."""

    return Path(filename).name.casefold()


def run_dataset(
    questions: list[dict[str, Any]],
    collection_id: uuid.UUID,
    owner_id: uuid.UUID,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:
    """Run Top-K retrieval for every question in the dataset."""

    question_results: list[dict[str, Any]] = []

    for index, item in enumerate(questions, start=1):
        question_id = item["id"]
        question = item["question"]
        expected_sources = item["source_documents"]

        logger.info(
            "Retrieving question %s (%d/%d)",
            question_id,
            index,
            len(questions),
        )

        # Retrieve chunks using the question only.
        results = retrieve_top_k(
            question=question,
            collection_id=collection_id,
            owner_id=owner_id,
            top_k=top_k,
        )

        # Compare retrieved filenames with expected source documents.
        expected_filenames = {_normalize_filename(source) for source in expected_sources}

        retrieved_filenames = {_normalize_filename(result["filename"]) for result in results}

        matched_sources = sorted(expected_filenames & retrieved_filenames)

        source_hit = bool(matched_sources)

        question_results.append(
            {
                "question_id": question_id,
                "question": question,
                "top_k": top_k,
                "results": results,
                "expected_source_documents": expected_sources,
                "matched_source_documents": matched_sources,
                "source_hit": source_hit,
                # Retained for later answer-quality evaluation.
                # These key points are NOT used in retrieval.
                "key_points": item["key_points"],
            }
        )

        logger.info(
            "Question %s: retrieved %d chunks, source_hit=%s",
            question_id,
            len(results),
            source_hit,
        )

    # 4. Calculate source-document Hit@K
    hit_count = sum(result["source_hit"] for result in question_results)

    total_questions = len(question_results)

    metrics = {
        "total_questions": total_questions,
        "top_k": top_k,
        "source_hit_count": hit_count,
        "source_hit_rate": (round(hit_count / total_questions, 4) if total_questions else 0.0),
    }

    return {
        "metrics": metrics,
        "questions": question_results,
    }


# ============================================================
# Step 4: CLI
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Run basic Top-K retrieval evaluation.")

    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("/app/eval/datasets/v0/questions.jsonl"),
    )

    parser.add_argument(
        "--collection-id",
        required=True,
    )

    parser.add_argument(
        "--owner-id",
        required=True,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/app/eval/reports/retrieval_results.json"),
    )

    args = parser.parse_args()

    try:
        collection_id = uuid.UUID(args.collection_id)
        owner_id = uuid.UUID(args.owner_id)
    except ValueError as exc:
        parser.error(f"Invalid UUID: {exc}")

    # Load dataset
    questions = load_questions(args.dataset)

    print(f"Loaded {len(questions)} questions.")
    print(f"Top-K: {args.top_k}")

    # Run retrieval
    output = run_dataset(
        questions=questions,
        collection_id=collection_id,
        owner_id=owner_id,
        top_k=args.top_k,
    )

    # Save output
    args.out.parent.mkdir(parents=True, exist_ok=True)

    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Print summary
    print("\nRetrieval evaluation completed.")
    print(json.dumps(output["metrics"], indent=2))
    print(f"\nResults saved to: {args.out}")

    for question_result in output["questions"]:
        print(f"\n[{question_result['question_id']}]")
        print(question_result["question"])
        print(
            "Source hit:",
            question_result["source_hit"],
        )

        for result in question_result["results"]:
            print(
                f"  #{result['rank']} "
                f"{result['filename']} "
                f"page={result['page']} "
                f"score={result['score']:.4f}"
            )


if __name__ == "__main__":
    main()
