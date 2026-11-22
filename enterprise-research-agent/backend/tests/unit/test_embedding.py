from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from workers import embedding as embedding_module


class FakeEmbeddingModels:
    def __init__(self, *, dimension: int, return_count: int | None = None):
        self.dimension = dimension
        self.return_count = return_count
        self.batch_sizes: list[int] = []

    def embed_content(self, *, model, contents, config):
        self.batch_sizes.append(len(contents))
        count = len(contents) if self.return_count is None else self.return_count
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[float(i) for i in range(self.dimension)])
                for _ in range(count)
            ]
        )


class FakeAPIError(Exception):
    def __init__(self, code: int):
        super().__init__(f"fake API error {code}")
        self.code = code


def configure_embedding(monkeypatch, *, dimension=3, api_key="test-key"):
    settings = SimpleNamespace(
        gemini_api_key=SecretStr(api_key) if api_key is not None else None,
        embedding_model="test-embedding-model",
        embedding_dim=dimension,
    )
    monkeypatch.setattr(embedding_module, "get_settings", lambda: settings)
    monkeypatch.setattr(embedding_module, "_reserve_embedding_quota", lambda count: None)
    return settings


def install_fake_client(monkeypatch, fake_models):
    fake_client = SimpleNamespace(models=fake_models)
    monkeypatch.setattr(
        embedding_module.genai,
        "Client",
        lambda **kwargs: fake_client,
    )
    return fake_client


def test_embed_chunks_returns_empty_list_without_calling_gemini(monkeypatch):
    configure_embedding(monkeypatch)
    monkeypatch.setattr(
        embedding_module.genai,
        "Client",
        lambda **kwargs: pytest.fail("Gemini client must not be created for empty input"),
    )

    assert embedding_module.embed_chunks([]) == []


def test_embed_chunks_batches_inputs_and_preserves_order(monkeypatch):
    configure_embedding(monkeypatch, dimension=3)
    fake_models = FakeEmbeddingModels(dimension=3)
    install_fake_client(monkeypatch, fake_models)

    vectors = embedding_module.embed_chunks([f"text-{i}" for i in range(33)])

    assert len(vectors) == 33
    assert all(len(vector) == 3 for vector in vectors)
    assert fake_models.batch_sizes == [32, 1]


def test_embed_chunks_requires_api_key(monkeypatch):
    configure_embedding(monkeypatch, api_key=None)
    monkeypatch.setattr(
        embedding_module.genai,
        "Client",
        lambda **kwargs: pytest.fail("Gemini client must not be created without an API key"),
    )

    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        embedding_module.embed_chunks(["hello"])


def test_embed_chunks_rejects_embedding_count_mismatch(monkeypatch):
    configure_embedding(monkeypatch, dimension=3)
    fake_models = FakeEmbeddingModels(dimension=3, return_count=0)
    install_fake_client(monkeypatch, fake_models)

    with pytest.raises(RuntimeError, match="Chunk and embedding counts do not match"):
        embedding_module.embed_chunks(["hello"])


def test_embed_chunks_rejects_wrong_embedding_dimension(monkeypatch):
    configure_embedding(monkeypatch, dimension=4)
    fake_models = FakeEmbeddingModels(dimension=3)
    install_fake_client(monkeypatch, fake_models)

    with pytest.raises(RuntimeError, match="Unexpected embedding dimension"):
        embedding_module.embed_chunks(["hello"])


def test_reserve_embedding_quota_rejects_batch_over_limit():
    with pytest.raises(ValueError, match="exceeds the local embedding quota"):
        embedding_module._reserve_embedding_quota(embedding_module.MAX_TEXTS_PER_MINUTE + 1)


def test_get_retry_delay_reads_google_retry_info():
    exc = SimpleNamespace(
        details={
            "error": {
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "12.5s",
                    }
                ]
            }
        }
    )

    assert embedding_module._get_retry_delay(exc) == 12.5


def test_embed_chunks_retries_gemini_429(monkeypatch):
    configure_embedding(monkeypatch, dimension=3)
    calls = 0

    class RetryOnceModels:
        def embed_content(self, *, model, contents, config):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise FakeAPIError(429)
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])])

    install_fake_client(monkeypatch, RetryOnceModels())
    monkeypatch.setattr(embedding_module, "APIError", FakeAPIError)
    monkeypatch.setattr(embedding_module, "_get_retry_delay", lambda exc: 0.0)
    monkeypatch.setattr(embedding_module.time, "sleep", lambda seconds: None)

    result = embedding_module.embed_chunks(["hello"])

    assert calls == 2
    assert result == [[0.1, 0.2, 0.3]]


def test_embed_chunks_does_not_retry_non_429_api_error(monkeypatch):
    configure_embedding(monkeypatch, dimension=3)
    calls = 0

    class FailingModels:
        def embed_content(self, *, model, contents, config):
            nonlocal calls
            calls += 1
            raise FakeAPIError(500)

    install_fake_client(monkeypatch, FailingModels())
    monkeypatch.setattr(embedding_module, "APIError", FakeAPIError)

    with pytest.raises(FakeAPIError):
        embedding_module.embed_chunks(["hello"])

    assert calls == 1
