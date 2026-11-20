import os
from datetime import date

os.environ.setdefault("APP_API_KEY", "test-app-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import pinecone_index, search
from app.db import Base
from app.embeddings import EmbeddingError
from app.ingestion import ingest_document_version
from app.models import Chunk, ChunkEmbedding
from app.pinecone_index import (
    OPEN_END, PineconeClient, PineconeError, PineconeFallbackIndex, PineconeIndex, date_number, sync_to_pinecone,
)

V1 = "Article 1 Scope\nThis rule covers tax matters for large companies."
V2 = V1.replace("large", "all")


def fake_embed(texts, *, is_query=False):
    return [[1.0, 0.0, 0.0] for _ in texts]


@pytest.fixture(autouse=True)
def fresh_store():
    search._store.count = -1  # the local vector matrix is cached between tests otherwise


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        for text, start in ((V1, date(2024, 1, 1)), (V2, date(2025, 1, 1))):
            ingest_document_version(s, title="Rule", document_type="directive", jurisdiction="EU", text=text, effective_from=start)
        for chunk in s.scalars(select(Chunk)).all():
            s.add(ChunkEmbedding(chunk_id=chunk.id, model="fake", vector=[1.0, 0.0, 0.0]))
        s.commit()
        yield s


class FakeClient:
    """Stands in for Pinecone. Records what it was asked and returns the chunks we tell it to."""

    def __init__(self, ids=(), fail=False):
        self.ids, self.fail, self.queries, self.upserts = list(ids), fail, [], []

    def query(self, vector, top_k, metadata_filter):
        if self.fail:
            raise PineconeError("down")
        self.queries.append((vector, top_k, metadata_filter))
        return [{"id": str(i), "score": 0.9 - n / 10, "metadata": {}} for n, i in enumerate(self.ids)]

    def upsert(self, vectors):
        self.upserts.append(vectors)
        return len(vectors)


def chunk_ids(session, version_number):
    from app.models import DocumentVersion
    return [c.id for c in session.scalars(select(Chunk).join(DocumentVersion).where(DocumentVersion.version_number == version_number))]


def test_dates_become_comparable_numbers():
    assert date_number(date(2026, 3, 18)) == 20260318


def test_query_filters_by_date_and_jurisdiction(session):
    client = FakeClient(chunk_ids(session, 2))
    PineconeIndex(session, fake_embed, client).search("tax", as_of=date(2025, 6, 1), jurisdiction="EU", top_k=5)
    vector, top_k, metadata_filter = client.queries[0]
    assert top_k == 5 and vector == [1.0, 0.0, 0.0]
    assert metadata_filter == {
        "effective_from": {"$lte": 20250601}, "effective_to": {"$gt": 20250601}, "jurisdiction": {"$eq": "EU"},
    }


def test_hits_are_built_from_our_database_not_from_pinecone(session):
    client = FakeClient(chunk_ids(session, 2))
    hits = PineconeIndex(session, fake_embed, client).search("tax", as_of=date(2025, 6, 1))
    assert len(hits) == 1 and hits[0].version_number == 2
    assert "all companies" in hits[0].text and hits[0].vector_score == pytest.approx(0.9)


def test_stale_pinecone_dates_cannot_serve_a_superseded_version(session):
    # Pinecone still thinks version 1 is in force, but our database closed it on 2025-01-01.
    client = FakeClient(chunk_ids(session, 1))
    assert PineconeIndex(session, fake_embed, client).search("tax", as_of=date(2025, 6, 1)) == []


def test_no_matches_gives_no_hits(session):
    assert PineconeIndex(session, fake_embed, FakeClient()).search("tax", as_of=date(2025, 6, 1)) == []


def test_sync_sends_vectors_with_dates_and_an_open_end(session):
    client = FakeClient()
    assert sync_to_pinecone(session, client, batch_size=1) == 2
    assert len(client.upserts) == 2  # batched
    sent = {v["metadata"]["effective_from"]: v for batch in client.upserts for v in batch}
    assert sent[20240101]["metadata"]["effective_to"] == 20250101  # closed version keeps its end date
    assert sent[20250101]["metadata"]["effective_to"] == OPEN_END  # current version is open-ended
    assert sent[20250101]["metadata"]["jurisdiction"] == "EU"
    assert "text" not in sent[20250101]["metadata"]  # passage text never leaves our database


def test_fallback_is_used_when_pinecone_is_down(session):
    index = PineconeFallbackIndex(session, fake_embed, FakeClient(fail=True))
    hits = index.search("tax", as_of=date(2025, 6, 1))
    assert hits and hits[0].version_number == 2  # answered from the local vectors


def test_fallback_is_used_when_the_question_cannot_be_embedded(session):
    def no_embed(texts, *, is_query=False):
        raise EmbeddingError("quota")

    index = PineconeFallbackIndex(session, no_embed, FakeClient(chunk_ids(session, 2)))
    assert index.search("tax matters", as_of=date(2025, 6, 1))  # keyword search still finds it


def test_unconfigured_pinecone_falls_back_instead_of_failing(session, monkeypatch):
    monkeypatch.setattr(pinecone_index.settings, "pinecone_api_key", "")
    monkeypatch.setattr(pinecone_index.settings, "pinecone_index_host", "")
    assert PineconeFallbackIndex(session, fake_embed).search("tax", as_of=date(2025, 6, 1))


# the REST client itself

class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body or {}

    def json(self):
        return self._body


def test_client_requires_a_key_and_host(monkeypatch):
    monkeypatch.setattr(pinecone_index.settings, "pinecone_api_key", "")
    monkeypatch.setattr(pinecone_index.settings, "pinecone_index_host", "")
    with pytest.raises(PineconeError):
        PineconeClient()


def test_client_sends_the_documented_request(monkeypatch):
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, body=json)
        return FakeResponse(200, {"matches": [{"id": "x", "score": 0.5}]})

    monkeypatch.setattr(pinecone_index.httpx, "post", fake_post)
    client = PineconeClient(host="https://idx.svc.example.pinecone.io/", api_key="secret", namespace="ns")
    assert client.query([0.1], 3, {"a": 1}) == [{"id": "x", "score": 0.5}]
    assert seen["url"] == "https://idx.svc.example.pinecone.io/query"
    assert seen["headers"] == {"Api-Key": "secret", "X-Pinecone-Api-Version": "2025-10"}
    assert seen["body"] == {"namespace": "ns", "vector": [0.1], "topK": 3, "filter": {"a": 1}, "includeMetadata": True}


def test_client_turns_http_and_network_errors_into_pinecone_error(monkeypatch):
    client = PineconeClient(host="idx.example", api_key="k")
    monkeypatch.setattr(pinecone_index.httpx, "post", lambda *a, **k: FakeResponse(401))
    with pytest.raises(PineconeError):
        client.query([0.1], 3, {})

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(pinecone_index.httpx, "post", boom)
    with pytest.raises(PineconeError):
        client.upsert([])
