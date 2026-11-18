import os
from datetime import date

os.environ.setdefault("APP_API_KEY", "test-app-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.main import app
from app.models import Chunk, Citation, Conversation, Document, DocumentVersion, Message
from app.versions import version_in_force

HEADERS = {"X-API-Key": os.environ["APP_API_KEY"]}


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def document(session):
    doc = Document(title="Sample directive", document_type="directive", jurisdiction="EU")
    session.add(doc)
    session.flush()
    return doc


def _version(doc, number, start, end, status="current"):
    return DocumentVersion(
        document_id=doc.id, version_number=number, effective_from=start, effective_to=end,
        status=status, content_hash=f"hash{number}",
    )


def test_picks_version_in_force_on_a_past_date(session, document):
    v1 = _version(document, 1, date(2024, 1, 1), date(2025, 1, 1), "superseded")
    v2 = _version(document, 2, date(2025, 1, 1), None)
    session.add_all([v1, v2])
    session.flush()
    assert version_in_force(session, document.id, date(2024, 6, 1)).id == v1.id
    assert version_in_force(session, document.id, date(2026, 6, 1)).id == v2.id


def test_boundary_date_belongs_to_the_new_version(session, document):
    v1 = _version(document, 1, date(2024, 1, 1), date(2025, 1, 1), "superseded")
    v2 = _version(document, 2, date(2025, 1, 1), None)
    session.add_all([v1, v2])
    session.flush()
    assert version_in_force(session, document.id, date(2025, 1, 1)).id == v2.id
    assert version_in_force(session, document.id, date(2024, 12, 31)).id == v1.id


def test_returns_none_before_first_version(session, document):
    session.add(_version(document, 1, date(2024, 1, 1), None))
    session.flush()
    assert version_in_force(session, document.id, date(2023, 12, 31)) is None


def test_ignores_drafts(session, document):
    session.add(_version(document, 1, date(2024, 1, 1), None, status="draft"))
    session.flush()
    assert version_in_force(session, document.id, date(2025, 1, 1)) is None


def test_conversation_messages_and_citations_link_up(session, document):
    version = _version(document, 1, date(2024, 1, 1), None)
    session.add(version)
    session.flush()
    chunk = Chunk(version_id=version.id, ordinal=0, text="Article 1 text", token_count=4)
    convo = Conversation(jurisdiction_filter="EU", as_of_date=date(2026, 1, 1))
    session.add_all([chunk, convo])
    session.flush()
    msg = Message(conversation_id=convo.id, role="assistant", content="Answer [1]", answer_status="answered")
    session.add(msg)
    session.flush()
    session.add(Citation(message_id=msg.id, chunk_id=chunk.id, rank=1, quoted_text="Article 1 text"))
    session.commit()
    assert convo.messages[0].citations[0].chunk.text == "Article 1 text"


client = TestClient(app)


def test_health_returns_ok():
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_documents_require_api_key():
    assert client.get("/api/v1/documents").status_code == 401
    assert client.get("/api/v1/documents", headers=HEADERS).status_code == 200
