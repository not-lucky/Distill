"""Unified API key loading for all providers."""

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from random import shuffle
from typing import Callable, List, Optional

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


# Environment variable names for each provider (for backward compatibility)
ENV_VAR_NAMES = {
    "cerebras": "CEREBRAS_KEYS_FILE_PATH",
    "openrouter": "OPENROUTER_KEYS_FILE_PATH",
    "gemini": "GEMINI_CREDENTIALS_FILE_PATH",
    "nvidia": "NVIDIA_KEYS_FILE_PATH",
    "canopywave": "CANOPYWAVE_KEYS_FILE_PATH",
    "baseten": "BASETEN_KEYS_FILE_PATH",
    "google_genai": "GOOGLE_GENAI_KEYS_FILE_PATH",
}


@lru_cache(maxsize=1)
def _get_key_paths_from_config():
    """
    Get key paths config from config.yaml, cached for performance.

    Returns KeyPathsConfig or None if config cannot be loaded.
    """
    try:
        from src.config.loader import load_config
        config = load_config()
        return config.paths.key_paths
    except Exception:
        return None


def get_key_path(provider_name: str) -> Path:
    """
    Resolve key file path for a provider.

    Resolution order (highest to lowest priority):
    1. Environment variable (if set)
    2. config.yaml paths.key_paths.<provider>
    3. Default value

    Args:
        provider_name: Provider name (e.g., 'cerebras', 'nvidia', 'google_genai')

    Returns:
        Path to the key file.
    """
    # Default paths
    defaults = {
        "cerebras": "api_keys.json",
        "openrouter": "openrouter_apikeys.json",
        "gemini": "python3ds.json",
        "nvidia": "nvidia_keys.json",
        "canopywave": "canopywave_keys.json",
        "baseten": "baseten_keys.json",
        "google_genai": "google_genai_keys.json",
    }

    # 1. Check environment variable first (highest priority)
    env_var = ENV_VAR_NAMES.get(provider_name)
    if env_var:
        env_value = os.getenv(env_var)
        if env_value:
            return Path(env_value)

    # 2. Check config.yaml
    key_paths = _get_key_paths_from_config()
    if key_paths is not None:
        config_path = getattr(key_paths, provider_name, None)
        if config_path:
            return Path(config_path)

    # 3. Fall back to default
    return Path(defaults.get(provider_name, f"{provider_name}_keys.json"))


# Registry of key configurations for each provider
KEY_CONFIGS: dict[str, KeyConfig] = {
    "cerebras": KeyConfig(
        path=get_key_path("cerebras"),
        extractor=_extract_api_key,
    ),
    "openrouter": KeyConfig(
        path=get_key_path("openrouter"),
        extractor=_extract_openrouter_key,
    ),
    "nvidia": KeyConfig(
        path=get_key_path("nvidia"),
        extractor=_extract_flexible,
    ),
    "canopywave": KeyConfig(
        path=get_key_path("canopywave"),
        extractor=_extract_flexible,
    ),
    "baseten": KeyConfig(
        path=get_key_path("baseten"),
        extractor=_extract_flexible,
    ),
    "google_genai": KeyConfig(
        path=get_key_path("google_genai"),
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
