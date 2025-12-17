import json
import os
from random import shuffle
from typing import List
from gemini_webapi import GeminiClient
from src.config import API_KEYS_FILE, GEMINI_CREDENTIALS_FILE, ENABLE_GEMINI
from src.providers.base import LLMProvider
from src.providers.cerebras import CerebrasProvider
from src.providers.gemini import GeminiProvider

async def load_api_keys() -> List[str]:
    if not API_KEYS_FILE.exists():
        raise FileNotFoundError(f"API keys file not found: {API_KEYS_FILE}")
    
    with open(API_KEYS_FILE, "r") as f:
        keys_data = json.load(f)
        
    api_keys = [item["api_key"] for item in keys_data if "api_key" in item]
    if not api_keys:
        raise ValueError("No API keys found in the file.")
    
    # Shuffle the API keys to randomize the order
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
    
    # 1. Load API Keys for Cerebras
    try:
        api_keys = await load_api_keys()
        if api_keys:
            # Provider 1: Cerebras Primary
            providers.append(CerebrasProvider(
                api_keys=api_keys, 
                model="gpt-oss-120b"
            ))
            
            # Provider 2: Secondary Cerebras model if available
            # We pass the same list of keys; they will be rotated independently (or we could share the iterator if we wanted strict global rotation)
            # Since we want to maximize throughput, passing the full list is good.
            providers.append(CerebrasProvider(
                api_keys=api_keys, 
                model="zai-glm-4.6" 
            ))
    except Exception as e:
        print(f"Warning: Could not load Cerebras API keys: {e}")

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
