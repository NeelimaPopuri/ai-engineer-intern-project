import logging

from anthropic import Anthropic, APIError
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("datafactz.hello")

app = FastAPI(title="DataFactZ Hello World", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

client = Anthropic(api_key=settings.anthropic_api_key)
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
        msg = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=500,
            messages=[{"role": "user", "content": body.prompt}],
        )
    except APIError as exc:
        log.error("LLM call failed: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The model provider returned an error") from exc
    text = "".join(b.text for b in msg.content if b.type == "text")
    return ChatResponse(reply=text, model=msg.model)
