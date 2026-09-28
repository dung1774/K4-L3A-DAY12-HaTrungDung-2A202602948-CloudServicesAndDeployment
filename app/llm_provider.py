"""LLM provider selector for the offline lab and optional OpenAI demo."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol, TypedDict

from openai import OpenAI

from utils.mock_llm import ask_llm

from .config import Settings, get_settings
from .logging_utils import log_event


class LLMResult(TypedDict):
    answer: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


class LLMProvider(Protocol):
    def ask(self, question: str, history: list[dict] | None = None) -> LLMResult:
        """Return the answer and usage data consumed by the /ask pipeline."""


class LLMProviderError(RuntimeError):
    """Safe error that may be returned to an API caller."""


class MockLLMProvider:
    """Adapter around the original deterministic, offline lab mock."""

    def ask(self, question: str, history: list[dict] | None = None) -> LLMResult:
        return ask_llm(question, history)  # type: ignore[return-value]


class OpenAILLMProvider:
    """Small server-side adapter for the OpenAI Responses API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        input_price_per_1m: float,
        output_price_per_1m: float,
        client: OpenAI | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
            )

        self.model = model
        self.input_price_per_1m = input_price_per_1m
        self.output_price_per_1m = output_price_per_1m
        self.client = client or OpenAI(api_key=api_key)

    def ask(self, question: str, history: list[dict] | None = None) -> LLMResult:
        messages = [
            {
                "role": turn.get("role", "user"),
                "content": str(turn.get("content", "")),
            }
            for turn in (history or [])
            if turn.get("role") in {"user", "assistant"}
        ]
        messages.append({"role": "user", "content": question})

        try:
            response = self.client.responses.create(
                model=self.model,
                input=messages,
            )
        except Exception as exc:
            # Chỉ log loại lỗi; không log exception text, headers hay credentials.
            log_event(
                "llm_provider_failed",
                level="error",
                provider="openai",
                error_type=type(exc).__name__,
            )
            raise LLMProviderError(
                "OpenAI service is temporarily unavailable. Please try again."
            ) from None

        answer = (response.output_text or "").strip()
        if not answer:
            raise LLMProviderError("OpenAI returned an empty response.")

        usage = getattr(response, "usage", None)
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        cost = (
            tokens_in * self.input_price_per_1m
            + tokens_out * self.output_price_per_1m
        ) / 1_000_000

        return {
            "answer": answer,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost, 8),
        }


def create_llm_provider(
    settings: Settings,
    *,
    openai_client: OpenAI | None = None,
) -> LLMProvider:
    """Create the configured provider without making a network request."""
    if settings.llm_provider == "mock":
        return MockLLMProvider()

    key = settings.openai_api_key
    if key is None or not key.get_secret_value().strip():
        raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    return OpenAILLMProvider(
        api_key=key.get_secret_value(),
        model=settings.openai_model,
        input_price_per_1m=settings.openai_input_price_per_1m,
        output_price_per_1m=settings.openai_output_price_per_1m,
        client=openai_client,
    )


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    return create_llm_provider(get_settings())
