import os

os.environ.setdefault("APP_API_KEY", "test-app-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import httpx
import pytest

from app import llm


class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body or {}

    def json(self):
        return self._body


OK = FakeResponse(200, {
    "candidates": [{"content": {"parts": [{"text": "An answer [1]."}]}}],
    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 4},
})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


def _script(monkeypatch, steps):
    calls = iter(steps)

    def fake_post(*args, **kwargs):
        step = next(calls)
        if isinstance(step, Exception):
            raise step
        return step

    monkeypatch.setattr(llm.httpx, "post", fake_post)


def test_good_reply_is_parsed(monkeypatch):
    _script(monkeypatch, [OK])
    reply = llm.generate("question")
    assert (reply.text, reply.input_tokens, reply.output_tokens) == ("An answer [1].", 10, 4)


def test_dropped_connection_is_retried(monkeypatch):
    _script(monkeypatch, [httpx.RemoteProtocolError("Server disconnected"), OK])
    assert llm.generate("question").text == "An answer [1]."


def test_repeated_network_failure_becomes_llm_error_not_a_crash(monkeypatch):
    _script(monkeypatch, [httpx.ConnectError("down")] * 3)
    with pytest.raises(llm.LLMError):
        llm.generate("question")


def test_overload_is_retried_then_reported(monkeypatch):
    _script(monkeypatch, [FakeResponse(503)] * 3)
    with pytest.raises(llm.LLMError):
        llm.generate("question")
