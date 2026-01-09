import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

try:
    from src.providers.google_genai import GoogleGenAIProvider
    from src.setup import load_google_genai_keys, initialize_providers
    from src.config import GOOGLE_GENAI_KEYS_FILE
    print("Imports successful.")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

async def test_instantiation():
    print("Testing instantiation...")
    # Mock keys file check
    # We won't actually call the API, just check we can create the object
    
    # Create the keys file temporarily if needed, or just pass a mock iterator
    mock_keys = iter(["dummy_key"])
    provider = GoogleGenAIProvider(api_keys=mock_keys)
    print(f"Provider instantiated: {provider}")
    print(f"Model: {provider.model}")
    
    # Test client creation (should not fail until API call)
    client = provider._get_client()
    print(f"Client created: {client}")

if __name__ == "__main__":
    asyncio.run(test_instantiation())
