"""Text to vector, through the Gemini embedding API. Everything else calls `embed_texts`,
so swapping the provider (for example Azure OpenAI) changes this one file."""

import hashlib
import json
import os
import time
from pathlib import Path

import httpx

from .config import settings

EMBEDDING_MODEL = "gemini-embedding-001"
DIMENSIONS = 768
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
BATCH_SIZE = 50

# Question vectors are cached on disk so repeating a question costs no API quota. The key is a
# hash of the question, so the question text itself is never written to disk.
_CACHE_PATH = Path(__file__).resolve().parent.parent / ".query_embedding_cache.json"


class EmbeddingError(RuntimeError):
    """The embedding service could not be used."""


def _post_with_retry(payload: dict, attempts: int = 8) -> dict:
    for attempt in range(attempts):
        last = attempt == attempts - 1
        try:
            res = httpx.post(
                URL.format(model=EMBEDDING_MODEL),
                headers={"x-goog-api-key": settings.gemini_api_key},
                json=payload,
                timeout=60,
            )
        except httpx.TransportError as exc:  # dropped connection, DNS failure, timeout
            if last:
                raise EmbeddingError(f"Embedding request could not reach the service: {type(exc).__name__}") from exc
            time.sleep(5 * (attempt + 1))
            continue
        if res.status_code in (429, 503) and not last:
            time.sleep(20 * (attempt + 1))  # rate limited: wait longer each time
            continue
        if res.status_code != 200:
            raise EmbeddingError(f"Embedding request failed with HTTP {res.status_code}")
        return res.json()
    raise EmbeddingError("Embedding request kept failing")


def _cache_key(text: str) -> str:
    normalised = " ".join(text.lower().split())
    return hashlib.sha256(f"{EMBEDDING_MODEL}:{DIMENSIONS}:{normalised}".encode("utf-8")).hexdigest()


def _read_cache() -> dict:
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}  # missing or damaged cache: start again, nothing depends on it


def _write_cache(cache: dict) -> None:
    try:
        tmp = _CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache), encoding="utf-8")
        os.replace(tmp, _CACHE_PATH)
    except OSError:
        pass  # a cache that cannot be saved only costs quota later


def embed_texts(texts: list[str], *, is_query: bool = False) -> list[list[float]]:
    """Embed texts in batches. Documents and questions use different task types."""
    if is_query and len(texts) == 1:
        key = _cache_key(texts[0])
        cache = _read_cache()
        if key in cache:
            return [cache[key]]
        vector = _embed_batches(texts, is_query=True)[0]
        cache[key] = vector
        _write_cache(cache)
        return [vector]
    return _embed_batches(texts, is_query=is_query)


def _embed_batches(texts: list[str], *, is_query: bool) -> list[list[float]]:
    task = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
    attempts = 1 if is_query else 8  # a user is waiting on a query: fail fast and let search fall back
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        payload = {
            "requests": [
                {
                    "model": f"models/{EMBEDDING_MODEL}",
                    "content": {"parts": [{"text": t}]},
                    "taskType": task,
                    "outputDimensionality": DIMENSIONS,
                }
                for t in batch
            ]
        }
        vectors.extend(item["values"] for item in _post_with_retry(payload, attempts)["embeddings"])
    return vectors
