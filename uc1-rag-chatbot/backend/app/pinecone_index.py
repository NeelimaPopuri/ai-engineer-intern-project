"""Pinecone adapter for the SearchIndex interface.

Pinecone holds only vectors, chunk ids and a few filter fields (version dates, jurisdiction).
The text of every passage stays in our own database, which remains the source of truth.
It talks to Pinecone's REST API with httpx, so it adds no new dependency and no native component.
Request formats follow https://docs.pinecone.io/reference/api/2025-10/data-plane/ (checked 2026-11-20).
"""

import uuid
from datetime import date
from typing import Callable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .embeddings import EmbeddingError, embed_texts
from .models import Chunk, ChunkEmbedding, Document, DocumentVersion
from .search import FallbackIndex, SearchHit

API_VERSION = "2025-10"
OPEN_END = 99991231  # stands in for "no end date": Pinecone filters compare numbers, not nulls
UPSERT_BATCH = 100


class PineconeError(RuntimeError):
    """Pinecone could not be used (not configured, unreachable, or it refused the request)."""


def date_number(d: date) -> int:
    """2026-03-18 becomes 20260318, so Pinecone can compare dates as numbers."""
    return d.year * 10000 + d.month * 100 + d.day


class PineconeClient:
    def __init__(self, host: str | None = None, api_key: str | None = None, namespace: str | None = None):
        self.host = (host or settings.pinecone_index_host).removeprefix("https://").rstrip("/")
        self.api_key = api_key or settings.pinecone_api_key
        self.namespace = namespace or settings.pinecone_namespace
        if not self.host or not self.api_key:
            raise PineconeError("Pinecone is not configured: set PINECONE_API_KEY and PINECONE_INDEX_HOST in .env")

    def _post(self, path: str, body: dict) -> dict:
        try:
            res = httpx.post(
                f"https://{self.host}{path}",
                headers={"Api-Key": self.api_key, "X-Pinecone-Api-Version": API_VERSION},
                json=body,
                timeout=30,
            )
        except httpx.TransportError as exc:
            raise PineconeError(f"Pinecone could not be reached: {type(exc).__name__}") from exc
        if res.status_code != 200:
            raise PineconeError(f"Pinecone request failed with HTTP {res.status_code}")
        return res.json()

    def upsert(self, vectors: list[dict]) -> int:
        result = self._post("/vectors/upsert", {"vectors": vectors, "namespace": self.namespace})
        return int(result.get("upsertedCount", 0))

    def query(self, vector: list[float], top_k: int, metadata_filter: dict) -> list[dict]:
        result = self._post("/query", {
            "namespace": self.namespace, "vector": vector, "topK": top_k,
            "filter": metadata_filter, "includeMetadata": True,
        })
        return result.get("matches", [])


def sync_to_pinecone(session: Session, client: PineconeClient, batch_size: int = UPSERT_BATCH) -> int:
    """Copy every stored vector to Pinecone with its current version dates. Safe to repeat.

    Run this after ingesting a new version: closing an old version changes its end date, and
    Pinecone only knows the dates from the last sync.
    """
    rows = session.execute(
        select(Chunk.id, ChunkEmbedding.vector, DocumentVersion, Document)
        .join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
        .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(DocumentVersion.status != "draft")
    ).all()
    vectors = [
        {
            "id": str(chunk_id),
            "values": vector,
            "metadata": {
                "effective_from": date_number(version.effective_from),
                "effective_to": date_number(version.effective_to) if version.effective_to else OPEN_END,
                "jurisdiction": document.jurisdiction,
                "version_id": str(version.id),
            },
        }
        for chunk_id, vector, version, document in rows
    ]
    sent = 0
    for start in range(0, len(vectors), batch_size):
        sent += client.upsert(vectors[start : start + batch_size])
    return sent


class PineconeIndex:
    """Ask Pinecone for the closest vectors among those in force on the date, then read the text locally."""

    def __init__(self, session: Session, embed: Callable[..., list[list[float]]] = embed_texts,
                 client: PineconeClient | None = None):
        self.session = session
        self.embed = embed
        self._client = client

    @property
    def client(self) -> PineconeClient:
        if self._client is None:
            self._client = PineconeClient()  # raises PineconeError if not configured
        return self._client

    def search(self, query: str, *, as_of: date, jurisdiction: str | None = None, top_k: int = 8) -> list[SearchHit]:
        day = date_number(as_of)
        metadata_filter: dict = {"effective_from": {"$lte": day}, "effective_to": {"$gt": day}}
        if jurisdiction:
            metadata_filter["jurisdiction"] = {"$eq": jurisdiction}

        vector = self.embed([query], is_query=True)[0]  # EmbeddingError propagates so a caller can fall back
        matches = self.client.query(vector, top_k, metadata_filter)
        scores = {uuid.UUID(m["id"]): float(m["score"]) for m in matches}
        if not scores:
            return []

        rows = self.session.execute(
            select(Chunk, DocumentVersion, Document)
            .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Chunk.id.in_(scores))
        ).all()
        hits = [
            SearchHit(
                chunk_id=c.id, version_id=v.id, document_title=d.title, version_number=v.version_number,
                effective_from=v.effective_from, effective_to=v.effective_to, section_ref=c.section_ref,
                text=c.text, score=scores[c.id], vector_score=scores[c.id], keyword_score=0.0,
                document_type=d.document_type,
            )
            for c, v, d in rows
            # Our database is the source of truth. If Pinecone's dates are stale, drop the hit here.
            if v.status != "draft" and v.effective_from <= as_of and (v.effective_to is None or v.effective_to > as_of)
        ]
        return sorted(hits, key=lambda h: -h.score)


class PineconeFallbackIndex:
    """Pinecone first. If it is not configured, unreachable, or the question cannot be embedded,
    use the local search (in-memory vectors, then keywords), so the app keeps answering."""

    def __init__(self, session: Session, embed: Callable[..., list[list[float]]] = embed_texts,
                 client: PineconeClient | None = None):
        self.primary = PineconeIndex(session, embed, client)
        self.fallback = FallbackIndex(session, embed)

    def search(self, query: str, *, as_of: date, jurisdiction: str | None = None, top_k: int = 8) -> list[SearchHit]:
        try:
            return self.primary.search(query, as_of=as_of, jurisdiction=jurisdiction, top_k=top_k)
        except (EmbeddingError, PineconeError):
            return self.fallback.search(query, as_of=as_of, jurisdiction=jurisdiction, top_k=top_k)
