"""Factory for Gemini WebAPI provider initialization."""

import json
import logging
from typing import List

from src.config.keys import get_key_path
from src.config.loader import DefaultsConfig, ProviderConfig
from src.providers.base import LLMProvider

logger = logging.getLogger(__name__)


async def create_gemini_providers(
    cfg: ProviderConfig,
    defaults: DefaultsConfig,
) -> List[LLMProvider]:
    """
    Factory function for creating Gemini WebAPI providers.

    Handles the special cookie-based authentication and async initialization
    required by the gemini_webapi library.

    Args:
        cfg: Provider configuration from config.yaml.
        defaults: Default configuration for fallback values.

    Returns:
        List of GeminiProvider instances (one per credential set).
    """
    from gemini_webapi import GeminiClient

    from src.providers.gemini import GeminiProvider

    credentials_file = get_key_path("gemini")

    if not credentials_file.exists():
        logger.warning(f"Gemini credentials file not found: {credentials_file}")
        return []

    try:
        with credentials_file.open("r", encoding="utf-8") as f:
            credentials_list = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load Gemini credentials: {e}")
        return []

    providers: List[LLMProvider] = []
    for credentials in credentials_list:
        try:
            client = GeminiClient(
                credentials["Secure_1PSID"],
                credentials["Secure_1PSIDTS"],
                proxy=None,
            )
            await client.init(auto_refresh=True)
            providers.append(GeminiProvider(client))
        except Exception as error:
            logger.error(f"Failed to initialize Gemini client: {error}")

    if not providers:
        logger.warning("No Gemini clients could be initialized")

    return providers
