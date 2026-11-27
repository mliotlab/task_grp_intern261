from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeRowsResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, result):
        self.result = result
        self.executed_statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement):
        self.executed_statements.append(statement)
        return self.result


def install_session_factory(monkeypatch, retrieval_module, sessions):
    sessions_iter = iter(sessions)
    monkeypatch.setattr(
        retrieval_module,
        "get_sessionmaker",
        lambda: lambda: next(sessions_iter),
    )


def make_row(*, filename="sample.pdf", page=2, section="Methods", distance=0.1):
    chunk = SimpleNamespace(
        id=uuid.uuid4(),
        ordinal=0,
        text="A representative document chunk.",
        page=page,
        section=section,
    )
    document = SimpleNamespace(
        id=uuid.uuid4(),
        filename=filename,
    )
    return chunk, document, distance


@pytest.mark.parametrize("question", ["", "   ", None])
def test_retrieve_top_k_rejects_empty_question(retrieval_module, question):
    with pytest.raises(ValueError, match="Question must not be empty"):
        retrieval_module.retrieve_top_k(
            question=question,
            collection_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
        )


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5])
def test_retrieve_top_k_rejects_invalid_top_k(retrieval_module, top_k):
    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        retrieval_module.retrieve_top_k(
            question="What is this document about?",
            collection_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            top_k=top_k,
        )


def test_retrieve_top_k_rejects_invalid_collection_id(retrieval_module):
    with pytest.raises(ValueError, match="Invalid collection_id"):
        retrieval_module.retrieve_top_k(
            question="question",
            collection_id="not-a-uuid",
            owner_id=uuid.uuid4(),
        )


def test_retrieve_top_k_rejects_invalid_owner_id(retrieval_module):
    with pytest.raises(ValueError, match="Invalid owner_id"):
        retrieval_module.retrieve_top_k(
            question="question",
            collection_id=uuid.uuid4(),
            owner_id="not-a-uuid",
        )


def test_retrieve_top_k_rejects_unowned_collection_before_embedding(retrieval_module, monkeypatch):
    collection_session = FakeSession(FakeScalarResult(None))
    install_session_factory(monkeypatch, retrieval_module, [collection_session])

    def mock_embedding(_texts):
        pytest.fail("Embedding must not run for an unowned collection")

    monkeypatch.setattr(retrieval_module, "embed_query", mock_embedding)

    with pytest.raises(PermissionError, match="does not belong to this owner"):
        retrieval_module.retrieve_top_k(
            question="question",
            collection_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
        )


def test_retrieve_top_k_rejects_query_embedding_dimension_mismatch(retrieval_module, monkeypatch):
    collection_session = FakeSession(FakeScalarResult(uuid.uuid4()))
    install_session_factory(monkeypatch, retrieval_module, [collection_session])
    monkeypatch.setattr(
        retrieval_module,
        "embed_query",
        lambda texts: [[0.0] * (retrieval_module.EMBEDDING_DIM - 1)],
    )

    with pytest.raises(RuntimeError, match=r"Expected .* dimensions"):
        retrieval_module.retrieve_top_k(
            question="question",
            collection_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
        )


def test_retrieve_top_k_returns_ranked_chunks_and_metadata(retrieval_module, monkeypatch):
    collection_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    row_1 = make_row(filename="paper.pdf", page=3, section="Introduction", distance=0.1)
    row_2 = make_row(filename="paper.pdf", page=5, section="Results", distance=0.25)

    collection_session = FakeSession(FakeScalarResult(collection_id))
    retrieval_session = FakeSession(FakeRowsResult([row_1, row_2]))
    install_session_factory(
        monkeypatch,
        retrieval_module,
        [collection_session, retrieval_session],
    )
    monkeypatch.setattr(
        retrieval_module,
        "embed_query",
        lambda texts: [[0.0] * retrieval_module.EMBEDDING_DIM],
    )

    results = retrieval_module.retrieve_top_k(
        question="What does the paper conclude?",
        collection_id=collection_id,
        owner_id=owner_id,
        top_k=2,
    )

    assert len(results) == 2
    assert results[0]["rank"] == 1
    assert results[0]["filename"] == "paper.pdf"
    assert results[0]["page"] == 3
    assert results[0]["section"] == "Introduction"
    assert results[0]["score"] == pytest.approx(0.9)
    assert results[1]["rank"] == 2
    assert results[1]["score"] == pytest.approx(0.75)


