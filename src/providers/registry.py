"""Provider registry for dynamic provider initialization."""

import itertools
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterator, List, Optional, Type, cast

from src.config.keys import load_keys
from src.config.loader import DefaultsConfig, ProviderConfig
from src.providers.base import LLMProvider
from src.providers.baseten import BasetenProvider
from src.providers.canopywave import CanopywaveProvider
from src.providers.cerebras import CerebrasProvider
from src.providers.g4f_provider import G4FProvider
from src.providers.gemini import GeminiProvider
from src.providers.gemini_factory import create_gemini_providers
from src.providers.google_antigravity import GoogleAntigravityProvider
from src.providers.google_genai import GoogleGenAIProvider
from src.providers.nvidia import NvidiaProvider
from src.providers.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)

# Type alias for custom factory functions
ProviderFactory = Callable[[ProviderConfig, DefaultsConfig], Awaitable[List[LLMProvider]]]


# Default base URLs for OpenAI-compatible providers
DEFAULT_BASE_URLS: Dict[str, str] = {
    "baseten": "https://inference.baseten.co/v1",
    "canopywave": "https://api.xiaomimimo.com/v1",
    "google_antigravity": "http://127.0.0.1:8317/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


@dataclass
class ProviderSpec:
    """Specification for how to initialize a provider."""

    provider_class: Type[LLMProvider]
    key_name: Optional[str] = None  # None for providers that don't need API keys
    extra_params: List[str] = field(default_factory=list)  # Config fields to pass
    multi_model: bool = False  # True if provider creates multiple instances from models list
    no_keys: bool = False  # True if provider doesn't need any keys
    uses_base_url: bool = False  # True for OpenAI-compatible providers that accept base_url
    factory: Optional[ProviderFactory] = None  # Custom factory for providers with special init


# Registry mapping config names to provider specifications
PROVIDER_REGISTRY: Dict[str, ProviderSpec] = {
    "cerebras": ProviderSpec(
        provider_class=CerebrasProvider,
        key_name="cerebras",
        extra_params=["reasoning_effort"],
    ),
    "openrouter": ProviderSpec(
        provider_class=OpenRouterProvider,
        key_name="openrouter",
        uses_base_url=True,
    ),
    "nvidia": ProviderSpec(
        provider_class=NvidiaProvider,
        key_name="nvidia",
        extra_params=["top_p", "extra_params"],
        uses_base_url=True,
    ),
    "g4f": ProviderSpec(
        provider_class=G4FProvider,
        no_keys=True,
        extra_params=["provider_name"],
    ),
    "canopywave": ProviderSpec(
        provider_class=CanopywaveProvider,
        key_name="canopywave",
        uses_base_url=True,
    ),
    "baseten": ProviderSpec(
        provider_class=BasetenProvider,
        key_name="baseten",
        extra_params=["strip_json_markers"],
        uses_base_url=True,
    ),
    "google_genai": ProviderSpec(
        provider_class=GoogleGenAIProvider,
        key_name="google_genai",
        extra_params=["thinking_level"],
    ),
    "google_antigravity": ProviderSpec(
        provider_class=GoogleAntigravityProvider,
        no_keys=True,
        multi_model=True,
        uses_base_url=True,
    ),
    "gemini_webapi": ProviderSpec(
        provider_class=GeminiProvider,
        no_keys=True,
        factory=create_gemini_providers,
    ),
}


async def create_provider_instances(
    name: str,
    spec: ProviderSpec,
    cfg: ProviderConfig,
    defaults: DefaultsConfig,
) -> List[LLMProvider]:
    """
    Create provider instance(s) based on the spec and config.

    Args:
        name: Provider name from config
        spec: Provider specification from registry
        cfg: Provider configuration from config.yaml
        defaults: Default configuration for fallback values

    Returns:
        List of provider instances (usually 1, but can be multiple for multi_model)
    """
    # Use custom factory if provided (for providers with special init requirements)
    if spec.factory is not None:
        return await spec.factory(cfg, defaults)

    # Get effective values using defaults
    effective_timeout = cfg.get_effective_timeout(defaults)
    effective_temperature = cfg.get_effective_temperature(defaults)
    effective_max_tokens = cfg.get_effective_max_tokens(defaults)
    max_retries = defaults.max_retries
    json_parse_retries = defaults.json_parse_retries

    # Handle multi-model providers (e.g., google_antigravity)
    if spec.multi_model:
        base_url = cfg.base_url or DEFAULT_BASE_URLS.get(name, "")
        # Cast provider_class to Any to allow dynamic kwargs
        provider_cls = cast(Any, spec.provider_class)
        return [
            provider_cls(
                model=model,
                base_url=base_url,
                timeout=effective_timeout,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
                max_retries=max_retries,
                json_parse_retries=json_parse_retries,
            )
            for model in cfg.models
        ]

    # Build kwargs for provider instantiation
    kwargs: Dict[str, Any] = {}

    # Add retry configuration
    kwargs["max_retries"] = max_retries
    kwargs["json_parse_retries"] = json_parse_retries

    # Load API keys if required
    if spec.key_name:
        keys = await load_keys(spec.key_name)
        if not keys:
            logger.warning(f"No API keys found for {name}")
            return []
        kwargs["api_keys"] = itertools.cycle(keys)

    # Add model if provider uses single model
    if cfg.model:
        kwargs["model"] = cfg.model

    # Add base_url, timeout, temperature for OpenAI-compatible providers
    if spec.uses_base_url:
        kwargs["base_url"] = cfg.base_url or DEFAULT_BASE_URLS.get(name, "")
        kwargs["timeout"] = effective_timeout
        kwargs["temperature"] = effective_temperature
        if effective_max_tokens is not None:
            kwargs["max_tokens"] = effective_max_tokens

    # Add extra parameters from config
    for param in spec.extra_params:
        value = getattr(cfg, param, None)
        if value is not None:
            kwargs[param] = value

    return [spec.provider_class(**kwargs)]
