"""Provider initialization and configuration."""

import json
import logging
from typing import List, Optional, Tuple

from gemini_webapi import GeminiClient

from src.config import GEMINI_CREDENTIALS_FILE, ENABLE_GEMINI
from src.config.loader import (
    load_config,
    get_combiner_config,
    get_formatter_config,
    CombinerConfig,
    FormatterConfig,
)
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


async def initialize_providers() -> Tuple[List[LLMProvider], Optional[LLMProvider], Optional[LLMProvider]]:
    """
    Initialize and return configured LLM providers with combiner and formatter separated.

    Reads configuration from config.yaml to determine which providers
    are enabled and their settings. If a combiner is configured in
    generation.combiner, it will be created separately. If a formatter
    is configured in generation.formatter, it will also be created separately.

    Returns:
        Tuple of (generator_providers, combiner_provider, formatter_provider).
        combiner_provider is None if not explicitly configured (first provider will be used).
        formatter_provider is None if not configured (combiner must output valid JSON).

    Raises:
        ConfigurationError: If combiner/formatter config references invalid provider/model.
    """
    config = load_config()
    combiner_cfg = get_combiner_config(config)  # Validates combiner config
    formatter_cfg = get_formatter_config(config)  # Validates formatter config

    # Get retry configuration from generation settings
    max_retries = config.generation.max_retries
    json_parse_retries = config.generation.json_parse_retries

    active_providers: List[LLMProvider] = []
    combiner_provider: Optional[LLMProvider] = None
    formatter_provider: Optional[LLMProvider] = None

    # Initialize providers from registry
    for name, spec in PROVIDER_REGISTRY.items():
        cfg = config.providers.get(name)
        if not cfg or not cfg.enabled:
            continue

        try:
            instances = await create_provider_instances(
                name, spec, cfg,
                max_retries=max_retries,
                json_parse_retries=json_parse_retries,
            )

            for instance in instances:
                is_combiner = False
                is_formatter = False

                # Check if this instance is the combiner
                if combiner_cfg and name == combiner_cfg.provider:
                    if instance.model == combiner_cfg.model or (
                        len(instances) == 1 and not cfg.models
                    ):
                        combiner_provider = instance
                        is_combiner = True

                # Check if this instance is the formatter
                if formatter_cfg and name == formatter_cfg.provider:
                    if instance.model == formatter_cfg.model or (
                        len(instances) == 1 and not cfg.models
                    ):
                        formatter_provider = instance
                        is_formatter = True

                # Determine if instance should be added to active generators
                should_add = True
                if is_combiner and not combiner_cfg.also_generate:
                    should_add = False
                if is_formatter and not formatter_cfg.also_generate:
                    should_add = False

                if should_add:
                    active_providers.append(instance)

        except Exception as error:
            logger.warning(f"Error loading {name} provider: {error}")

    # Gemini Web API (reverse-engineered) - special case due to different auth
    gemini_cfg = config.providers.get("gemini_webapi")
    if (gemini_cfg and gemini_cfg.enabled) or ENABLE_GEMINI:
        try:
            gemini_clients = await load_gemini_clients()
            gemini_providers = [GeminiProvider(client) for client in gemini_clients]

            for i, provider in enumerate(gemini_providers):
                is_combiner = False
                is_formatter = False

                # First gemini provider can be combiner/formatter
                if combiner_cfg and combiner_cfg.provider == "gemini_webapi" and i == 0:
                    combiner_provider = provider
                    is_combiner = True

                if formatter_cfg and formatter_cfg.provider == "gemini_webapi" and i == 0:
                    formatter_provider = provider
                    is_formatter = True

                should_add = True
                if is_combiner and not combiner_cfg.also_generate:
                    should_add = False
                if is_formatter and not formatter_cfg.also_generate:
                    should_add = False

                if should_add:
                    active_providers.append(provider)

        except Exception as error:
            logger.warning(f"Could not load Gemini clients: {error}")

    if not active_providers and not combiner_provider:
        logger.error("No providers could be initialized.")

    return active_providers, combiner_provider, formatter_provider
