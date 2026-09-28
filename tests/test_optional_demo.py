"""Tests for the optional real-OpenAI provider and tiny browser UI."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError


def test_default_provider_is_mock(monkeypatch):
    from app.config import Settings
    from app.llm_provider import MockLLMProvider, create_llm_provider

    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(_env_file=None)

    assert isinstance(create_llm_provider(settings), MockLLMProvider)


def test_openai_provider_requires_api_key(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValidationError, match="OPENAI_API_KEY is required"):
        Settings(_env_file=None)


def test_openai_provider_uses_history_and_usage(monkeypatch):
    from app.config import Settings
    from app.llm_provider import OpenAILLMProvider, create_llm_provider

    class FakeResponses:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(
                output_text="Câu trả lời thật (đã mock client)",
                usage=SimpleNamespace(input_tokens=100, output_tokens=50),
            )

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-placeholder")
    settings = Settings(_env_file=None)
    provider = create_llm_provider(settings, openai_client=fake_client)

    assert isinstance(provider, OpenAILLMProvider)
    result = provider.ask(
        "Câu mới",
        [{"role": "user", "content": "Câu cũ"}],
    )

    assert fake_client.responses.kwargs["model"] == "gpt-5-mini"
    assert fake_client.responses.kwargs["input"][-1]["content"] == "Câu mới"
    assert result == {
        "answer": "Câu trả lời thật (đã mock client)",
        "tokens_in": 100,
        "tokens_out": 50,
        "cost_usd": 0.000125,
    }


def test_openai_error_does_not_leak_secret(monkeypatch, capsys):
    from app.config import Settings
    from app.llm_provider import LLMProviderError, create_llm_provider

    secret = "unit-test-secret-that-must-not-leak"

    class FailingResponses:
        def create(self, **_kwargs):
            raise RuntimeError(f"provider failed with {secret}")

    fake_client = SimpleNamespace(responses=FailingResponses())
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    provider = create_llm_provider(
        Settings(_env_file=None),
        openai_client=fake_client,
    )

    with pytest.raises(LLMProviderError) as error:
        provider.ask("hello")

    assert secret not in str(error.value)
    assert secret not in capsys.readouterr().out


def test_chat_ui_is_public_and_contains_no_openai_secret(client):
    response = client.get("/")
    javascript = client.get("/static/app.js")

    assert response.status_code == 200
    assert javascript.status_code == 200
    assert "Day 12 AI Chat Demo" in response.text
    assert "Access Key" in response.text
    assert "OPENAI_API_KEY" not in response.text
    assert "OPENAI_API_KEY" not in javascript.text
