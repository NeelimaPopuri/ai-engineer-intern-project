import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("APP_API_KEY", "test-app-key")

import httpx
import pytest
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


def _stub_post(monkeypatch, fn):
    monkeypatch.setattr(main.httpx, "post", fn)


def test_chat_returns_model_reply(monkeypatch):
    body = {"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]}
    _stub_post(monkeypatch, lambda *a, **k: httpx.Response(200, json=body, request=httpx.Request("POST", "http://x")))
    res = client.post("/api/v1/chat", json={"prompt": "hi"}, headers=HEADERS)
    assert res.status_code == 200
    assert res.json() == {"reply": "Hello", "model": main.settings.gemini_model}


def test_chat_maps_provider_failure_to_502(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("down", request=httpx.Request("POST", "http://x"))

    _stub_post(monkeypatch, boom)
    assert client.post("/api/v1/chat", json={"prompt": "hi"}, headers=HEADERS).status_code == 502


def test_chat_reports_bad_key(monkeypatch):
    req = httpx.Request("POST", "http://x")
    _stub_post(monkeypatch, lambda *a, **k: httpx.Response(400, text="API key not valid", request=req))
    res = client.post("/api/v1/chat", json={"prompt": "hi"}, headers=HEADERS)
    assert res.status_code == 502
    assert "GEMINI_API_KEY" in res.json()["detail"]
