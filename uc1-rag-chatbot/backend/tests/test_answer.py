import os
from datetime import date

os.environ.setdefault("APP_API_KEY", "test-app-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.answer import REFUSAL_TEXT, answer_question
from app.db import Base, get_session
from app.ingestion import ingest_document_version
from app.llm import LLMError, LLMReply
from app.models import Chunk, Conversation, Message
from app.search import SearchHit

HEADERS = {"X-API-Key": "test-app-key"}


@pytest.fixture
def session():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        ingest_document_version(
            s, title="Rule", document_type="directive", jurisdiction="EU",
            text="Article 1 Scope\nLarge companies must report.", effective_from=date(2024, 1, 1),
        )
        s.commit()
        yield s


class FakeIndex:
    def __init__(self, session, vector_score=0.8, empty=False, extra_news=False):
        self.session, self.vector_score, self.empty, self.extra_news = session, vector_score, empty, extra_news

    def search(self, query, *, as_of, jurisdiction=None, top_k=8):
        if self.empty:
            return []
        chunk = self.session.scalars(select(Chunk)).first()
        version = chunk.version
        hits = [SearchHit(chunk.id, version.id, "Rule", 1, version.effective_from, None, chunk.section_ref,
                          chunk.text, 0.03, self.vector_score, 2.0)]
        if self.extra_news:
            hits.append(SearchHit(chunk.id, version.id, "News", 1, version.effective_from, None, None,
                                  "News text", 0.02, self.vector_score, 1.0, document_type="news"))
        return hits


def reply(text):
    return lambda prompt: LLMReply(text, 100, 20, "fake-model")


def make_conversation(session):
    c = Conversation(as_of_date=date(2025, 1, 1))
    session.add(c)
    session.flush()
    return c


def test_good_answer_is_saved_with_its_citation(session):
    msg = answer_question(session, make_conversation(session), "Who must report?", FakeIndex(session),
                          reply("Large companies must report [1]."))
    assert msg.answer_status == "answered"
    assert len(msg.citations) == 1 and msg.citations[0].quoted_text.startswith("Large companies")
    assert (msg.model, msg.input_tokens, msg.output_tokens) == ("fake-model", 100, 20)


def test_weak_evidence_refuses_without_calling_the_model(session):
    def boom(prompt):
        raise AssertionError("model must not be called")

    msg = answer_question(session, make_conversation(session), "Capital of France?", FakeIndex(session, vector_score=0.4), boom)
    assert msg.answer_status == "insufficient_evidence" and msg.content == REFUSAL_TEXT and msg.citations == []


def test_no_results_refuses(session):
    msg = answer_question(session, make_conversation(session), "Anything?", FakeIndex(session, empty=True), reply("x [1]"))
    assert msg.answer_status == "insufficient_evidence"


def test_grouped_citation_numbers_are_accepted(session):
    msg = answer_question(session, make_conversation(session), "Who must report?", FakeIndex(session),
                          reply("Large companies must report [1, 1]."))
    assert msg.answer_status == "answered" and len(msg.citations) == 1


def test_grouped_citation_with_unknown_number_is_rejected(session):
    msg = answer_question(session, make_conversation(session), "Who must report?", FakeIndex(session),
                          reply("Large companies must report [1, 4]."))
    assert msg.answer_status == "insufficient_evidence"


def test_legal_and_news_sources_together_are_flagged(session):
    msg = answer_question(session, make_conversation(session), "Who must report?", FakeIndex(session, extra_news=True),
                          reply("Large companies must report [1] and [2]."))
    assert msg.answer_status == "conflict" and "different authority" in msg.content


def test_legal_source_alone_is_not_flagged(session):
    msg = answer_question(session, make_conversation(session), "Who must report?", FakeIndex(session, extra_news=True),
                          reply("Large companies must report [1]."))
    assert msg.answer_status == "answered"


def test_markers_are_renumbered_to_match_citation_ranks(session):
    class ThreeHits(FakeIndex):
        def search(self, *args, **kwargs):
            return super().search(*args, **kwargs) * 3

    msg = answer_question(session, make_conversation(session), "Who must report?", ThreeHits(session),
                          reply("Companies report [3]. Large ones also [3, 1]."))
    assert msg.content == "Companies report [1]. Large ones also [1, 2]."
    assert [c.rank for c in msg.citations] == [1, 2]


def test_answer_without_citation_is_rejected(session):
    msg = answer_question(session, make_conversation(session), "Who must report?", FakeIndex(session), reply("Large companies."))
    assert msg.answer_status == "insufficient_evidence" and msg.citations == []


def test_citation_to_unknown_source_is_rejected(session):
    msg = answer_question(session, make_conversation(session), "Who must report?", FakeIndex(session),
                          reply("Large companies [1] and others [7]."))
    assert msg.answer_status == "insufficient_evidence"


def test_model_saying_insufficient_becomes_a_refusal(session):
    msg = answer_question(session, make_conversation(session), "Who must report?", FakeIndex(session), reply("INSUFFICIENT"))
    assert msg.answer_status == "insufficient_evidence"


# API

@pytest.fixture
def client(session):
    main.app.dependency_overrides[get_session] = lambda: session
    main.app.dependency_overrides[main.get_index] = lambda: FakeIndex(session)
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_ask_requires_api_key(client):
    assert client.post("/api/v1/conversations", json={}).status_code == 401


def test_conversation_round_trip(client, monkeypatch):
    monkeypatch.setattr("app.answer.generate", reply("Large companies must report [1]."))
    created = client.post("/api/v1/conversations", json={"jurisdiction": "EU"}, headers=HEADERS)
    assert created.status_code == 201
    cid = created.json()["id"]

    asked = client.post(f"/api/v1/conversations/{cid}/messages", json={"question": "Who must report?"}, headers=HEADERS)
    assert asked.status_code == 201
    body = asked.json()
    assert body["answer_status"] == "answered" and body["citations"][0]["document_title"] == "Rule"

    fetched = client.get(f"/api/v1/conversations/{cid}", headers=HEADERS).json()
    assert [m["role"] for m in fetched["messages"]] == ["user", "assistant"]
    assert client.get(f"/api/v1/citations/{body['citations'][0]['id']}", headers=HEADERS).status_code == 200


def test_unknown_conversation_is_404_and_short_question_is_422(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/v1/conversations/{missing}/messages", json={"question": "Who?"}, headers=HEADERS).status_code == 404
    cid = client.post("/api/v1/conversations", json={}, headers=HEADERS).json()["id"]
    assert client.post(f"/api/v1/conversations/{cid}/messages", json={"question": "a"}, headers=HEADERS).status_code == 422


def test_provider_failure_is_502(client, monkeypatch):
    def fail(prompt):
        raise LLMError("down")

    monkeypatch.setattr("app.answer.generate", fail)
    cid = client.post("/api/v1/conversations", json={}, headers=HEADERS).json()["id"]
    res = client.post(f"/api/v1/conversations/{cid}/messages", json={"question": "Who must report?"}, headers=HEADERS)
    assert res.status_code == 502
