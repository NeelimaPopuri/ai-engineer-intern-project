"""Chat model call (Gemini). The rest of the app only sees `generate`, so the provider can change here.

If the main model is overloaded or gone, the call moves to a fallback model, so a busy moment on
the provider's side does not become an error on the user's screen. The reply says which model
actually answered, so cost and quality can be traced.
"""

import time
from dataclasses import dataclass

import httpx

from .config import settings

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Worth trying again, then trying another model: the provider is busy or briefly broken.
RETRYABLE = {429, 500, 502, 503, 504}
# The model name is no longer served: go straight to the next model.
MODEL_GONE = {404}


class LLMError(RuntimeError):
    """The chat model could not be used."""


@dataclass(frozen=True)
class LLMReply:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    model: str


def _models() -> list[str]:
    fallback = settings.gemini_fallback_model
    return [settings.gemini_model] + ([fallback] if fallback and fallback != settings.gemini_model else [])


def _parse(res: httpx.Response, model: str) -> LLMReply:
    body = res.json()
    try:
        text = "".join(p.get("text", "") for p in body["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        raise LLMError("Model returned no answer") from None
    usage = body.get("usageMetadata", {})
    return LLMReply(text.strip(), usage.get("promptTokenCount"), usage.get("candidatesTokenCount"), model)


def generate(prompt: str) -> LLMReply:
    models = _models()
    last_problem = "no attempt was made"
    for position, model in enumerate(models):
        # When a fallback exists, give up on a struggling model sooner: the user is waiting.
        attempts = 2 if position < len(models) - 1 else 3
        for attempt in range(attempts):
            try:
                res = httpx.post(
                    URL.format(model=model),
                    headers={"x-goog-api-key": settings.gemini_api_key},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.1},
                    },
                    timeout=60,
                )
            except httpx.TransportError as exc:  # dropped connection, DNS failure, timeout
                last_problem = f"{model} could not be reached ({type(exc).__name__})"
                time.sleep(1.5 * (attempt + 1))
                continue
            if res.status_code == 200:
                return _parse(res, model)
            if res.status_code in MODEL_GONE:
                last_problem = f"{model} is not available (HTTP {res.status_code})"
                break
            if res.status_code in RETRYABLE:
                last_problem = f"{model} is busy (HTTP {res.status_code})"
                time.sleep(1.5 * (attempt + 1))
                continue
            # A bad request or a rejected key will fail on any model: say so now.
            raise LLMError(f"Model request failed with HTTP {res.status_code}")
    raise LLMError(f"Model request failed: {last_problem}")
