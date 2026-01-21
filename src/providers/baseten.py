"""Baseten LLM Provider using OpenAI-compatible API."""

from typing import Iterator

from src.providers.openai_compatible import OpenAICompatibleProvider


class BasetenProvider(OpenAICompatibleProvider):
    """LLM Provider for Baseten's API."""

    def __init__(self, api_keys: Iterator[str], model: str, max_retries: int = 3, json_parse_retries: int = 3):
        super().__init__(
            model=model,
            base_url="https://inference.baseten.co/v1",
            api_keys=api_keys,
            timeout=120.0,
            max_retries=max_retries,
            json_parse_retries=json_parse_retries,
            strip_json_markers=False,  # Baseten doesn't wrap in markdown
        )

    @property
    def name(self) -> str:
        return "llm2deck_baseten"
