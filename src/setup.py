import json
import os
from random import shuffle
import itertools
from typing import List
import logging

logger = logging.getLogger(__name__)
from gemini_webapi import GeminiClient
from src.config import CEREBRAS_KEYS_FILE_PATH, OPENROUTER_KEYS_FILE, GEMINI_CREDENTIALS_FILE, ENABLE_GEMINI, NVIDIA_KEYS_FILE, CANOPYWAVE_KEYS_FILE, BASETEN_KEYS_FILE, GOOGLE_GENAI_KEYS_FILE
from src.providers.base import LLMProvider
from src.providers.cerebras import CerebrasProvider
from src.providers.gemini import GeminiProvider
from src.providers.openrouter import OpenRouterProvider
from src.providers.nvidia import NvidiaProvider
from src.providers.g4f_provider import G4FProvider
from src.providers.canopywave import CanopywaveProvider
from src.providers.baseten import BasetenProvider
from src.providers.google_genai import GoogleGenAIProvider

async def load_cerebras_keys() -> List[str]:
    if not CEREBRAS_KEYS_FILE_PATH.exists():
        logger.warning(f"Cerebras API keys file not found: {CEREBRAS_KEYS_FILE_PATH}")
        return []
    
    with open(CEREBRAS_KEYS_FILE_PATH, "r", encoding="utf-8") as keys_file:
        keys_json_data = json.load(keys_file)
        
    api_key_list = [item["api_key"] for item in keys_json_data if "api_key" in item]
    if not api_key_list:
        logger.warning("No Cerebras API keys found in the file.")
        return []
    
    shuffle(api_key_list)
    return api_key_list

async def load_openrouter_keys() -> List[str]:
    if not OPENROUTER_KEYS_FILE.exists():
        logger.warning(f"OpenRouter API keys file not found: {OPENROUTER_KEYS_FILE}")
        return []
    
    with open(OPENROUTER_KEYS_FILE, "r", encoding="utf-8") as keys_file:
        keys_json_data = json.load(keys_file)
        
    api_key_list = [item["data"]["key"] for item in keys_json_data if "data" in item and "key" in item.get("data", {})]
    if not api_key_list:
        logger.warning("No OpenRouter API keys found in the file.")
        return []
    
    shuffle(api_key_list)
    return api_key_list

async def load_nvidia_keys() -> List[str]:
    if not NVIDIA_KEYS_FILE.exists():
        logger.warning(f"NVIDIA keys file not found: {NVIDIA_KEYS_FILE}")
        return []
    
    with open(NVIDIA_KEYS_FILE, "r", encoding="utf-8") as keys_file:
        keys_json_data = json.load(keys_file)
        
    # Support both list of strings or list of dicts with 'api_key'
    api_key_list = []
    if isinstance(keys_json_data, list) and len(keys_json_data) > 0:
        if isinstance(keys_json_data[0], str):
            api_key_list = keys_json_data
        elif isinstance(keys_json_data[0], dict) and "api_key" in keys_json_data[0]:
            api_key_list = [item["api_key"] for item in keys_json_data if "api_key" in item]
            
    if not api_key_list:
        logger.warning("No NVIDIA API keys found in the file.")
        return []
    
    shuffle(api_key_list)
    return api_key_list

async def load_canopywave_keys() -> List[str]:
    if not CANOPYWAVE_KEYS_FILE.exists():
        logger.warning(f"Canopywave API keys file not found: {CANOPYWAVE_KEYS_FILE}")
        return []
    
    with open(CANOPYWAVE_KEYS_FILE, "r", encoding="utf-8") as keys_file:
        keys_json_data = json.load(keys_file)
    
    # Support both list of strings or list of dicts with 'api_key'
    api_key_list = []
    if isinstance(keys_json_data, list) and len(keys_json_data) > 0:
        if isinstance(keys_json_data[0], str):
            api_key_list = keys_json_data
        elif isinstance(keys_json_data[0], dict) and "api_key" in keys_json_data[0]:
            api_key_list = [item["api_key"] for item in keys_json_data if "api_key" in item]
            
    if not api_key_list:
        logger.warning("No Canopywave API keys found in the file.")
        return []
    
    shuffle(api_key_list)
    return api_key_list

async def load_baseten_keys() -> List[str]:
    if not BASETEN_KEYS_FILE.exists():
        logger.warning(f"Baseten API keys file not found: {BASETEN_KEYS_FILE}")
        return []
    
    with open(BASETEN_KEYS_FILE, "r", encoding="utf-8") as keys_file:
        keys_json_data = json.load(keys_file)
    
    # Support both list of strings or list of dicts with 'api_key'
    api_key_list = []
    if isinstance(keys_json_data, list) and len(keys_json_data) > 0:
        if isinstance(keys_json_data[0], str):
            api_key_list = keys_json_data
        elif isinstance(keys_json_data[0], dict) and "api_key" in keys_json_data[0]:
            api_key_list = [item["api_key"] for item in keys_json_data if "api_key" in item]
            
    if not api_key_list:
        logger.warning("No Baseten API keys found in the file.")
        return []
    
    shuffle(api_key_list)
    return api_key_list

async def load_google_genai_keys() -> List[str]:
    if not GOOGLE_GENAI_KEYS_FILE.exists():
        logger.warning(f"Google GenAI API keys file not found: {GOOGLE_GENAI_KEYS_FILE}")
        return []
    
    with open(GOOGLE_GENAI_KEYS_FILE, "r", encoding="utf-8") as keys_file:
        keys_json_data = json.load(keys_file)
    
    # Support both list of strings or list of dicts with 'api_key'
    api_key_list = []
    if isinstance(keys_json_data, list) and len(keys_json_data) > 0:
        if isinstance(keys_json_data[0], str):
            api_key_list = keys_json_data
        elif isinstance(keys_json_data[0], dict) and "api_key" in keys_json_data[0]:
            api_key_list = [item["api_key"] for item in keys_json_data if "api_key" in item]
            
    if not api_key_list:
        logger.warning("No Google GenAI API keys found in the file.")
        return []
    
    shuffle(api_key_list)
    return api_key_list

