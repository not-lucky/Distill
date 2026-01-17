"""Provider initialization and configuration."""

import itertools
import json
import logging
from typing import List

from gemini_webapi import GeminiClient

from src.config import GEMINI_CREDENTIALS_FILE, ENABLE_GEMINI
from src.config.keys import load_keys
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
    """Initialize and return a list of configured LLM providers."""
    active_providers = []

    # Cerebras
    try:
        cerebras_keys = await load_keys("cerebras")
        if cerebras_keys:
            key_cycle = itertools.cycle(cerebras_keys)
            active_providers.append(
                CerebrasProvider(api_keys=key_cycle, model="gpt-oss-120b")
            )
    except Exception as error:
        logger.warning(f"Error loading Cerebras providers: {error}")

    # OpenRouter (commented out by default)
    # try:
    #     openrouter_keys = await load_keys("openrouter")
    #     if openrouter_keys:
    #         key_cycle = itertools.cycle(openrouter_keys)
    #         active_providers.append(
    #             OpenRouterProvider(api_keys=key_cycle, model="xiaomi/mimo-v2-flash:free")
    #         )
    # except Exception as error:
    #     logger.warning(f"Error loading OpenRouter providers: {error}")

    # NVIDIA (commented out by default)
    # try:
    #     nvidia_keys = await load_keys("nvidia")
    #     if nvidia_keys:
    #         key_cycle = itertools.cycle(nvidia_keys)
    #         active_providers.append(
    #             NvidiaProvider(api_keys=key_cycle, model="moonshotai/kimi-k2-thinking")
    #         )
    # except Exception as error:
    #     logger.warning(f"Error loading NVIDIA providers: {error}")

    # G4F (commented out by default)
    # try:
    #     active_providers.append(
    #         G4FProvider(model="claude-opus-4-5-20251101-thinking-32k", provider="LMArena")
    #     )
    # except Exception as error:
    #     logger.warning(f"Error initializing G4F provider: {error}")

    # Canopywave (commented out by default)
    # try:
    #     canopywave_keys = await load_keys("canopywave")
    #     if canopywave_keys:
    #         key_cycle = itertools.cycle(canopywave_keys)
    #         active_providers.append(
    #             CanopywaveProvider(api_keys=key_cycle, model="zai/glm-4.7")
    #         )
    # except Exception as error:
    #     logger.warning(f"Error loading Canopywave providers: {error}")

    # Baseten (commented out by default)
    # try:
    #     baseten_keys = await load_keys("baseten")
    #     if baseten_keys:
    #         key_cycle = itertools.cycle(baseten_keys)
    #         active_providers.append(
    #             BasetenProvider(api_keys=key_cycle, model="zai-org/GLM-4.7")
    #         )
    # except Exception as error:
    #     logger.warning(f"Error loading Baseten providers: {error}")

    # Gemini Web API (reverse-engineered)
    if ENABLE_GEMINI:
        try:
            gemini_clients = await load_gemini_clients()
            for client in gemini_clients:
                active_providers.append(GeminiProvider(client))
        except Exception as error:
            logger.warning(f"Could not load Gemini clients: {error}")

    # Google GenAI (Official API, commented out by default)
    # try:
    #     google_genai_keys = await load_keys("google_genai")
    #     if google_genai_keys:
    #         key_cycle = itertools.cycle(google_genai_keys)
    #         active_providers.append(
    #             GoogleGenAIProvider(
    #                 api_keys=key_cycle,
    #                 model="gemini-3-flash-preview",
    #                 thinking_level="high",
    #             )
    #         )
    # except Exception as error:
    #     logger.warning(f"Error loading Google GenAI providers: {error}")

    # Google Antigravity (local proxy, no auth needed)
    active_providers.append(GoogleAntigravityProvider(model="gemini-3-pro-preview"))
    active_providers.append(
        GoogleAntigravityProvider(model="gemini-claude-sonnet-4-5-thinking")
    )

    if not active_providers:
        logger.error("No providers could be initialized.")

    return active_providers
