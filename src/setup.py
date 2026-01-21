"""Provider initialization and configuration."""

import logging
from typing import List, Optional, Tuple

from src.config import ENABLE_GEMINI
from src.config.loader import (
    load_config,
    get_combiner_config,
    get_formatter_config,
    DefaultsConfig,
)
from src.providers.base import LLMProvider
from src.providers.registry import PROVIDER_REGISTRY, create_provider_instances

logger = logging.getLogger(__name__)


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

    # Create effective defaults by merging global defaults with generation settings
    effective_defaults = DefaultsConfig(
        timeout=config.defaults.timeout,
        temperature=config.defaults.temperature,
        max_tokens=config.defaults.max_tokens,
        max_retries=config.generation.max_retries or config.defaults.max_retries,
        json_parse_retries=config.generation.json_parse_retries or config.defaults.json_parse_retries,
        retry_delay=config.defaults.retry_delay,
        retry_min_wait=config.defaults.retry_min_wait,
        retry_max_wait=config.defaults.retry_max_wait,
    )

    active_providers: List[LLMProvider] = []
    combiner_provider: Optional[LLMProvider] = None
    formatter_provider: Optional[LLMProvider] = None

    # Initialize providers from registry
    for name, spec in PROVIDER_REGISTRY.items():
        cfg = config.providers.get(name)

        # Handle ENABLE_GEMINI env var for backward compatibility
        if name == "gemini_webapi" and ENABLE_GEMINI:
            if cfg is None:
                from src.config.loader import ProviderConfig
                cfg = ProviderConfig(enabled=True)
            elif not cfg.enabled:
                cfg = ProviderConfig(enabled=True)

        if not cfg or not cfg.enabled:
            continue

        try:
            instances = await create_provider_instances(
                name, spec, cfg,
                defaults=effective_defaults,
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

    if not active_providers and not combiner_provider:
        logger.error("No providers could be initialized.")

    return active_providers, combiner_provider, formatter_provider
