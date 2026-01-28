"""Integration tests for LLM response caching."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from assertpy import assert_that

from src.cache import generate_cache_key
from src.database import DatabaseManager


class TestCachingIntegration:
    """Integration tests for end-to-end caching behavior."""

    @pytest.fixture
    def cache_db(self, integration_db):
        """Database manager for caching tests."""
        return integration_db

    @pytest.fixture
    def test_provider(self, cache_db):
        """Create a test provider with caching enabled."""
        from src.providers.openai_compatible import OpenAICompatibleProvider

        class TestProvider(OpenAICompatibleProvider):
            @property
            def name(self):
                return "test_provider"

        provider = TestProvider(
            model="test-model",
            base_url="http://test.api",
            temperature=0.7,
            use_cache=True,
        )
        return provider

    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self, cache_db, test_provider):
        """Second identical request should hit cache, not API."""
        messages = [{"role": "user", "content": "test message"}]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"cards": []}'

        # Track API calls
        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(
            test_provider, "_get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            mock_get_client.return_value = mock_client

            # First call - should call API
            result1 = await test_provider._make_request(messages)
            assert_that(result1).is_equal_to('{"cards": []}')
            assert_that(call_count).is_equal_to(1)

            # Second call - should hit cache
            result2 = await test_provider._make_request(messages)
            assert_that(result2).is_equal_to('{"cards": []}')
            # API should NOT be called again
            assert_that(call_count).is_equal_to(1)

    @pytest.mark.asyncio
    async def test_different_messages_miss_cache(self, cache_db, test_provider):
        """Different messages should cause cache miss."""
        messages1 = [{"role": "user", "content": "message 1"}]
        messages2 = [{"role": "user", "content": "message 2"}]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"cards": []}'

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(
            test_provider, "_get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            mock_get_client.return_value = mock_client

            # First call with message 1
            await test_provider._make_request(messages1)
            assert_that(call_count).is_equal_to(1)

            # Second call with message 2 - should call API again
            await test_provider._make_request(messages2)
            assert_that(call_count).is_equal_to(2)

    @pytest.mark.asyncio
    async def test_bypass_cache_lookup_still_stores(self, cache_db):
        """bypass_cache_lookup=True should skip lookup but still store."""
        from src.providers.openai_compatible import OpenAICompatibleProvider

        class TestProvider(OpenAICompatibleProvider):
            @property
            def name(self):
                return "test_provider"

        # Create provider with bypass_cache_lookup=True
        provider = TestProvider(
            model="test-model",
            base_url="http://test.api",
            temperature=0.7,
            use_cache=True,
            bypass_cache_lookup=True,
        )

        messages = [{"role": "user", "content": "bypass test"}]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "bypass"}'

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(
            provider, "_get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            mock_get_client.return_value = mock_client

            # First call - should call API (bypass is on)
            result1 = await provider._make_request(messages)
            assert_that(call_count).is_equal_to(1)

            # Second call - should ALSO call API (bypass is still on)
            result2 = await provider._make_request(messages)
            assert_that(call_count).is_equal_to(2)

        # Now create a normal provider and verify cache was populated
        normal_provider = TestProvider(
            model="test-model",
            base_url="http://test.api",
            temperature=0.7,
            use_cache=True,
            bypass_cache_lookup=False,
        )

        with patch.object(
            normal_provider, "_get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            mock_get_client.return_value = mock_client

            # This should hit cache from the bypass provider's storage
            result3 = await normal_provider._make_request(messages)
            # API should NOT be called again (call_count stays at 2)
            assert_that(call_count).is_equal_to(2)
            assert_that(result3).is_equal_to('{"result": "bypass"}')

    @pytest.mark.asyncio
    async def test_cache_disabled_never_caches(self, cache_db):
        """use_cache=False should never cache."""
        from src.providers.openai_compatible import OpenAICompatibleProvider

        class TestProvider(OpenAICompatibleProvider):
            @property
            def name(self):
                return "test_provider"

        # Create provider with use_cache=False
        provider = TestProvider(
            model="test-model",
            base_url="http://test.api",
            temperature=0.7,
            use_cache=False,
        )

        messages = [{"role": "user", "content": "no cache test"}]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "no cache"}'

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(
            provider, "_get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            mock_get_client.return_value = mock_client

            # First call
            await provider._make_request(messages)
            assert_that(call_count).is_equal_to(1)

            # Second call - should still call API (no caching)
            await provider._make_request(messages)
            assert_that(call_count).is_equal_to(2)

            # Third call - should still call API
            await provider._make_request(messages)
            assert_that(call_count).is_equal_to(3)

    @pytest.mark.asyncio
    async def test_failed_request_not_cached(self, cache_db, test_provider):
        """Failed API requests should not be cached."""
        messages = [{"role": "user", "content": "fail test"}]

        call_count = 0

        async def mock_create_fail(**kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("API Error")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"success": true}'

        async def mock_create_success(**kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch.object(
            test_provider, "_get_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create_fail
            mock_get_client.return_value = mock_client

            # First call fails
            result1 = await test_provider._make_request(messages)
            assert_that(result1).is_none()
            assert_that(call_count).is_equal_to(1)

            # Update mock to succeed
            mock_client.chat.completions.create = mock_create_success

            # Second call should succeed and hit API (failure not cached)
            result2 = await test_provider._make_request(messages)
            assert_that(result2).is_equal_to('{"success": true}')
            assert_that(call_count).is_equal_to(2)

            # Third call should hit cache
            result3 = await test_provider._make_request(messages)
            assert_that(result3).is_equal_to('{"success": true}')
            assert_that(call_count).is_equal_to(2)  # No additional API call
