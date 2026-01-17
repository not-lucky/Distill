"""OpenRouter LLM Provider using OpenAI-compatible API."""

from typing import Iterator

from src.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """LLM Provider for OpenRouter's API."""

    def __init__(self, api_keys: Iterator[str], model: str):
        super().__init__(
            model=model,
            base_url="https://openrouter.ai/api/v1",
            api_keys=api_keys,
            timeout=120.0,
            max_retries=3,
        )

    @property
    def name(self) -> str:
        return "llm2deck_openrouter"
