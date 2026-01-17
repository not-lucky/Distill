"""Google Antigravity LLM Provider (local OpenAI-compatible API)."""

from typing import Any, Dict

from src.providers.openai_compatible import OpenAICompatibleProvider


class GoogleAntigravityProvider(OpenAICompatibleProvider):
    """LLM Provider for Google's local OpenAI-compatible API (Gemini models)."""

    def __init__(self, model: str):
        super().__init__(
            model=model,
            base_url="http://127.0.0.1:8317/v1",
            api_keys=None,  # No API key needed for local
            timeout=900.0,
            max_retries=5,
            max_tokens=16384,
        )

    @property
    def name(self) -> str:
        return "llm2deck_google_antigravity"
