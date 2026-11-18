import logging
import time

import httpx
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("datafactz.hello")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

app = FastAPI(title="DataFactZ Hello World", version="0.1.0")
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


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    model: str


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
def chat(body: ChatRequest) -> ChatResponse:
    try:
        for attempt in range(3):
            res = httpx.post(
                GEMINI_URL.format(model=settings.gemini_model),
                headers={"x-goog-api-key": settings.gemini_api_key},
                json={
                    "contents": [{"parts": [{"text": body.prompt}]}],
                    "generationConfig": {"maxOutputTokens": 500},
                },
                timeout=30,
            )
            if res.status_code not in (429, 503) or attempt == 2:
                break
            time.sleep(1.5 * (attempt + 1))
        res.raise_for_status()
    except httpx.HTTPStatusError as exc:
        log.error("LLM call failed: %s %s", exc.response.status_code, exc.response.text)
        if exc.response.status_code in (400, 401, 403):
            detail = "The server's Gemini API key is invalid. Check GEMINI_API_KEY in .env and restart the backend."
        else:
            detail = "The model provider returned an error"
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail) from exc
    except httpx.HTTPError as exc:
        log.error("LLM call failed: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The model provider returned an error") from exc
    parts = (res.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    return ChatResponse(reply=text, model=settings.gemini_model)