def test_load_questions_reads_jsonl_and_skips_blank_lines(retrieval_module, tmp_path):
    dataset = tmp_path / "questions.jsonl"
    records = [
        {
            "id": "q1",
            "question": "What is the topic?",
            "key_points": ["topic"],
            "source_documents": ["paper.pdf"],
        },
        {
            "id": "q2",
            "question": "What is the conclusion?",
            "key_points": [],
            "source_documents": [],
        },
    ]
    dataset.write_text(
        json.dumps(records[0]) + "\n\n" + json.dumps(records[1]) + "\n",
        encoding="utf-8",
    )

    questions = retrieval_module.load_questions(dataset)

    assert len(questions) == 2
    assert questions[0]["id"] == "q1"
    assert questions[0]["source_documents"] == ["paper.pdf"]
    assert questions[1]["id"] == "q2"


def test_load_questions_raises_for_missing_file(retrieval_module, tmp_path):
    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        retrieval_module.load_questions(tmp_path / "missing.jsonl")


def test_load_questions_raises_for_invalid_json(retrieval_module, tmp_path):
    dataset = tmp_path / "invalid.jsonl"
    dataset.write_text('{"id": "q1"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON at line 1"):
        retrieval_module.load_questions(dataset)


def test_load_questions_raises_for_non_object_record(retrieval_module, tmp_path):
    dataset = tmp_path / "array.jsonl"
    dataset.write_text('["not", "an", "object"]\n', encoding="utf-8")

    with pytest.raises(ValueError, match="must be an object"):
        retrieval_module.load_questions(dataset)


def test_load_questions_requires_valid_id_and_question(retrieval_module, tmp_path):
    dataset = tmp_path / "missing-fields.jsonl"
    dataset.write_text(json.dumps({"id": "q1", "question": " "}), encoding="utf-8")

    with pytest.raises(ValueError, match="Missing or invalid question"):
        retrieval_module.load_questions(dataset)


def test_load_questions_validates_source_documents(retrieval_module, tmp_path):
    dataset = tmp_path / "invalid-sources.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "q1",
                "question": "Question?",
                "key_points": [],
                "source_documents": ["paper.pdf", 123],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must contain strings"):
        retrieval_module.load_questions(dataset)


def test_load_questions_rejects_empty_dataset(retrieval_module, tmp_path):
    dataset = tmp_path / "empty.jsonl"
    dataset.write_text("\n  \n", encoding="utf-8")

    with pytest.raises(ValueError, match="contains no questions"):
        retrieval_module.load_questions(dataset)


def test_run_dataset_calculates_source_hit_rate(retrieval_module, monkeypatch):
    questions = [
        {
            "id": "q1",
            "question": "Question one?",
            "key_points": ["point"],
            "source_documents": ["/data/Paper-A.pdf"],
        },
        {
            "id": "q2",
            "question": "Question two?",
            "key_points": [],
            "source_documents": ["paper-b.pdf"],
        },
    ]
    retrieval_results = [
        {"filename": "paper-a.PDF", "text": "chunk A"},
        {"filename": "different.pdf", "text": "chunk X"},
    ]
    calls = iter(retrieval_results)
    monkeypatch.setattr(
        retrieval_module,
        "retrieve_top_k",
        lambda **kwargs: [next(calls)],
    )

    output = retrieval_module.run_dataset(
        questions=questions,
        collection_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        top_k=5,
    )

    assert output["metrics"]["total_questions"] == 2
    assert output["metrics"]["source_hit_count"] == 1
    assert output["metrics"]["source_hit_rate"] == 0.5
    assert output["questions"][0]["source_hit"] is True
    assert output["questions"][1]["source_hit"] is False
