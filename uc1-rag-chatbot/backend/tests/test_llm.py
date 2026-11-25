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
    monkeypatch.setattr(llm.settings, "gemini_fallback_model", "")
    _script(monkeypatch, [httpx.ConnectError("down")] * 3)
    with pytest.raises(llm.LLMError):
        llm.generate("question")


def test_overload_is_retried_then_reported_when_there_is_no_fallback(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_fallback_model", "")
    _script(monkeypatch, [FakeResponse(503)] * 3)
    with pytest.raises(llm.LLMError):
        llm.generate("question")


def test_overloaded_main_model_hands_over_to_the_fallback(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_model", "main-model")
    monkeypatch.setattr(llm.settings, "gemini_fallback_model", "backup-model")
    _script(monkeypatch, [FakeResponse(503), FakeResponse(503), OK])
    reply = llm.generate("question")
    assert reply.text == "An answer [1]." and reply.model == "backup-model"  # the reply names who answered


def test_a_retired_main_model_goes_straight_to_the_fallback(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_model", "main-model")
    monkeypatch.setattr(llm.settings, "gemini_fallback_model", "backup-model")
    _script(monkeypatch, [FakeResponse(404), OK])
    assert llm.generate("question").model == "backup-model"


def test_a_rejected_key_does_not_waste_time_on_the_fallback(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_model", "main-model")
    monkeypatch.setattr(llm.settings, "gemini_fallback_model", "backup-model")
    _script(monkeypatch, [FakeResponse(403)])  # a second call would raise StopIteration
    with pytest.raises(llm.LLMError):
        llm.generate("question")


def test_both_models_busy_gives_a_clean_error(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_model", "main-model")
    monkeypatch.setattr(llm.settings, "gemini_fallback_model", "backup-model")
    _script(monkeypatch, [FakeResponse(503)] * 5)
    with pytest.raises(llm.LLMError):
        llm.generate("question")


def test_main_model_is_used_when_it_works(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_model", "main-model")
    monkeypatch.setattr(llm.settings, "gemini_fallback_model", "backup-model")
    _script(monkeypatch, [OK])
    assert llm.generate("question").model == "main-model"
