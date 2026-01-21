"""Google Antigravity LLM Provider (local OpenAI-compatible API)."""

from typing import Any, Dict, Optional

from src.providers.openai_compatible import OpenAICompatibleProvider


class GoogleAntigravityProvider(OpenAICompatibleProvider):
    """LLM Provider for Google's local OpenAI-compatible API (Gemini models)."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:8317/v1",
        timeout: float = 900.0,
        temperature: float = 0.4,
        max_tokens: Optional[int] = 16384,
        max_retries: int = 5,
        json_parse_retries: int = 3,
    ):
        super().__init__(
            model=model,
            base_url=base_url,
            api_keys=None,  # No API key needed for local
            timeout=timeout,
            temperature=temperature,
            max_retries=max_retries,
            json_parse_retries=json_parse_retries,
            max_tokens=max_tokens,
        )

    @property
    def name(self) -> str:
        return "llm2deck_google_antigravity"
