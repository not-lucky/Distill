"""Baseten LLM Provider using OpenAI-compatible API."""

from typing import Iterator, Optional

from src.providers.openai_compatible import OpenAICompatibleProvider


class BasetenProvider(OpenAICompatibleProvider):
    """LLM Provider for Baseten's API."""

    def __init__(
        self,
        api_keys: Iterator[str],
        model: str,
        base_url: str = "https://inference.baseten.co/v1",
        timeout: float = 120.0,
        temperature: float = 0.4,
        max_tokens: Optional[int] = None,
        strip_json_markers: bool = False,
        max_retries: int = 3,
        json_parse_retries: int = 3,
    ):
        super().__init__(
            model=model,
            base_url=base_url,
            api_keys=api_keys,
            timeout=timeout,
            temperature=temperature,
            max_retries=max_retries,
            json_parse_retries=json_parse_retries,
            max_tokens=max_tokens,
            strip_json_markers=strip_json_markers,
        )

    @property
    def name(self) -> str:
        return "llm2deck_baseten"
