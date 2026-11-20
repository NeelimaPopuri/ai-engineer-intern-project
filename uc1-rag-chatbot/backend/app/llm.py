"""Chat model call (Gemini). The rest of the app only sees `generate`, so the provider can change here."""

import time
from dataclasses import dataclass

import httpx

from .config import settings

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(RuntimeError):
    """The chat model could not be used."""


@dataclass(frozen=True)
class LLMReply:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    model: str


def generate(prompt: str) -> LLMReply:
    for attempt in range(3):
        last = attempt == 2
        try:
            res = httpx.post(
                URL.format(model=settings.gemini_model),
                headers={"x-goog-api-key": settings.gemini_api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.1},
                },
                timeout=60,
            )
        except httpx.TransportError as exc:  # dropped connection, DNS failure, timeout
            if last:
                raise LLMError(f"Model request could not reach the service: {type(exc).__name__}") from exc
            time.sleep(1.5 * (attempt + 1))
            continue
        if res.status_code in (429, 503) and not last:
            time.sleep(1.5 * (attempt + 1))
            continue
        break
    if res.status_code != 200:
        raise LLMError(f"Model request failed with HTTP {res.status_code}")
    body = res.json()
    try:
        text = "".join(p.get("text", "") for p in body["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        raise LLMError("Model returned no answer") from None
    usage = body.get("usageMetadata", {})
    return LLMReply(text.strip(), usage.get("promptTokenCount"), usage.get("candidatesTokenCount"), settings.gemini_model)
