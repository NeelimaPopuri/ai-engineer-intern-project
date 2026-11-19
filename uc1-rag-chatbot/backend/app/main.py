import logging
import uuid
from datetime import date, datetime

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .answer import answer_question
from .config import settings
from .db import get_session
from .embeddings import EmbeddingError
from .llm import LLMError
from .models import Citation, Conversation, Document, DocumentVersion
from .search import LocalHybridIndex, SearchIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("datafactz.uc1")

app = FastAPI(title="DataFactZ Regulatory Change Navigator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str | None = Security(api_key_header)) -> None:
    if key != settings.app_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid API key")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/documents", dependencies=[Depends(require_api_key)])
def list_documents(session: Session = Depends(get_session)) -> list[dict]:
    out = []
    for doc in session.scalars(select(Document).order_by(Document.title)).all():
        versions = session.scalars(
            select(DocumentVersion).where(DocumentVersion.document_id == doc.id).order_by(DocumentVersion.version_number)
        ).all()
        out.append({
            "id": str(doc.id), "title": doc.title, "jurisdiction": doc.jurisdiction, "source_url": doc.source_url,
            "versions": [{"version": v.version_number, "effective_from": v.effective_from.isoformat(),
                          "effective_to": v.effective_to.isoformat() if v.effective_to else None, "status": v.status}
                         for v in versions],
        })
    return out


# ---- conversations ----


class ConversationCreate(BaseModel):
    jurisdiction: str | None = Field(default=None, max_length=50)
    company_size: str | None = Field(default=None, max_length=50)
    as_of_date: date | None = None


class QuestionIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class CitationOut(BaseModel):
    id: uuid.UUID
    rank: int
    quoted_text: str
    relevance_score: float | None
    document_title: str
    version_number: int
    effective_from: date
    effective_to: date | None
    section_ref: str | None


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    answer_status: str | None
    created_at: datetime
    citations: list[CitationOut] = []


class ConversationOut(BaseModel):
    id: uuid.UUID
    jurisdiction: str | None
    company_size: str | None
    as_of_date: date | None
    messages: list[MessageOut] = []


def get_index(session: Session = Depends(get_session)) -> SearchIndex:
    return LocalHybridIndex(session)


def _citation_out(c: Citation) -> CitationOut:
    version = c.chunk.version
    return CitationOut(
        id=c.id, rank=c.rank, quoted_text=c.quoted_text, relevance_score=c.relevance_score,
        document_title=version.document.title, version_number=version.version_number,
        effective_from=version.effective_from, effective_to=version.effective_to, section_ref=c.chunk.section_ref,
    )


def _message_out(m) -> MessageOut:
    return MessageOut(
        id=m.id, role=m.role, content=m.content, answer_status=m.answer_status, created_at=m.created_at,
        citations=[_citation_out(c) for c in m.citations],
    )


def _conversation_out(c: Conversation) -> ConversationOut:
    return ConversationOut(
        id=c.id, jurisdiction=c.jurisdiction_filter, company_size=c.company_size_filter,
        as_of_date=c.as_of_date, messages=[_message_out(m) for m in c.messages],
    )


def _get_conversation(session: Session, conversation_id: uuid.UUID) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


@app.post("/api/v1/conversations", status_code=201, response_model=ConversationOut, dependencies=[Depends(require_api_key)])
def create_conversation(body: ConversationCreate, session: Session = Depends(get_session)):
    conversation = Conversation(
        jurisdiction_filter=body.jurisdiction, company_size_filter=body.company_size,
        as_of_date=body.as_of_date or date.today(),
    )
    session.add(conversation)
    session.commit()
    return _conversation_out(conversation)


@app.get("/api/v1/conversations", response_model=list[ConversationOut], dependencies=[Depends(require_api_key)])
def list_conversations(session: Session = Depends(get_session)):
    rows = session.scalars(select(Conversation).order_by(Conversation.created_at.desc()).limit(50)).all()
    return [_conversation_out(c) for c in rows]


@app.get("/api/v1/conversations/{conversation_id}", response_model=ConversationOut, dependencies=[Depends(require_api_key)])
def get_conversation(conversation_id: uuid.UUID, session: Session = Depends(get_session)):
    return _conversation_out(_get_conversation(session, conversation_id))


@app.post("/api/v1/conversations/{conversation_id}/messages", status_code=201, response_model=MessageOut,
          dependencies=[Depends(require_api_key)])
def ask(conversation_id: uuid.UUID, body: QuestionIn, session: Session = Depends(get_session),
        index: SearchIndex = Depends(get_index)):
    conversation = _get_conversation(session, conversation_id)
    try:
        message = answer_question(session, conversation, body.question, index)
    except (EmbeddingError, LLMError) as exc:
        session.rollback()
        log.warning("model provider failure: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The model provider returned an error")
    session.commit()
    log.info("answered status=%s latency_ms=%s question_chars=%d", message.answer_status, message.latency_ms, len(body.question))
    return _message_out(message)


@app.get("/api/v1/citations/{citation_id}", response_model=CitationOut, dependencies=[Depends(require_api_key)])
def get_citation(citation_id: uuid.UUID, session: Session = Depends(get_session)):
    citation = session.get(Citation, citation_id)
    if citation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Citation not found")
    return _citation_out(citation)
