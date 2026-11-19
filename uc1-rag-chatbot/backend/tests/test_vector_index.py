import os
from datetime import date

os.environ.setdefault("APP_API_KEY", "test-app-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import search
from app.db import Base
from app.embeddings import EmbeddingError
from app.ingestion import ingest_document_version
from app.models import Chunk, ChunkEmbedding
from app.search import FallbackIndex, VectorIndex

# Fake embedder: one axis per topic word, so similarity is easy to predict.
AXES = ["tax", "report", "water"]


def fake_embed(texts, *, is_query=False):
    return [[float(w in t.lower()) + 0.01 for w in AXES] for t in texts]


V1 = "Article 1 Tax\nThis rule covers tax.\n\nArticle 2 Water\nThis rule covers water."
V2 = V1.replace("covers tax", "covers all tax")


@pytest.fixture(autouse=True)
def fresh_store():
    search._store.count = -1  # the vector matrix is cached between tests otherwise


@pytest.fixture
def session():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        for text, start in ((V1, date(2024, 1, 1)), (V2, date(2025, 1, 1))):
            ingest_document_version(s, title="Rule", document_type="directive", jurisdiction="EU", text=text, effective_from=start)
        for chunk in s.scalars(select(Chunk)).all():
            s.add(ChunkEmbedding(chunk_id=chunk.id, model="fake", vector=fake_embed([chunk.text])[0]))
        s.commit()
        yield s


def test_closest_chunk_ranks_first(session):
    hits = VectorIndex(session, fake_embed).search("tax", as_of=date(2024, 6, 1))
    assert hits[0].section_ref == "Article 1 Tax"
    assert hits[0].vector_score > hits[1].vector_score
    assert hits[0].keyword_score == 0.0


def test_only_the_version_in_force_is_searched(session):
    index = VectorIndex(session, fake_embed)
    assert {h.version_number for h in index.search("tax", as_of=date(2024, 6, 1))} == {1}
    assert {h.version_number for h in index.search("tax", as_of=date(2025, 6, 1))} == {2}


def test_nothing_before_the_first_version(session):
    assert VectorIndex(session, fake_embed).search("tax", as_of=date(2023, 1, 1)) == []


def test_jurisdiction_filter(session):
    index = VectorIndex(session, fake_embed)
    assert index.search("tax", as_of=date(2024, 6, 1), jurisdiction="FR") == []
    assert index.search("tax", as_of=date(2024, 6, 1), jurisdiction="EU")


def test_top_k_limits_results(session):
    assert len(VectorIndex(session, fake_embed).search("tax", as_of=date(2024, 6, 1), top_k=1)) == 1


def test_chunk_without_a_vector_cannot_be_found(session):
    water = session.scalars(select(Chunk).where(Chunk.section_ref == "Article 2 Water")).first()
    session.delete(session.get(ChunkEmbedding, water.id))
    session.commit()
    hits = VectorIndex(session, fake_embed).search("water", as_of=date(2024, 6, 1))
    assert all(h.section_ref != "Article 2 Water" for h in hits)


def test_unembeddable_question_raises(session):
    def broken(texts, *, is_query=False):
        raise EmbeddingError("quota")

    with pytest.raises(EmbeddingError):
        VectorIndex(session, broken).search("tax", as_of=date(2024, 6, 1))


def test_fallback_uses_keyword_search_when_embedding_fails(session):
    def broken(texts, *, is_query=False):
        raise EmbeddingError("quota")

    hits = FallbackIndex(session, broken).search("tax", as_of=date(2024, 6, 1))
    assert hits and hits[0].vector_score is None and hits[0].keyword_score > 0