async def load_gemini_clients() -> List[GeminiClient]:
    if not GEMINI_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"Credentials file not found: {GEMINI_CREDENTIALS_FILE}")
    
    with GEMINI_CREDENTIALS_FILE.open("r", encoding="utf-8") as credentials_file:
        credentials_list = json.load(credentials_file)
        
    initialized_clients = []
    for credentials in credentials_list:
        try:
            gemini_client = GeminiClient(credentials["Secure_1PSID"], credentials["Secure_1PSIDTS"], proxy=None)
            await gemini_client.init(auto_refresh=True)
            initialized_clients.append(gemini_client)
        except Exception as error:
            logger.error(f"Failed to initialize Gemini client: {error}")
    return initialized_clients

async def initialize_providers() -> List[LLMProvider]:
    """Initializes and returns a list of configured LLM providers."""
    active_providers = []
    
    # 1. Load Cerebras Keys
    try:
        cerebras_api_keys = await load_cerebras_keys()
        if cerebras_api_keys:
            # Create a shared iterator for all Cerebras providers
            cerebras_key_cycle = itertools.cycle(cerebras_api_keys)
            
            # active_providers.append(CerebrasProvider(
            #     api_keys=cerebras_key_cycle, 
            #     model="gpt-oss-120b"
            # ))
            # providers.append(CerebrasProvider(
            #     api_keys=cerebras_key_cycle, 
            #     model="gpt-oss-120b"
            # ))
            active_providers.append(CerebrasProvider(
                api_keys=cerebras_key_cycle, 
                model="zai-glm-4.6" 
            ))
            # providers.append(CerebrasProvider(
            #     api_keys=cerebras_key_cycle, 
            #     model="qwen-3-235b-a22b-instruct-2507" 
            # ))
    except Exception as error:
        logger.warning(f"Error loading Cerebras providers: {error}")

    # 2. Load OpenRouter Keys
    try:
        openrouter_api_keys = await load_openrouter_keys()
        # if openrouter_api_keys:
        #     openrouter_model_name = os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash:free")
        #     active_providers.append(OpenRouterProvider(
        #         api_keys=openrouter_api_keys,
        #         model=openrouter_model_name
        #     ))
    except Exception as error:
        logger.warning(f"Error loading OpenRouter providers: {error}")

    # 3. Load NVIDIA Keys
    try:
        nvidia_api_keys = await load_nvidia_keys()
        if nvidia_api_keys:
            nvidia_key_cycle = itertools.cycle(nvidia_api_keys)
            # active_providers.append(NvidiaProvider(
            #     api_keys=nvidia_key_cycle,
            #     model="moonshotai/kimi-k2-thinking"
            # ))
            # Also adding the one specifically requested in snippet, assuming it exists
            # active_providers.append(NvidiaProvider(
            #     api_keys=nvidia_key_cycle,
            #     model="deepseek-ai/deepseek-v3.2"
            # ))
    except Exception as error:
        logger.warning(f"Error loading NVIDIA providers: {error}")

    # 4. Initialize G4F Provider (Experimental)
    # try:
    #     # Using LMArena and the specific model as requested
    #     active_providers.append(G4FProvider(
    #         model="claude-opus-4-5-20251101-thinking-32k",
    #         provider="LMArena"
    #     ))
    # except Exception as error:
    #      logger.warning(f"Error initializing G4F provider: {error}")

    # 5. Load Canopywave Keys
    try:
        canopywave_api_keys = await load_canopywave_keys()
        if canopywave_api_keys:
            canopywave_key_cycle = itertools.cycle(canopywave_api_keys)
            active_providers.append(CanopywaveProvider(
                api_keys=canopywave_key_cycle,
                model="mimo-v2-flash"
            ))
            # active_providers.append(CanopywaveProvider(
            #     api_keys=canopywave_key_cycle,
            #     model="zai/glm-4.7"
            # ))
    except Exception as error:
        logger.warning(f"Error loading Canopywave providers: {error}")

    # 6. Initialize Baseten Keys
    try:
        baseten_api_keys = await load_baseten_keys()
        if baseten_api_keys:
            baseten_key_cycle = itertools.cycle(baseten_api_keys)
            # active_providers.append(BasetenProvider(
            #     api_keys=baseten_key_cycle,
            #     model="zai-org/GLM-4.7"
            # ))
    except Exception as error:
        logger.warning(f"Error loading Baseten providers: {error}")

    # 7. Initialize Gemini Providers (reverse-engineered webapi)
    if ENABLE_GEMINI:
        try:
            gemini_client_list = await load_gemini_clients()
            for gemini_client in gemini_client_list:
                active_providers.append(GeminiProvider(gemini_client))
        except Exception as error:
            logger.warning(f"Could not load Gemini clients: {error}")

    # 8. Initialize Google GenAI Provider (Official API)
    try:
        google_genai_keys = await load_google_genai_keys()
        if google_genai_keys:
            google_genai_key_cycle = itertools.cycle(google_genai_keys)
            active_providers.append(GoogleGenAIProvider(
                api_keys=google_genai_key_cycle,
                model="gemini-3-flash-preview",
                thinking_level="high"
            ))
    except Exception as error:
        logger.warning(f"Error loading Google GenAI providers: {error}")

    if not active_providers:
        logger.error("No providers could be initialized.")
        
    return active_providers
