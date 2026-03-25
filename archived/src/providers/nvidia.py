"""NVIDIA LLM Provider using OpenAI-compatible API."""

from typing import Any, Dict, Iterator, Optional

from src.providers.openai_compatible import OpenAICompatibleProvider


class NvidiaProvider(OpenAICompatibleProvider):
    """LLM Provider for NVIDIA's API."""

    def __init__(
        self,
        api_keys: Iterator[str],
        model: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        timeout: float = 900.0,
        temperature: float = 0.4,
        max_tokens: Optional[int] = 16384,
        top_p: Optional[float] = 0.95,
        extra_params: Optional[Dict[str, Any]] = None,
        max_retries: int = 5,
        json_parse_retries: int = 3,
    ):
        # Merge default extra_body with config extra_params
        default_extra = {"extra_body": {"chat_template_kwargs": {"thinking": True}}}
        merged_extra = {**default_extra, **(extra_params or {})}

        super().__init__(
            model=model,
            base_url=base_url,
            api_keys=api_keys,
            timeout=timeout,
            temperature=temperature,
            max_retries=max_retries,
            json_parse_retries=json_parse_retries,
            max_tokens=max_tokens,
            top_p=top_p,
            extra_params=merged_extra,
        )

    @property
    def name(self) -> str:
        return "llm2deck_nvidia"
