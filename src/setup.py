import json
import os
from random import shuffle
import itertools
from typing import List
import logging

logger = logging.getLogger(__name__)
from gemini_webapi import GeminiClient
from src.config import CEREBRAS_KEYS_FILE_PATH, OPENROUTER_KEYS_FILE, GEMINI_CREDENTIALS_FILE, ENABLE_GEMINI, NVIDIA_KEYS_FILE
from src.providers.base import LLMProvider
from src.providers.cerebras import CerebrasProvider
from src.providers.gemini import GeminiProvider
from src.providers.openrouter import OpenRouterProvider
from src.providers.nvidia import NvidiaProvider
from src.providers.g4f_provider import G4FProvider

async def load_cerebras_keys() -> List[str]:
    if not CEREBRAS_KEYS_FILE_PATH.exists():
        logger.warning(f"Cerebras API keys file not found: {CEREBRAS_KEYS_FILE_PATH}")
        return []
    
    with open(CEREBRAS_KEYS_FILE_PATH, "r", encoding="utf-8") as f:
        keys_data = json.load(f)
        
    api_keys = [item["api_key"] for item in keys_data if "api_key" in item]
    if not api_keys:
        logger.warning("No Cerebras API keys found in the file.")
        return []
    
    shuffle(api_keys)
    return api_keys

async def load_openrouter_keys() -> List[str]:
    if not OPENROUTER_KEYS_FILE.exists():
        logger.warning(f"OpenRouter API keys file not found: {OPENROUTER_KEYS_FILE}")
        return []
    
    with open(OPENROUTER_KEYS_FILE, "r", encoding="utf-8") as f:
        keys_data = json.load(f)
        
    api_keys = [item["data"]["key"] for item in keys_data if "data" in item and "key" in item.get("data", {})]
    if not api_keys:
        logger.warning("No OpenRouter API keys found in the file.")
        return []
    
    shuffle(api_keys)
    shuffle(api_keys)
    return api_keys

async def load_nvidia_keys() -> List[str]:
    if not NVIDIA_KEYS_FILE.exists():
        logger.warning(f"NVIDIA keys file not found: {NVIDIA_KEYS_FILE}")
        return []
    
    with open(NVIDIA_KEYS_FILE, "r", encoding="utf-8") as f:
        keys_data = json.load(f)
        
    # Support both list of strings or list of dicts with 'api_key'
    api_keys = []
    if isinstance(keys_data, list) and len(keys_data) > 0:
        if isinstance(keys_data[0], str):
            api_keys = keys_data
        elif isinstance(keys_data[0], dict) and "api_key" in keys_data[0]:
            api_keys = [item["api_key"] for item in keys_data if "api_key" in item]
            
    if not api_keys:
        logger.warning("No NVIDIA API keys found in the file.")
        return []
    
    shuffle(api_keys)
    return api_keys

async def load_gemini_clients() -> List[GeminiClient]:
    if not GEMINI_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"Credentials file not found: {GEMINI_CREDENTIALS_FILE}")
    
    with GEMINI_CREDENTIALS_FILE.open("r", encoding="utf-8") as f:
        creds_list = json.load(f)
        
    clients = []
    for creds in creds_list:
        try:
            client = GeminiClient(creds["Secure_1PSID"], creds["Secure_1PSIDTS"], proxy=None)
            await client.init(auto_refresh=True)
            clients.append(client)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
    return clients

async def initialize_providers() -> List[LLMProvider]:
    """Initializes and returns a list of configured LLM providers."""
    providers = []
    
    # 1. Load Cerebras Keys
    try:
        cerebras_keys = await load_cerebras_keys()
        if cerebras_keys:
            # Create a shared iterator for all Cerebras providers
            cerebras_key_iterator = itertools.cycle(cerebras_keys)
            
            providers.append(CerebrasProvider(
                api_keys=cerebras_key_iterator, 
                model="gpt-oss-120b"
            ))
            # providers.append(CerebrasProvider(
            #     api_keys=cerebras_key_iterator, 
            #     model="gpt-oss-120b"
            # ))
            # providers.append(CerebrasProvider(
            #     api_keys=cerebras_key_iterator, 
            #     model="zai-glm-4.6" 
            # ))
            # providers.append(CerebrasProvider(
            #     api_keys=cerebras_key_iterator, 
            #     model="qwen-3-235b-a22b-instruct-2507" 
            # ))
    except Exception as e:
        logger.warning(f"Error loading Cerebras providers: {e}")

    # # 2. Load OpenRouter Keys
    # try:
    #     openrouter_keys = await load_openrouter_keys()
    #     if openrouter_keys:
    #         or_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
    #         providers.append(OpenRouterProvider(
    #             api_keys=openrouter_keys,
    #             model=or_model
    #         ))
    # except Exception as e:
    #     logger.warning(f"Error loading OpenRouter providers: {e}")

    # 3. Load NVIDIA Keys
    try:
        nvidia_keys = await load_nvidia_keys()
        if nvidia_keys:
            nvidia_key_iterator = itertools.cycle(nvidia_keys)
            # providers.append(NvidiaProvider(
            #     api_keys=nvidia_key_iterator,
            #     model="moonshotai/kimi-k2-thinking"
            # ))
            # Also adding the one specifically requested in snippet, assuming it exists
            providers.append(NvidiaProvider(
                api_keys=nvidia_key_iterator,
                model="deepseek-ai/deepseek-v3.2"
            ))
    except Exception as e:
        logger.warning(f"Error loading NVIDIA providers: {e}")

    # 4. Initialize G4F Provider (Experimental)
    # try:
    #     # Using LMArena and the specific model as requested
    #     providers.append(G4FProvider(
    #         model="claude-opus-4-5-20251101-thinking-32k",
    #         provider="LMArena"
    #     ))
    # except Exception as e:
    #      logger.warning(f"Error initializing G4F provider: {e}")

    # 4. Initialize Gemini Providers
    if ENABLE_GEMINI:
        try:
            gemini_clients = await load_gemini_clients()
            for client in gemini_clients:
                providers.append(GeminiProvider(client))
        except Exception as e:
            logger.warning(f"Could not load Gemini clients: {e}")

    if not providers:
        logger.error("No providers could be initialized.")
        
    return providers
