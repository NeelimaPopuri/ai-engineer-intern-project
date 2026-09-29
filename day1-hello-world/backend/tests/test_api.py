import os
from types import SimpleNamespace

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("APP_API_KEY", "test-app-key")

import httpx
import pytest
from anthropic import APIConnectionError
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)
HEADERS = {"X-API-Key": os.environ["APP_API_KEY"]}


def test_health_returns_ok():
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_chat_requires_api_key():
    assert client.post("/api/v1/chat", json={"prompt": "hi"}).status_code == 401


def test_chat_rejects_empty_prompt():
    assert client.post("/api/v1/chat", json={"prompt": ""}, headers=HEADERS).status_code == 422


def test_chat_returns_model_reply(monkeypatch):
    fake = SimpleNamespace(model="test-model", content=[SimpleNamespace(type="text", text="Hello")])
    monkeypatch.setattr(main.client.messages, "create", lambda **_: fake)
    res = client.post("/api/v1/chat", json={"prompt": "hi"}, headers=HEADERS)
    assert res.status_code == 200
    assert res.json() == {"reply": "Hello", "model": "test-model"}


def test_chat_maps_provider_failure_to_502(monkeypatch):
    def boom(**_):
        raise APIConnectionError(request=httpx.Request("POST", "http://x"))

    monkeypatch.setattr(main.client.messages, "create", boom)
    assert client.post("/api/v1/chat", json={"prompt": "hi"}, headers=HEADERS).status_code == 502
