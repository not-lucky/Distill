"""Provider initialization and configuration."""

import itertools
import json
import logging
from typing import List

from gemini_webapi import GeminiClient

from src.config import GEMINI_CREDENTIALS_FILE, ENABLE_GEMINI
from src.config.keys import load_keys
from src.config.loader import load_config, ProviderConfig
from src.providers.base import LLMProvider
from src.providers.cerebras import CerebrasProvider
from src.providers.gemini import GeminiProvider
from src.providers.openrouter import OpenRouterProvider
from src.providers.nvidia import NvidiaProvider
from src.providers.g4f_provider import G4FProvider
from src.providers.canopywave import CanopywaveProvider
from src.providers.baseten import BasetenProvider
from src.providers.google_genai import GoogleGenAIProvider
from src.providers.google_antigravity import GoogleAntigravityProvider

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
    active_providers = []

    # Cerebras
    cerebras_cfg = config.providers.get("cerebras")
    if cerebras_cfg and cerebras_cfg.enabled:
        try:
            cerebras_keys = await load_keys("cerebras")
            if cerebras_keys:
                key_cycle = itertools.cycle(cerebras_keys)
                active_providers.append(
                    CerebrasProvider(
                        api_keys=key_cycle,
                        model=cerebras_cfg.model,
                        reasoning_effort=cerebras_cfg.reasoning_effort or "high",
                    )
                )
        except Exception as error:
            logger.warning(f"Error loading Cerebras providers: {error}")

    # OpenRouter
    openrouter_cfg = config.providers.get("openrouter")
    if openrouter_cfg and openrouter_cfg.enabled:
        try:
            openrouter_keys = await load_keys("openrouter")
            if openrouter_keys:
                key_cycle = itertools.cycle(openrouter_keys)
                active_providers.append(
                    OpenRouterProvider(api_keys=key_cycle, model=openrouter_cfg.model)
                )
        except Exception as error:
            logger.warning(f"Error loading OpenRouter providers: {error}")

    # NVIDIA
    nvidia_cfg = config.providers.get("nvidia")
    if nvidia_cfg and nvidia_cfg.enabled:
        try:
            nvidia_keys = await load_keys("nvidia")
            if nvidia_keys:
                key_cycle = itertools.cycle(nvidia_keys)
                active_providers.append(
                    NvidiaProvider(
                        api_keys=key_cycle,
                        model=nvidia_cfg.model,
                        timeout=nvidia_cfg.timeout,
                    )
                )
        except Exception as error:
            logger.warning(f"Error loading NVIDIA providers: {error}")

    # G4F
    g4f_cfg = config.providers.get("g4f")
    if g4f_cfg and g4f_cfg.enabled:
        try:
            active_providers.append(
                G4FProvider(
                    model=g4f_cfg.model,
                    provider=g4f_cfg.provider_name or "LMArena",
                )
            )
        except Exception as error:
            logger.warning(f"Error initializing G4F provider: {error}")

    # Canopywave
    canopywave_cfg = config.providers.get("canopywave")
    if canopywave_cfg and canopywave_cfg.enabled:
        try:
            canopywave_keys = await load_keys("canopywave")
            if canopywave_keys:
                key_cycle = itertools.cycle(canopywave_keys)
                active_providers.append(
                    CanopywaveProvider(api_keys=key_cycle, model=canopywave_cfg.model)
                )
        except Exception as error:
            logger.warning(f"Error loading Canopywave providers: {error}")

    # Baseten
    baseten_cfg = config.providers.get("baseten")
    if baseten_cfg and baseten_cfg.enabled:
        try:
            baseten_keys = await load_keys("baseten")
            if baseten_keys:
                key_cycle = itertools.cycle(baseten_keys)
                active_providers.append(
                    BasetenProvider(api_keys=key_cycle, model=baseten_cfg.model)
                )
        except Exception as error:
            logger.warning(f"Error loading Baseten providers: {error}")

    # Gemini Web API (reverse-engineered)
    gemini_cfg = config.providers.get("gemini_webapi")
    if (gemini_cfg and gemini_cfg.enabled) or ENABLE_GEMINI:
        try:
            gemini_clients = await load_gemini_clients()
            for client in gemini_clients:
                active_providers.append(GeminiProvider(client))
        except Exception as error:
            logger.warning(f"Could not load Gemini clients: {error}")

    # Google GenAI (Official API)
    google_genai_cfg = config.providers.get("google_genai")
    if google_genai_cfg and google_genai_cfg.enabled:
        try:
            google_genai_keys = await load_keys("google_genai")
            if google_genai_keys:
                key_cycle = itertools.cycle(google_genai_keys)
                active_providers.append(
                    GoogleGenAIProvider(
                        api_keys=key_cycle,
                        model=google_genai_cfg.model,
                        thinking_level=google_genai_cfg.thinking_level or "high",
                    )
                )
        except Exception as error:
            logger.warning(f"Error loading Google GenAI providers: {error}")

    # Google Antigravity (local proxy, no auth needed)
    antigravity_cfg = config.providers.get("google_antigravity")
    if antigravity_cfg and antigravity_cfg.enabled:
        for model in antigravity_cfg.models:
            active_providers.append(GoogleAntigravityProvider(model=model))

    if not active_providers:
        logger.error("No providers could be initialized.")

    return active_providers
