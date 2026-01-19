"""Provider registry for dynamic provider initialization."""

import itertools
import logging
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Type

from src.config.keys import load_keys
from src.config.loader import ProviderConfig
from src.providers.base import LLMProvider
from src.providers.baseten import BasetenProvider
from src.providers.canopywave import CanopywaveProvider
from src.providers.cerebras import CerebrasProvider
from src.providers.g4f_provider import G4FProvider
from src.providers.google_antigravity import GoogleAntigravityProvider
from src.providers.google_genai import GoogleGenAIProvider
from src.providers.nvidia import NvidiaProvider
from src.providers.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


@dataclass
class ProviderSpec:
    """Specification for how to initialize a provider."""

    provider_class: Type[LLMProvider]
    key_name: Optional[str] = None  # None for providers that don't need API keys
    extra_params: List[str] = field(default_factory=list)  # Config fields to pass
    multi_model: bool = False  # True if provider creates multiple instances from models list
    no_keys: bool = False  # True if provider doesn't need any keys


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
    ),
    "nvidia": ProviderSpec(
        provider_class=NvidiaProvider,
        key_name="nvidia",
        extra_params=["timeout"],
    ),
    "g4f": ProviderSpec(
        provider_class=G4FProvider,
        no_keys=True,
        extra_params=["provider_name"],
    ),
    "canopywave": ProviderSpec(
        provider_class=CanopywaveProvider,
        key_name="canopywave",
    ),
    "baseten": ProviderSpec(
        provider_class=BasetenProvider,
        key_name="baseten",
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
    ),
}


async def create_provider_instances(
    name: str,
    spec: ProviderSpec,
    cfg: ProviderConfig,
) -> List[LLMProvider]:
    """
    Create provider instance(s) based on the spec and config.

    Args:
        name: Provider name from config
        spec: Provider specification from registry
        cfg: Provider configuration from config.yaml

    Returns:
        List of provider instances (usually 1, but can be multiple for multi_model)
    """
    # Handle multi-model providers (e.g., google_antigravity)
    if spec.multi_model:
        return [spec.provider_class(model=model) for model in cfg.models]

    # Build kwargs for provider instantiation
    kwargs: Dict[str, any] = {}

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

    # Add extra parameters from config
    for param in spec.extra_params:
        value = getattr(cfg, param, None)
        if value is not None:
            kwargs[param] = value

    return [spec.provider_class(**kwargs)]
