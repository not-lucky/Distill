"""Provider initialization and configuration."""

import json
import logging
from typing import List

from gemini_webapi import GeminiClient

from src.config import GEMINI_CREDENTIALS_FILE, ENABLE_GEMINI
from src.config.loader import load_config
from src.providers.base import LLMProvider
from src.providers.gemini import GeminiProvider
from src.providers.registry import PROVIDER_REGISTRY, create_provider_instances

logger = logging.getLogger(__name__)


async def load_gemini_clients() -> List[GeminiClient]:
    """Load and initialize Gemini web API clients."""
    if not GEMINI_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"Credentials file not found: {GEMINI_CREDENTIALS_FILE}")

    with GEMINI_CREDENTIALS_FILE.open("r", encoding="utf-8") as f:
        credentials_list = json.load(f)

    clients = []
    for credentials in credentials_list:
        try:
            client = GeminiClient(
                credentials["Secure_1PSID"],
                credentials["Secure_1PSIDTS"],
                proxy=None,
            )
            await client.init(auto_refresh=True)
            clients.append(client)
        except Exception as error:
            logger.error(f"Failed to initialize Gemini client: {error}")

    return clients


async def initialize_providers() -> List[LLMProvider]:
    """
    Initialize and return a list of configured LLM providers.

    Reads configuration from config.yaml to determine which providers
    are enabled and their settings.
    """
    config = load_config()
    active_providers: List[LLMProvider] = []

    # Initialize providers from registry
    for name, spec in PROVIDER_REGISTRY.items():
        cfg = config.providers.get(name)
        if not cfg or not cfg.enabled:
            continue

        try:
            instances = await create_provider_instances(name, spec, cfg)
            active_providers.extend(instances)
        except Exception as error:
            logger.warning(f"Error loading {name} provider: {error}")

    # Gemini Web API (reverse-engineered) - special case due to different auth
    gemini_cfg = config.providers.get("gemini_webapi")
    if (gemini_cfg and gemini_cfg.enabled) or ENABLE_GEMINI:
        try:
            gemini_clients = await load_gemini_clients()
            for client in gemini_clients:
                active_providers.append(GeminiProvider(client))
        except Exception as error:
            logger.warning(f"Could not load Gemini clients: {error}")

    if not active_providers:
        logger.error("No providers could be initialized.")

    return active_providers
