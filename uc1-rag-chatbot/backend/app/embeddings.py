"""Text to vector, through the Gemini embedding API. Everything else calls `embed_texts`,
so swapping the provider (for example Azure OpenAI) changes this one file."""

import time

import httpx

from .config import settings

EMBEDDING_MODEL = "gemini-embedding-001"
DIMENSIONS = 768
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
BATCH_SIZE = 50


class EmbeddingError(RuntimeError):
    """The embedding service could not be used."""


def _post_with_retry(payload: dict, attempts: int = 8) -> dict:
    for attempt in range(attempts):
        res = httpx.post(
            URL.format(model=EMBEDDING_MODEL),
            headers={"x-goog-api-key": settings.gemini_api_key},
            json=payload,
            timeout=60,
        )
        if res.status_code in (429, 503) and attempt < attempts - 1:
            time.sleep(20 * (attempt + 1))  # rate limited: wait longer each time
            continue
        if res.status_code != 200:
            raise EmbeddingError(f"Embedding request failed with HTTP {res.status_code}")
        return res.json()
    raise EmbeddingError("Embedding request kept failing")


def embed_texts(texts: list[str], *, is_query: bool = False) -> list[list[float]]:
    """Embed texts in batches. Documents and questions use different task types."""
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
