import asyncio
import json
from unittest.mock import AsyncMock, patch
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.providers.cerebras import CerebrasProvider
from src.providers.nvidia import NvidiaProvider
from src.providers.openrouter import OpenRouterProvider

async def test_combine_cards_retries():
    """
    Test that combine_cards retries on JSONDecodeError and eventually succeeds
    if valid JSON is returned within the retry limit.
    """
    
    # Mock return values: 2 failures (bad JSON), then 1 success (good JSON)
    bad_response = "This is not JSON"
    good_response = '{"cards": [{"front": "Q", "back": "A"}]}'
    
    # We'll test with one provider as the logic is identical across them
    # Mocking CerebrasProvider's _make_request
    
    provider = CerebrasProvider(api_keys=iter(["fake_key"]), model="llama3.1-70b")
    
    with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = [bad_response, bad_response, good_response]
        
        result = await provider.combine_cards("question", "inputs", {})
        
        assert mock_request.call_count == 3
        assert result is not None
        assert result.get("cards")[0].get("front") == "Q"
        print("\n✅ Test passed: Retried 3 times and succeeded.")

async def test_combine_cards_fails_after_retries():
    """
    Test that combine_cards gives up after 3 failed attempts.
    """
    bad_response = "This is not JSON"
    
    provider = CerebrasProvider(api_keys=iter(["fake_key"]), model="llama3.1-70b")
    
    with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = bad_response
        
        result = await provider.combine_cards("question", "inputs", {})
        
        assert mock_request.call_count == 3
        assert result is None
        print("\n✅ Test passed: Failed gracefully after 3 retries.")

if __name__ == "__main__":
    # Simple manual runner if pytest isn't available or for quick check
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print("Running success test...")
        loop.run_until_complete(test_combine_cards_retries())
        print("Running failure test...")
        loop.run_until_complete(test_combine_cards_fails_after_retries())
    finally:
        loop.close()
