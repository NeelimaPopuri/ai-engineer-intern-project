import os

os.environ.setdefault("APP_API_KEY", "test-app-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import httpx
import pytest

from app import embeddings


class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body or {}

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch, tmp_path):
    monkeypatch.setattr(embeddings.time, "sleep", lambda s: None)
    monkeypatch.setattr(embeddings, "_CACHE_PATH", tmp_path / "cache.json")  # never touch the real cache


def _script(monkeypatch, steps):
    calls = iter(steps)

    def fake_post(*args, **kwargs):
        step = next(calls)
        if isinstance(step, Exception):
            raise step
        return step

    monkeypatch.setattr(embeddings.httpx, "post", fake_post)


def test_dropped_connection_is_retried(monkeypatch):
    ok = FakeResponse(200, {"embeddings": [{"values": [0.1, 0.2]}]})
    _script(monkeypatch, [httpx.RemoteProtocolError("peer closed connection"), ok])
    assert embeddings.embed_texts(["hello"]) == [[0.1, 0.2]]


def test_rate_limit_is_retried(monkeypatch):
    ok = FakeResponse(200, {"embeddings": [{"values": [1.0]}]})
    _script(monkeypatch, [FakeResponse(429), ok])
    assert embeddings.embed_texts(["hello"]) == [[1.0]]


def test_repeated_network_failure_becomes_embedding_error(monkeypatch):
    _script(monkeypatch, [httpx.ConnectError("down")] * 8)
    with pytest.raises(embeddings.EmbeddingError):
        embeddings.embed_texts(["hello"])


def test_a_question_fails_fast_so_search_can_fall_back(monkeypatch):
    _script(monkeypatch, [FakeResponse(429)])
    with pytest.raises(embeddings.EmbeddingError):
        embeddings.embed_texts(["hello"], is_query=True)


def test_a_repeated_question_is_served_from_the_cache(monkeypatch):
    ok = FakeResponse(200, {"embeddings": [{"values": [0.5, 0.5]}]})
    _script(monkeypatch, [ok])  # a second API call would raise StopIteration
    first = embeddings.embed_texts(["What is CSRD?"], is_query=True)
    again = embeddings.embed_texts(["  what is   csrd? "], is_query=True)  # same question, different spacing and case
    assert first == again == [[0.5, 0.5]]


def test_cache_file_never_contains_the_question_text(monkeypatch):
    ok = FakeResponse(200, {"embeddings": [{"values": [0.1]}]})
    _script(monkeypatch, [ok])
    embeddings.embed_texts(["client secret merger plan"], is_query=True)
    assert "merger" not in embeddings._CACHE_PATH.read_text(encoding="utf-8")


def test_damaged_cache_is_ignored(monkeypatch):
    embeddings._CACHE_PATH.write_text("{not json", encoding="utf-8")
    ok = FakeResponse(200, {"embeddings": [{"values": [0.9]}]})
    _script(monkeypatch, [ok])
    assert embeddings.embed_texts(["hello"], is_query=True) == [[0.9]]


def test_documents_are_not_cached(monkeypatch):
    ok = FakeResponse(200, {"embeddings": [{"values": [0.3]}]})
    _script(monkeypatch, [ok, ok])
    embeddings.embed_texts(["a chunk"])
    embeddings.embed_texts(["a chunk"])  # two API calls: only questions are cached
    assert not embeddings._CACHE_PATH.exists()
