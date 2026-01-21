"""NVIDIA LLM Provider using OpenAI-compatible API."""

from typing import Any, Dict, Iterator, Optional

from src.providers.openai_compatible import OpenAICompatibleProvider


class NvidiaProvider(OpenAICompatibleProvider):
    """LLM Provider for NVIDIA's API."""

    def __init__(
        self,
        api_keys: Iterator[str],
        model: str,
        timeout: float = 900.0,
        max_retries: int = 5,
        json_parse_retries: int = 3,
    ):
        super().__init__(
            model=model,
            base_url="https://integrate.api.nvidia.com/v1",
            api_keys=api_keys,
            timeout=timeout,
            max_retries=max_retries,
            json_parse_retries=json_parse_retries,
            max_tokens=16384,
        )

    @property
    def name(self) -> str:
        return "llm2deck_nvidia"

    def _get_extra_request_params(self) -> Dict[str, Any]:
        return {
            "top_p": 0.95,
            "extra_body": {"chat_template_kwargs": {"thinking": True}},
        }
