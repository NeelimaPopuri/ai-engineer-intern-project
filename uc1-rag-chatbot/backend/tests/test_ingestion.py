import os
from datetime import date

os.environ.setdefault("APP_API_KEY", "test-app-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.chunking import chunk_text, estimate_tokens
from app.db import Base
from app.ingestion import IngestionError, ingest_document_version
from app.models import Chunk
from app.versions import version_in_force

SAMPLE = """Preamble text before any heading.

Article 1 Scope
This directive applies to large undertakings.

Article 2 Definitions
For the purposes of this directive the following definitions apply.
"""


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _ingest(session, text, start, **kw):
    return ingest_document_version(
        session, title="Sample directive", document_type="directive", jurisdiction="EU",
        text=text, effective_from=start, **kw,
    )


# chunking

def test_splits_at_article_headings():
    chunks = chunk_text(SAMPLE)
    assert [c.section_ref for c in chunks] == [None, "Article 1 Scope", "Article 2 Definitions"]
    assert chunks[1].text.startswith("This directive applies")


def test_ordinals_run_from_zero_without_gaps():
    chunks = chunk_text(SAMPLE)
    assert [c.ordinal for c in chunks] == [0, 1, 2]


def test_long_section_is_split_and_every_chunk_respects_the_limit():
    body = "\n\n".join(f"Paragraph {i}. " + "word " * 60 for i in range(12))
    chunks = chunk_text(f"Article 9 Long\n{body}", max_tokens=100, overlap_tokens=10)
    assert len(chunks) > 1
    assert all(len(c.text) <= 100 * 4 + 10 * 4 + 2 for c in chunks)
    assert all(c.section_ref == "Article 9 Long" for c in chunks)


def test_overlap_repeats_the_end_of_the_previous_chunk():
    body = "\n\n".join(f"Marker{i} " + "x" * 300 for i in range(6))
    chunks = chunk_text(f"Article 1 Overlap\n{body}", max_tokens=100, overlap_tokens=20)
    assert len(chunks) > 1
    assert chunks[0].text[-30:] in chunks[1].text


def test_single_huge_sentence_is_hard_cut():
    chunks = chunk_text("Article 1 Huge\n" + "a" * 2000, max_tokens=100, overlap_tokens=0)
    assert len(chunks) == 5
    assert all(len(c.text) <= 400 for c in chunks)


def test_empty_text_gives_no_chunks():
    assert chunk_text("   \n\n  ") == []


def test_bad_sizes_are_rejected():
    with pytest.raises(ValueError):
        chunk_text("text", max_tokens=0)
    with pytest.raises(ValueError):
        chunk_text("text", max_tokens=50, overlap_tokens=50)


def test_token_estimate_is_never_zero():
    assert estimate_tokens("a") == 1
    assert estimate_tokens("a" * 400) == 100


# ingestion

def test_ingest_creates_document_version_and_chunks(session):
    version = _ingest(session, SAMPLE, date(2024, 1, 1), publisher="EU", source_url="https://example.org/x")
    chunks = session.scalars(select(Chunk).where(Chunk.version_id == version.id)).all()
    assert version.version_number == 1 and version.status == "current"
    assert version.document.source_url == "https://example.org/x"
    assert len(chunks) == 3


def test_same_text_is_not_ingested_twice(session):
    first = _ingest(session, SAMPLE, date(2024, 1, 1))
    second = _ingest(session, SAMPLE + "   \n", date(2025, 1, 1))
    assert first.id == second.id
    assert len(session.scalars(select(Chunk)).all()) == 3


def test_new_version_supersedes_the_old_one(session):
    v1 = _ingest(session, SAMPLE, date(2024, 1, 1))
    v2 = _ingest(session, SAMPLE.replace("large", "all"), date(2025, 6, 1))
    assert v2.version_number == 2
    assert (v1.status, v1.effective_to, v1.superseded_by_id) == ("superseded", date(2025, 6, 1), v2.id)
    assert version_in_force(session, v1.document_id, date(2025, 5, 31)).id == v1.id
    assert version_in_force(session, v1.document_id, date(2025, 6, 1)).id == v2.id


def test_back_dated_version_is_rejected(session):
    _ingest(session, SAMPLE, date(2025, 1, 1))
    with pytest.raises(IngestionError):
        _ingest(session, SAMPLE + "More text", date(2024, 1, 1))


def test_empty_document_is_rejected(session):
    with pytest.raises(IngestionError):
        _ingest(session, "  ", date(2024, 1, 1))
