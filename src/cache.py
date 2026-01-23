"""Cache utilities for LLM response caching."""

import hashlib
import json
from typing import Any, Optional


def generate_cache_key(
    provider_name: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    json_schema: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Generate deterministic SHA256 cache key from request parameters.

    Args:
        provider_name: Name of the LLM provider (e.g., "cerebras")
        model: Model identifier (e.g., "llama3.1-70b")
        messages: Chat messages array
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        top_p: Nucleus sampling parameter
        json_schema: JSON schema for structured outputs
        **kwargs: Additional parameters that affect output

    Returns:
        64-character hex string (SHA256 hash)
    """
    payload: dict[str, Any] = {
        "v": "1",  # Cache version for future invalidation
        "provider": provider_name.lower(),
        "model": model.lower(),
        "messages": messages,
        "temperature": round(temperature, 2),
    }

    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if top_p is not None:
        payload["top_p"] = round(top_p, 2)
    if json_schema is not None:
        payload["json_schema"] = json_schema

    # Add any extra params that affect output
    for k in sorted(kwargs.keys()):
        if kwargs[k] is not None:
            payload[k] = kwargs[k]

    content = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
