"""Canopywave LLM Provider using OpenAI-compatible API."""

from typing import Iterator

from src.providers.openai_compatible import OpenAICompatibleProvider


class CanopywaveProvider(OpenAICompatibleProvider):
    """LLM Provider for Canopywave's OpenAI-compatible API."""

    def __init__(self, api_keys: Iterator[str], model: str, max_retries: int = 5, json_parse_retries: int = 3):
        super().__init__(
            model=model,
            base_url="https://api.xiaomimimo.com/v1",
            api_keys=api_keys,
            timeout=900.0,
            max_retries=max_retries,
            json_parse_retries=json_parse_retries,
            max_tokens=16384,
        )

    @property
    def name(self) -> str:
        return "llm2deck_canopywave"
