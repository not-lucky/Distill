"""Provider initialization and configuration."""

import json
import logging
from typing import List, Optional, Tuple

from gemini_webapi import GeminiClient

from src.config import GEMINI_CREDENTIALS_FILE, ENABLE_GEMINI
from src.config.loader import load_config, get_combiner_config, CombinerConfig
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


async def initialize_providers() -> Tuple[List[LLMProvider], Optional[LLMProvider]]:
    """
    Initialize and return configured LLM providers with combiner separated.

    Reads configuration from config.yaml to determine which providers
    are enabled and their settings. If a combiner is configured in
    generation.combiner, it will be created separately.

    Returns:
        Tuple of (generator_providers, combiner_provider).
        combiner_provider is None if not explicitly configured (first provider will be used).

    Raises:
        ConfigurationError: If combiner config references invalid provider/model.
    """
    config = load_config()
    combiner_cfg = get_combiner_config(config)  # Validates combiner config

    active_providers: List[LLMProvider] = []
    combiner_provider: Optional[LLMProvider] = None

    # Initialize providers from registry
    for name, spec in PROVIDER_REGISTRY.items():
        cfg = config.providers.get(name)
        if not cfg or not cfg.enabled:
            continue

        try:
            instances = await create_provider_instances(name, spec, cfg)

            # Check if this provider contains the combiner model
            if combiner_cfg and name == combiner_cfg.provider:
                # Find the combiner instance by model name
                combiner_found = False
                for instance in instances:
                    if instance.model == combiner_cfg.model:
                        combiner_provider = instance
                        combiner_found = True
                        if combiner_cfg.also_generate:
                            # Keep combiner in generators too
                            active_providers.append(instance)
                    else:
                        active_providers.append(instance)

                # For single-model providers, the instance is the combiner
                if not combiner_found and len(instances) == 1:
                    combiner_provider = instances[0]
                    if combiner_cfg.also_generate:
                        active_providers.append(instances[0])
            else:
                active_providers.extend(instances)
        except Exception as error:
            logger.warning(f"Error loading {name} provider: {error}")

    # Gemini Web API (reverse-engineered) - special case due to different auth
    gemini_cfg = config.providers.get("gemini_webapi")
    if (gemini_cfg and gemini_cfg.enabled) or ENABLE_GEMINI:
        try:
            gemini_clients = await load_gemini_clients()
            gemini_providers = [GeminiProvider(client) for client in gemini_clients]

            if combiner_cfg and combiner_cfg.provider == "gemini_webapi" and gemini_providers:
                combiner_provider = gemini_providers[0]
                if combiner_cfg.also_generate:
                    active_providers.append(gemini_providers[0])
                active_providers.extend(gemini_providers[1:])
            else:
                active_providers.extend(gemini_providers)
        except Exception as error:
            logger.warning(f"Could not load Gemini clients: {error}")

    if not active_providers and not combiner_provider:
        logger.error("No providers could be initialized.")

    return active_providers, combiner_provider
