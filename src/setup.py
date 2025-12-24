import json
import os
from random import shuffle
import itertools
from typing import List
from gemini_webapi import GeminiClient
from src.config import CEREBRAS_KEYS_FILE_PATH, OPENROUTER_KEYS_FILE, GEMINI_CREDENTIALS_FILE, ENABLE_GEMINI
from src.providers.base import LLMProvider
from src.providers.cerebras import CerebrasProvider
from src.providers.gemini import GeminiProvider
from src.providers.openrouter import OpenRouterProvider

async def load_cerebras_keys() -> List[str]:
    if not CEREBRAS_KEYS_FILE_PATH.exists():
        print(f"Warning: Cerebras API keys file not found: {CEREBRAS_KEYS_FILE_PATH}")
        return []
    
    with open(CEREBRAS_KEYS_FILE_PATH, "r") as f:
        keys_data = json.load(f)
        
    api_keys = [item["api_key"] for item in keys_data if "api_key" in item]
    if not api_keys:
        print("Warning: No Cerebras API keys found in the file.")
        return []
    
    shuffle(api_keys)
    return api_keys

async def load_openrouter_keys() -> List[str]:
    if not OPENROUTER_KEYS_FILE.exists():
        print(f"Warning: OpenRouter API keys file not found: {OPENROUTER_KEYS_FILE}")
        return []
    
    with open(OPENROUTER_KEYS_FILE, "r") as f:
        keys_data = json.load(f)
        
    api_keys = [item["data"]["key"] for item in keys_data if "data" in item and "key" in item.get("data", {})]
    if not api_keys:
        print("Warning: No OpenRouter API keys found in the file.")
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
            print(f"Failed to initialize Gemini client: {e}")
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
            providers.append(CerebrasProvider(
                api_keys=cerebras_key_iterator, 
                model="zai-glm-4.6" 
            ))
            providers.append(CerebrasProvider(
                api_keys=cerebras_key_iterator, 
                model="qwen-3-235b-a22b-instruct-2507" 
            ))
    except Exception as e:
        print(f"Warning: Error loading Cerebras providers: {e}")

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
    #     print(f"Warning: Error loading OpenRouter providers: {e}")

    # 2. Initialize Gemini Providers
    if ENABLE_GEMINI:
        try:
            gemini_clients = await load_gemini_clients()
            for client in gemini_clients:
                providers.append(GeminiProvider(client))
        except Exception as e:
            print(f"Warning: Could not load Gemini clients: {e}")

    if not providers:
        print("Error: No providers could be initialized.")
        
    return providers
