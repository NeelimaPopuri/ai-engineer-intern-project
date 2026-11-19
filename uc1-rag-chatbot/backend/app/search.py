"""Hybrid search behind one interface.

`SearchIndex` is what the rest of the app depends on. `LocalHybridIndex` is the pilot
implementation (keyword scoring plus vector similarity, merged by rank). An Azure AI Search
class with the same `search` method would replace it without touching the callers.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Callable, Protocol

import numpy as np
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .embeddings import embed_texts
from .models import Chunk, ChunkEmbedding, Document, DocumentVersion

_WORD = re.compile(r"[a-z0-9]+")
RRF_K = 60  # standard constant for reciprocal rank fusion


@dataclass(frozen=True)
class SearchHit:
    chunk_id: object
    version_id: object
    document_title: str
    version_number: int
    effective_from: date
    effective_to: date | None
    section_ref: str | None
    text: str
    score: float          # merged rank score, used for ordering
    vector_score: float   # cosine similarity, 0 to 1, used for the "is the evidence good enough" check
    keyword_score: float


class SearchIndex(Protocol):
    def search(
        self, query: str, *, as_of: date, jurisdiction: str | None = None, top_k: int = 8
    ) -> list[SearchHit]: ...


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _bm25(query_terms: list[str], docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    n = len(docs)
    avg_len = (sum(len(d) for d in docs) / n) if n else 0
    df = Counter(term for d in docs for term in set(d))
    scores = []
    for d in docs:
        tf = Counter(d)
        score = 0.0
        for term in set(query_terms):
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(d) / (avg_len or 1)))
        scores.append(score)
    return scores


class LocalHybridIndex:
    def __init__(self, session: Session, embed: Callable[..., list[list[float]]] = embed_texts):
        self.session = session
        self.embed = embed

    def _candidates(self, as_of: date, jurisdiction: str | None):
        """Chunks whose version was in force on `as_of`, with their vectors."""
        stmt = (
            select(Chunk, DocumentVersion, Document, ChunkEmbedding)
            .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
            .where(
                DocumentVersion.status != "draft",
                DocumentVersion.effective_from <= as_of,
                or_(DocumentVersion.effective_to.is_(None), DocumentVersion.effective_to > as_of),
            )
        )
        if jurisdiction:
            stmt = stmt.where(Document.jurisdiction == jurisdiction)
        return self.session.execute(stmt).all()

    def search(self, query: str, *, as_of: date, jurisdiction: str | None = None, top_k: int = 8) -> list[SearchHit]:
        rows = self._candidates(as_of, jurisdiction)
        if not rows:
            return []

        keyword = _bm25(tokenize(query), [tokenize(r[0].text) for r in rows])
        matrix = np.array([r[3].vector for r in rows], dtype=np.float32)
        q = np.array(self.embed([query], is_query=True)[0], dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1) * (np.linalg.norm(q) or 1.0)
        cosine = (matrix @ q) / np.where(norms == 0, 1.0, norms)

        # Merge the two rankings. A chunk that is good at either keywords or meaning rises.
        fused = np.zeros(len(rows))
        for scores in (np.array(keyword), cosine):
            for rank, idx in enumerate(np.argsort(-scores)):
                if scores is not cosine and scores[idx] == 0:
                    break  # no keyword match: it earns nothing from the keyword ranking
                fused[idx] += 1.0 / (RRF_K + rank + 1)

        hits = []
        for idx in np.argsort(-fused)[:top_k]:
            chunk, version, document, _ = rows[idx]
            hits.append(
                SearchHit(
                    chunk_id=chunk.id, version_id=version.id, document_title=document.title,
                    version_number=version.version_number, effective_from=version.effective_from,
                    effective_to=version.effective_to, section_ref=chunk.section_ref, text=chunk.text,
                    score=float(fused[idx]), vector_score=float(cosine[idx]), keyword_score=float(keyword[idx]),
                )
            )
        return hits
