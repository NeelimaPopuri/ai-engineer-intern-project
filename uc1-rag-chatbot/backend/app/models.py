"""Relational schema from docs/database-design.md."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_jurisdiction", "jurisdiction"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    document_type: Mapped[str] = mapped_column(String(50))
    jurisdiction: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        Index("ix_versions_document_effective", "document_id", "effective_from"),
        Index("ix_versions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)  # null means still in force
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("document_versions.id"))
    status: Mapped[str] = mapped_column(String(20), default="current")  # current | superseded | draft
    content_hash: Mapped[str] = mapped_column(String(64))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    document: Mapped[Document] = relationship(back_populates="versions")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="version", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (Index("ix_chunks_version_ordinal", "version_id", "ordinal"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_versions.id"))
    ordinal: Mapped[int] = mapped_column(Integer)
    section_ref: Mapped[str | None] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)

    version: Mapped[DocumentVersion] = relationship(back_populates="chunks")


class ChunkEmbedding(Base):
    """One embedding vector per chunk. Kept apart from chunks so the model can be swapped."""

    __tablename__ = "chunk_embeddings"

    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chunks.id"), primary_key=True)
    model: Mapped[str] = mapped_column(String(100))
    vector: Mapped[list[float]] = mapped_column(JSON)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    title: Mapped[str | None] = mapped_column(Text)
    jurisdiction_filter: Mapped[str | None] = mapped_column(String(50))
    company_size_filter: Mapped[str | None] = mapped_column(String(50))
    as_of_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    answer_status: Mapped[str | None] = mapped_column(String(30))  # answered | insufficient_evidence | conflict
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan", order_by="Citation.rank"
    )


class Citation(Base):
    __tablename__ = "citations"
    __table_args__ = (
        Index("ix_citations_message_rank", "message_id", "rank"),
        Index("ix_citations_chunk", "chunk_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"))
    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chunks.id"))
    rank: Mapped[int] = mapped_column(Integer)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    quoted_text: Mapped[str] = mapped_column(Text)

    message: Mapped[Message] = relationship(back_populates="citations")
    chunk: Mapped[Chunk] = relationship()


class EvalQuestion(Base):
    __tablename__ = "eval_questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    question: Mapped[str] = mapped_column(Text)
    expected_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)
    expected_behavior: Mapped[str] = mapped_column(String(20))  # answer | refuse
    as_of_date: Mapped[date | None] = mapped_column(Date)


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_questions.id"))
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id"))
    run_label: Mapped[str] = mapped_column(String(100))
    cited_correctly: Mapped[bool] = mapped_column(Boolean)
    behavior_correct: Mapped[bool] = mapped_column(Boolean)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
