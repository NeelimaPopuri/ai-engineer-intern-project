"""Ingest a source document version: store it, chunk it, and retire the version it replaces."""

import hashlib
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .chunking import chunk_text
from .models import Chunk, Document, DocumentVersion


class IngestionError(ValueError):
    """The document cannot be ingested as given."""


def _content_hash(text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in text.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def ingest_document_version(
    session: Session,
    *,
    title: str,
    document_type: str,
    jurisdiction: str,
    text: str,
    effective_from: date,
    publisher: str | None = None,
    source_url: str | None = None,
    max_tokens: int = 350,
    overlap_tokens: int = 40,
) -> DocumentVersion:
    """Store one version of a document with its chunks.

    - The same text for the same document is stored once (re-running is safe).
    - A new version must take effect after the previous one. The previous version is
      closed on the new version's start date and marked superseded.
    """
    if not text.strip():
        raise IngestionError("The document text is empty")

    document = session.scalars(
        select(Document).where(Document.title == title, Document.jurisdiction == jurisdiction)
    ).first()
    if document is None:
        document = Document(
            title=title, document_type=document_type, jurisdiction=jurisdiction,
            publisher=publisher, source_url=source_url,
        )
        session.add(document)
        session.flush()

    versions = session.scalars(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number)
    ).all()

    content_hash = _content_hash(text)
    for existing in versions:
        if existing.content_hash == content_hash:
            return existing

    latest = versions[-1] if versions else None
    if latest is not None and effective_from <= latest.effective_from:
        raise IngestionError(
            f"A new version must take effect after {latest.effective_from}; got {effective_from}"
        )

    version = DocumentVersion(
        document_id=document.id,
        version_number=(latest.version_number + 1) if latest else 1,
        effective_from=effective_from,
        status="current",
        content_hash=content_hash,
    )
    session.add(version)
    session.flush()

    if latest is not None:
        latest.effective_to = effective_from
        latest.status = "superseded"
        latest.superseded_by_id = version.id

    for piece in chunk_text(text, max_tokens=max_tokens, overlap_tokens=overlap_tokens):
        session.add(
            Chunk(
                version_id=version.id, ordinal=piece.ordinal, section_ref=piece.section_ref,
                text=piece.text, token_count=piece.token_count,
            )
        )
    session.flush()
    return version
