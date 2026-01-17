"""Unified API key loading for all providers."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from random import shuffle
from typing import Callable, List, Optional

from src.config import (
    CEREBRAS_KEYS_FILE_PATH,
    OPENROUTER_KEYS_FILE,
    NVIDIA_KEYS_FILE,
    CANOPYWAVE_KEYS_FILE,
    BASETEN_KEYS_FILE,
    GOOGLE_GENAI_KEYS_FILE,
)

logger = logging.getLogger(__name__)


def _extract_api_key(data: list) -> List[str]:
    """Extract keys from list of dicts with 'api_key' field."""
    return [item["api_key"] for item in data if "api_key" in item]


def _extract_openrouter_key(data: list) -> List[str]:
    """Extract keys from OpenRouter's nested format."""
    return [
        item["data"]["key"]
        for item in data
        if "data" in item and "key" in item.get("data", {})
    ]


def _extract_flexible(data: list) -> List[str]:
    """Extract keys from either list of strings or list of dicts."""
    if not data:
        return []
    if isinstance(data[0], str):
        return data
    return _extract_api_key(data)


@dataclass
class KeyConfig:
    """Configuration for loading API keys for a provider."""

    path: Path
    extractor: Callable[[list], List[str]]


# Registry of key configurations for each provider
KEY_CONFIGS: dict[str, KeyConfig] = {
    "cerebras": KeyConfig(
        path=CEREBRAS_KEYS_FILE_PATH,
        extractor=_extract_api_key,
    ),
    "openrouter": KeyConfig(
        path=OPENROUTER_KEYS_FILE,
        extractor=_extract_openrouter_key,
    ),
    "nvidia": KeyConfig(
        path=NVIDIA_KEYS_FILE,
        extractor=_extract_flexible,
    ),
    "canopywave": KeyConfig(
        path=CANOPYWAVE_KEYS_FILE,
        extractor=_extract_flexible,
    ),
    "baseten": KeyConfig(
        path=BASETEN_KEYS_FILE,
        extractor=_extract_flexible,
    ),
    "google_genai": KeyConfig(
        path=GOOGLE_GENAI_KEYS_FILE,
        extractor=_extract_flexible,
    ),
}


async def load_keys(provider_name: str) -> List[str]:
    """
    Load and shuffle API keys for a provider.

    Args:
        provider_name: Name of the provider (e.g., 'cerebras', 'nvidia')

    Returns:
        List of API keys, shuffled for load balancing.
        Returns empty list if keys file not found or no keys extracted.
    """
    config = KEY_CONFIGS.get(provider_name)
    if not config:
        logger.warning(f"Unknown provider: {provider_name}")
        return []

    if not config.path.exists():
        logger.warning(f"{provider_name} keys file not found: {config.path}")
        return []

    try:
        with open(config.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        keys = config.extractor(data)

        if not keys:
            logger.warning(f"No {provider_name} API keys found in the file.")
            return []

        shuffle(keys)
        return keys

    except (json.JSONDecodeError, KeyError, TypeError) as error:
        logger.error(f"Error loading {provider_name} keys: {error}")
        return []
