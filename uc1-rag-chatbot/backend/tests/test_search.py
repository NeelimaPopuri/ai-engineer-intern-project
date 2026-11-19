import os
from datetime import date

os.environ.setdefault("APP_API_KEY", "test-app-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.ingestion import ingest_document_version
from app.models import Chunk, ChunkEmbedding
from app.search import LocalHybridIndex, tokenize

# Tiny fake embedder: a 3-number vector from keyword presence, so no real model is called.
def fake_embed(texts, *, is_query=False):
    return [[float("tax" in t.lower()), float("report" in t.lower()), 0.1] for t in texts]


V1 = "Article 1 Scope\nThis rule covers tax matters for large companies.\n\nArticle 2 Reporting\nCompanies must report yearly."
V2 = V1.replace("large companies", "all companies")


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        ingest_document_version(s, title="Rule", document_type="directive", jurisdiction="EU", text=V1, effective_from=date(2024, 1, 1))
        ingest_document_version(s, title="Rule", document_type="directive", jurisdiction="EU", text=V2, effective_from=date(2025, 1, 1))
        for chunk in s.scalars(select(Chunk)).all():
            s.add(ChunkEmbedding(chunk_id=chunk.id, model="fake", vector=fake_embed([chunk.text])[0]))
        s.commit()
        yield s


def test_tokenizer_keeps_article_numbers():
    assert tokenize("Article 29b applies") == ["article", "29b", "applies"]


def test_search_returns_only_the_version_in_force(session):
    index = LocalHybridIndex(session, embed=fake_embed)
    old = index.search("tax companies", as_of=date(2024, 6, 1))
    new = index.search("tax companies", as_of=date(2025, 6, 1))
    assert old and {h.version_number for h in old} == {1}
    assert new and {h.version_number for h in new} == {2}


def test_nothing_is_returned_before_the_first_version(session):
    assert LocalHybridIndex(session, embed=fake_embed).search("tax", as_of=date(2023, 1, 1)) == []


def test_keyword_match_ranks_first(session):
    hits = LocalHybridIndex(session, embed=fake_embed).search("tax matters", as_of=date(2024, 6, 1))
    assert hits[0].section_ref == "Article 1 Scope"
    assert hits[0].keyword_score > 0


def test_jurisdiction_filter(session):
    index = LocalHybridIndex(session, embed=fake_embed)
    assert index.search("tax", as_of=date(2024, 6, 1), jurisdiction="FR") == []
    assert index.search("tax", as_of=date(2024, 6, 1), jurisdiction="EU")
