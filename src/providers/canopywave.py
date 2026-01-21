"""Canopywave LLM Provider using OpenAI-compatible API."""

from typing import Iterator, Optional

from src.providers.openai_compatible import OpenAICompatibleProvider


class CanopywaveProvider(OpenAICompatibleProvider):
    """LLM Provider for Canopywave's OpenAI-compatible API."""

    def __init__(
        self,
        api_keys: Iterator[str],
        model: str,
        base_url: str = "https://api.xiaomimimo.com/v1",
        timeout: float = 900.0,
        temperature: float = 0.4,
        max_tokens: Optional[int] = 16384,
        max_retries: int = 5,
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
        )

    @property
    def name(self) -> str:
        return "llm2deck_canopywave"
