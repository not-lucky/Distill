"""Tests for providers/openai_compatible.py.

Comprehensive tests for OpenAI-compatible provider implementation.
Target: 5:1 test-to-code ratio (~1,455 lines of tests for ~291 lines of code).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import itertools
from typing import Iterator

from assertpy import assert_that

from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.base import RateLimitError, TimeoutError, EmptyResponseError, RetryableError

from conftest import SAMPLE_CARD_RESPONSE, SAMPLE_CARD_RESPONSE_DICT


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


class ConcreteOpenAIProvider(OpenAICompatibleProvider):
    """Concrete implementation for testing."""

    @property
    def name(self) -> str:
        return "test_provider"


def create_mock_response(content: str):
    """Helper to create a mock OpenAI completion response."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    return mock_completion


def create_mock_client(response=None, side_effect=None):
    """Helper to create a mock AsyncOpenAI client."""
    mock_client = AsyncMock()
    if side_effect:
        mock_client.chat.completions.create = AsyncMock(side_effect=side_effect)
    else:
        mock_client.chat.completions.create = AsyncMock(return_value=response)
    return mock_client


# =============================================================================
# Initialization Tests
# =============================================================================


class TestOpenAICompatibleProviderInit:
    """Tests for OpenAICompatibleProvider initialization."""

    def test_init_basic(self):
        """
        Given basic initialization parameters
        When ConcreteOpenAIProvider is created
        Then model and base_url are set correctly
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        assert_that(provider.model).is_equal_to("test-model")
        assert_that(provider.base_url).is_equal_to("https://api.test.com/v1")

    def test_init_all_parameters(self):
        """
        Given all initialization parameters
        When ConcreteOpenAIProvider is created
        Then all values are set correctly
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            api_keys=itertools.cycle(["key1", "key2"]),
            timeout=120.0,
            max_retries=3,
            json_parse_retries=2,
            temperature=0.7,
            max_tokens=4096,
            strip_json_markers=False,
            top_p=0.9,
            extra_params={"custom": "value"},
        )
        assert_that(provider.model).is_equal_to("test-model")
        assert_that(provider.timeout).is_equal_to(120.0)
        assert_that(provider.max_retries).is_equal_to(3)
        assert_that(provider.json_parse_retries).is_equal_to(2)
        assert_that(provider.temperature).is_equal_to(0.7)
        assert_that(provider.max_tokens).is_equal_to(4096)
        assert_that(provider.strip_json_markers).is_false()
        assert_that(provider.top_p).is_equal_to(0.9)
        assert_that(provider.extra_params).is_equal_to({"custom": "value"})

    def test_init_defaults(self):
        """
        Given minimal initialization parameters
        When ConcreteOpenAIProvider is created
        Then default values are set correctly
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
        )
        assert_that(provider.max_retries).is_equal_to(5)
        assert_that(provider.json_parse_retries).is_equal_to(5)
        assert_that(provider.timeout).is_equal_to(120.0)
        assert_that(provider.temperature).is_equal_to(0.4)
        assert_that(provider.max_tokens).is_none()
        assert_that(provider.strip_json_markers).is_true()
        assert_that(provider.top_p).is_none()
        assert_that(provider.extra_params).is_equal_to({})

    @pytest.mark.parametrize("model_name", [
        "gpt-4",
        "llama3.1-70b",
        "gemini-1.5-pro",
        "claude-3-opus",
        "model-with-numbers-123",
    ])
    def test_init_various_model_names(self, model_name):
        """
        Given various model name strings
        When ConcreteOpenAIProvider is created
        Then the model name is stored correctly
        """
        provider = ConcreteOpenAIProvider(
            model=model_name,
            base_url="https://api.test.com/v1",
        )
        assert_that(provider.model).is_equal_to(model_name)

    @pytest.mark.parametrize("base_url", [
        "https://api.openai.com/v1",
        "https://api.cerebras.ai/v1",
        "http://localhost:8080/v1",
        "https://custom.domain.com/api/v2",
    ])
    def test_init_various_base_urls(self, base_url):
        """
        Given various base URL strings
        When ConcreteOpenAIProvider is created
        Then the base URL is stored correctly
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url=base_url,
        )
        assert_that(provider.base_url).is_equal_to(base_url)

    @pytest.mark.parametrize("timeout", [10.0, 30.0, 60.0, 120.0, 300.0])
    def test_init_various_timeouts(self, timeout):
        """
        Given various timeout values
        When ConcreteOpenAIProvider is created
        Then the timeout is stored correctly
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            timeout=timeout,
        )
        assert_that(provider.timeout).is_equal_to(timeout)

    @pytest.mark.parametrize("temperature", [0.0, 0.3, 0.5, 0.7, 1.0, 2.0])
    def test_init_various_temperatures(self, temperature):
        """
        Given various temperature values
        When ConcreteOpenAIProvider is created
        Then the temperature is stored correctly
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            temperature=temperature,
        )
        assert_that(provider.temperature).is_equal_to(temperature)


class TestOpenAICompatibleProviderProperties:
    """Tests for provider properties."""

    def test_model_property(self):
        """
        Given an initialized provider
        When the model property is accessed
        Then the model name is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model-v1",
            base_url="https://api.test.com/v1",
        )
        assert_that(provider.model).is_equal_to("test-model-v1")

    def test_name_property_abstract(self):
        """
        Given an initialized concrete provider
        When the name property is accessed
        Then the subclass-defined name is returned
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
        )
        assert_that(provider.name).is_equal_to("test_provider")


# =============================================================================
# API Key Management Tests
# =============================================================================


class TestAPIKeyManagement:
    """Tests for API key management."""

    def test_get_api_key_cycles(self):
        """
        Given a provider with multiple API keys
        When _get_api_key is called multiple times
        Then keys cycle in order
        """
        keys = itertools.cycle(["key1", "key2", "key3"])
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            api_keys=keys,
        )
        assert_that(provider._get_api_key()).is_equal_to("key1")
        assert_that(provider._get_api_key()).is_equal_to("key2")
        assert_that(provider._get_api_key()).is_equal_to("key3")
        assert_that(provider._get_api_key()).is_equal_to("key1")  # Cycles back

    def test_get_api_key_none(self):
        """
        Given a provider with no API keys configured
        When _get_api_key is called
        Then an empty string is returned
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            api_keys=None,
        )
        assert_that(provider._get_api_key()).is_equal_to("")

    def test_get_api_key_single_key(self):
        """
        Given a provider with a single cycling key
        When _get_api_key is called multiple times
        Then the same key is returned each time
        """
        keys = itertools.cycle(["only-key"])
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            api_keys=keys,
        )
        assert_that(provider._get_api_key()).is_equal_to("only-key")
        assert_that(provider._get_api_key()).is_equal_to("only-key")

    def test_get_api_key_iterator_exhausted(self):
        """
        Given a provider with a finite key iterator
        When the iterator is exhausted
        Then StopIteration is raised
        """
        keys = iter(["key1", "key2"])
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            api_keys=keys,
        )
        assert_that(provider._get_api_key()).is_equal_to("key1")
        assert_that(provider._get_api_key()).is_equal_to("key2")
        with pytest.raises(StopIteration):
            provider._get_api_key()


# =============================================================================
# Extra Request Parameters Tests
# =============================================================================


class TestExtraRequestParams:
    """Tests for _get_extra_request_params method."""

    def test_get_extra_request_params_empty(self):
        """
        Given a provider with no extra params configured
        When _get_extra_request_params is called
        Then an empty dict is returned
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
        )
        params = provider._get_extra_request_params()
        assert_that(params).is_equal_to({})

    def test_get_extra_request_params_top_p_only(self):
        """
        Given a provider with only top_p configured
        When _get_extra_request_params is called
        Then top_p is included in the result
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            top_p=0.9,
        )
        params = provider._get_extra_request_params()
        assert_that(params).is_equal_to({"top_p": 0.9})

    def test_get_extra_request_params_extra_only(self):
        """
        Given a provider with only extra_params configured
        When _get_extra_request_params is called
        Then all extra_params are included
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            extra_params={"custom_param": "value", "another": 42},
        )
        params = provider._get_extra_request_params()
        assert_that(params).is_equal_to({"custom_param": "value", "another": 42})

    def test_get_extra_request_params_combined(self):
        """
        Given a provider with both top_p and extra_params
        When _get_extra_request_params is called
        Then both are included in the result
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            top_p=0.9,
            extra_params={"custom_param": "value"},
        )
        params = provider._get_extra_request_params()
        assert_that(params["top_p"]).is_equal_to(0.9)
        assert_that(params["custom_param"]).is_equal_to("value")

    def test_extra_params_override_top_p(self):
        """
        Given a provider with conflicting top_p values
        When _get_extra_request_params is called
        Then extra_params takes precedence
        """
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            top_p=0.9,
            extra_params={"top_p": 0.5},  # Override
        )
        params = provider._get_extra_request_params()
        assert_that(params["top_p"]).is_equal_to(0.5)  # extra_params wins


# =============================================================================
# Client Creation Tests
# =============================================================================


class TestGetClient:
    """Tests for _get_client method."""

    def test_get_client_creates_async_openai(self):
        """
        Given a configured provider
        When _get_client is called
        Then AsyncOpenAI client is created with correct parameters
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            api_keys=itertools.cycle(["test-key"]),
            timeout=30.0,
        )
        with patch("src.providers.openai_compatible.AsyncOpenAI") as MockAsyncOpenAI:
            provider._get_client()
            MockAsyncOpenAI.assert_called_once_with(
                api_key="test-key",
                base_url="https://api.test.com/v1",
                timeout=30.0,
            )

    def test_get_client_uses_correct_timeout(self):
        """
        Given a provider with custom timeout
        When _get_client is called
        Then the timeout is passed to AsyncOpenAI
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            timeout=60.0,
        )
        with patch("src.providers.openai_compatible.AsyncOpenAI") as MockAsyncOpenAI:
            provider._get_client()
            call_kwargs = MockAsyncOpenAI.call_args[1]
            assert_that(call_kwargs["timeout"]).is_equal_to(60.0)

    def test_get_client_rotates_keys(self):
        """
        Given a provider with multiple API keys
        When _get_client is called multiple times
        Then API keys are rotated
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            api_keys=itertools.cycle(["key1", "key2"]),
        )
        with patch("src.providers.openai_compatible.AsyncOpenAI") as MockAsyncOpenAI:
            provider._get_client()
            assert_that(MockAsyncOpenAI.call_args[1]["api_key"]).is_equal_to("key1")

            provider._get_client()
            assert_that(MockAsyncOpenAI.call_args[1]["api_key"]).is_equal_to("key2")


# =============================================================================
# Make Request Tests
# =============================================================================


class TestMakeRequestSuccess:
    """Tests for successful _make_request calls."""

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """
        Given a provider with mocked successful response
        When _make_request is called
        Then the response content is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response("response content")

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_equal_to("response content")

    @pytest.mark.asyncio
    async def test_make_request_with_json_schema(self):
        """
        Given a request with json_schema parameter
        When _make_request is called
        Then the response is returned correctly
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response('{"key": "value"}')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema={"type": "object"},
            )
            assert_that(result).is_equal_to('{"key": "value"}')

    @pytest.mark.asyncio
    async def test_make_request_with_max_tokens(self):
        """
        Given a provider with max_tokens configured
        When _make_request is called
        Then max_tokens is passed to the API
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_tokens=4096,
        )
        mock_response = create_mock_response("response")

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = create_mock_client(response=mock_response)
            mock_get_client.return_value = mock_client

            await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert_that(call_kwargs["max_tokens"]).is_equal_to(4096)


class TestMakeRequestJSONStripping:
    """Tests for JSON marker stripping in _make_request."""

    @pytest.mark.asyncio
    async def test_strips_json_markers(self):
        """
        Given strip_json_markers=True and response with markers
        When _make_request is called with json_schema
        Then JSON markers are stripped from response
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            strip_json_markers=True,
        )
        mock_response = create_mock_response('```json\n{"key": "value"}\n```')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema={"type": "object"},
            )
            assert_that(result).is_equal_to('{"key": "value"}')

    @pytest.mark.asyncio
    async def test_strips_plain_markdown_markers(self):
        """
        Given strip_json_markers=True and response with plain code block markers
        When _make_request is called with json_schema
        Then markers are stripped from response
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            strip_json_markers=True,
        )
        mock_response = create_mock_response('```\n{"key": "value"}\n```')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema={"type": "object"},
            )
            assert_that(result).is_equal_to('{"key": "value"}')

    @pytest.mark.asyncio
    async def test_no_strip_when_disabled(self):
        """
        Given strip_json_markers=False
        When _make_request is called
        Then markers are preserved in response
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            strip_json_markers=False,
        )
        mock_response = create_mock_response('```json\n{"key": "value"}\n```')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema={"type": "object"},
            )
            assert_that(result).is_equal_to('```json\n{"key": "value"}\n```')

    @pytest.mark.asyncio
    async def test_no_strip_without_json_schema(self):
        """
        Given strip_json_markers=True but no json_schema
        When _make_request is called
        Then markers are preserved in response
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            strip_json_markers=True,
        )
        mock_response = create_mock_response('```json\n{"key": "value"}\n```')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema=None,  # No schema
            )
            assert_that(result).is_equal_to('```json\n{"key": "value"}\n```')


class TestMakeRequestErrorHandling:
    """Tests for error handling in _make_request."""

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self):
        """
        Given a rate limit error from the API
        When _make_request is called
        Then None is returned
        """
        from openai import RateLimitError as OpenAIRateLimitError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        error = OpenAIRateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self):
        """
        Given a timeout error from the API
        When _make_request is called
        Then None is returned
        """
        from openai import APITimeoutError as OpenAITimeoutError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        error = OpenAITimeoutError(request=MagicMock())

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_empty_response(self):
        """
        Given an empty response from the API
        When _make_request is called
        Then None is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )
        mock_response = create_mock_response("")

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_none_content(self):
        """
        Given None content in response
        When _make_request is called
        Then None is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )
        mock_response = create_mock_response(None)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self):
        """
        Given a generic exception from the API
        When _make_request is called
        Then None is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(
                side_effect=Exception("Unexpected error")
            )

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()


class TestMakeRequestRetryBehavior:
    """Tests for retry behavior in _make_request."""

    @pytest.mark.asyncio
    async def test_retries_on_empty_response(self):
        """
        Given empty responses followed by successful response
        When _make_request is called
        Then retries until success and returns valid content
        """
        call_count = 0

        async def create_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return create_mock_response("")
            return create_mock_response("success")

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=5,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=create_response)
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_equal_to("success")
            assert_that(call_count).is_equal_to(3)

    @pytest.mark.asyncio
    async def test_max_retries_respected(self):
        """
        Given always empty responses
        When _make_request is called
        Then max_retries is respected and None is returned
        """
        call_count = 0

        async def always_empty(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return create_mock_response("")

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=3,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=always_empty)
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()
            assert_that(call_count).is_equal_to(3)


# =============================================================================
# Generate Initial Cards Tests
# =============================================================================


class TestGenerateInitialCards:
    """Tests for generate_initial_cards method."""

    @pytest.mark.asyncio
    async def test_success(self):
        """
        Given a successful API response
        When generate_initial_cards is called
        Then the response content is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.generate_initial_cards(
                question="Binary Search",
                json_schema={"type": "object"},
                prompt_template="Generate cards for {question}",
            )
            assert_that(result).is_equal_to(SAMPLE_CARD_RESPONSE)

    @pytest.mark.asyncio
    async def test_uses_custom_prompt_template(self):
        """
        Given a custom prompt template
        When generate_initial_cards is called
        Then the template is used with the question
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response('{"cards": []}')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = create_mock_client(response=mock_response)
            mock_get_client.return_value = mock_client

            await provider.generate_initial_cards(
                question="Test Question",
                json_schema={"type": "object"},
                prompt_template="Custom template for {question}",
            )

            call_args = mock_client.chat.completions.create.call_args[1]
            messages = call_args["messages"]
            assert_that(messages[1]["content"]).contains("Custom template for Test Question")

    @pytest.mark.asyncio
    async def test_empty_returns_empty_string(self):
        """
        Given an empty API response
        When generate_initial_cards is called
        Then an empty string is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )
        mock_response = create_mock_response("")

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.generate_initial_cards(
                question="Test",
                json_schema={},
            )
            assert_that(result).is_equal_to("")

    @pytest.mark.asyncio
    async def test_includes_system_message(self):
        """
        Given generate_initial_cards is called
        When checking the API call
        Then system message is included first
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response('{"cards": []}')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = create_mock_client(response=mock_response)
            mock_get_client.return_value = mock_client

            await provider.generate_initial_cards(
                question="Test",
                json_schema={},
            )

            call_args = mock_client.chat.completions.create.call_args[1]
            messages = call_args["messages"]
            assert_that(messages[0]["role"]).is_equal_to("system")
            assert_that(messages[0]["content"]).contains("Anki cards")


# =============================================================================
# Combine Cards Tests
# =============================================================================


class TestCombineCards:
    """Tests for combine_cards method."""

    @pytest.mark.asyncio
    async def test_success(self):
        """
        Given a successful API response
        When combine_cards is called
        Then the response content is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.combine_cards(
                question="Binary Search",
                combined_inputs="Set 1:\n{...}\n\nSet 2:\n{...}",
                json_schema={"type": "object"},
                combine_prompt_template="Combine: {inputs}",
            )
            assert_that(result).is_equal_to(SAMPLE_CARD_RESPONSE)

    @pytest.mark.asyncio
    async def test_uses_custom_combine_template(self):
        """
        Given a custom combine template
        When combine_cards is called
        Then the template is used in the message
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response('{"cards": []}')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = create_mock_client(response=mock_response)
            mock_get_client.return_value = mock_client

            await provider.combine_cards(
                question="Test",
                combined_inputs="input1\ninput2",
                json_schema={},
                combine_prompt_template="Custom combine: {inputs}",
            )

            call_args = mock_client.chat.completions.create.call_args[1]
            messages = call_args["messages"]
            assert_that(messages[1]["content"]).contains("Custom combine:")

    @pytest.mark.asyncio
    async def test_returns_none_on_failure(self):
        """
        Given an API error
        When combine_cards is called
        Then None is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(
                side_effect=Exception("error")
            )

            result = await provider.combine_cards(
                question="Test",
                combined_inputs="inputs",
                json_schema={},
            )
            assert_that(result).is_none()


# =============================================================================
# Format JSON Tests
# =============================================================================


class TestFormatJSON:
    """Tests for format_json method."""

    @pytest.mark.asyncio
    async def test_success(self):
        """
        Given a successful API response with valid JSON
        When format_json is called
        Then parsed JSON dict is returned
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="Some raw content to format",
                json_schema={"type": "object"},
            )
            assert_that(result).is_equal_to(SAMPLE_CARD_RESPONSE_DICT)

    @pytest.mark.asyncio
    async def test_retries_on_invalid_json(self):
        """
        Given invalid JSON responses followed by valid JSON
        When format_json is called
        Then retries and returns valid parsed JSON
        """
        call_count = 0

        async def create_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return create_mock_response("invalid json")
            return create_mock_response(SAMPLE_CARD_RESPONSE)

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            json_parse_retries=5,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=create_response)
            mock_get_client.return_value = mock_client

            result = await provider.format_json(
                raw_content="Content",
                json_schema={},
            )
            assert_that(result).is_equal_to(SAMPLE_CARD_RESPONSE_DICT)
            assert_that(call_count).is_equal_to(3)

    @pytest.mark.asyncio
    async def test_returns_none_after_max_retries(self):
        """
        Given always invalid JSON responses
        When format_json is called
        Then None is returned after max retries
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            json_parse_retries=2,
        )
        mock_response = create_mock_response("not valid json")

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="Content",
                json_schema={},
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_raises_retryable_error_on_empty_response(self):
        """
        Given an empty response after retries
        When format_json is called
        Then RetryableError is raised
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
            json_parse_retries=1,
        )
        mock_response = create_mock_response("")

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            with pytest.raises(RetryableError, match="Empty response"):
                await provider.format_json(
                    raw_content="Content",
                    json_schema={},
                )


# =============================================================================
# Unicode and Special Content Tests
# =============================================================================


class TestUnicodeHandling:
    """Tests for Unicode content handling."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("content", [
        '{"title": "中文标题", "cards": []}',  # Chinese
        '{"title": "العربية", "cards": []}',  # Arabic
        '{"title": "עברית", "cards": []}',  # Hebrew
        '{"title": "🎉 Emoji 🚀", "cards": []}',  # Emoji
        '{"title": "Ñoño español", "cards": []}',  # Spanish
        '{"title": "日本語テスト", "cards": []}',  # Japanese
        '{"title": "한국어", "cards": []}',  # Korean
    ])
    async def test_unicode_response_handling(self, content):
        """
        Given a response with Unicode content
        When _make_request is called
        Then Unicode is preserved in the response
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_equal_to(content)

    @pytest.mark.asyncio
    async def test_mixed_unicode_and_code(self):
        """
        Given content with mixed Unicode and code
        When _make_request is called
        Then all content is preserved correctly
        """
        content = '{"title": "算法 Algorithm", "code": "def foo():\\n    pass"}'
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_equal_to(content)


# =============================================================================
# Error Status Code Tests
# =============================================================================


class TestErrorStatusCodes:
    """Tests for various HTTP error status codes."""

    @pytest.mark.asyncio
    async def test_handles_400_bad_request(self):
        """
        Given a 400 Bad Request error
        When _make_request is called
        Then None is returned
        """
        from openai import BadRequestError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 400
        error = BadRequestError(
            message="Bad request",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_401_unauthorized(self):
        """
        Given a 401 Unauthorized error
        When _make_request is called
        Then None is returned
        """
        from openai import AuthenticationError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        error = AuthenticationError(
            message="Unauthorized",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_429_rate_limit(self):
        """
        Given a 429 Rate Limit error
        When _make_request is called
        Then None is returned
        """
        from openai import RateLimitError as OpenAIRateLimitError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        error = OpenAIRateLimitError(
            message="Rate limit",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_500_server_error(self):
        """
        Given a 500 Internal Server Error
        When _make_request is called
        Then None is returned
        """
        from openai import InternalServerError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        error = InternalServerError(
            message="Server error",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()


# =============================================================================
# Integration-Style Tests
# =============================================================================


class TestOpenAICompatibleProviderIntegration:
    """Integration-style tests for OpenAICompatibleProvider."""

    @pytest.fixture
    def provider(self):
        """Create a test provider instance."""
        return ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            api_keys=itertools.cycle(["key1", "key2"]),
            timeout=60.0,
            temperature=0.5,
        )

    def test_full_initialization(self, provider):
        """
        Given a fully configured provider
        When checking its properties
        Then all values are correctly set
        """
        assert_that(provider.model).is_equal_to("test-model")
        assert_that(provider.base_url).is_equal_to("https://api.test.com/v1")
        assert_that(provider.timeout).is_equal_to(60.0)
        assert_that(provider.temperature).is_equal_to(0.5)
        assert_that(provider.name).is_equal_to("test_provider")

    @pytest.mark.asyncio
    async def test_full_generate_flow(self, provider):
        """
        Given a mocked provider
        When running the full generate flow
        Then all steps complete successfully
        """
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            # Generate cards
            initial = await provider.generate_initial_cards(
                question="Test Question",
                json_schema={"type": "object"},
            )
            assert_that(initial).is_equal_to(SAMPLE_CARD_RESPONSE)

            # Combine cards
            combined = await provider.combine_cards(
                question="Test Question",
                combined_inputs=initial,
                json_schema={"type": "object"},
            )
            assert_that(combined).is_equal_to(SAMPLE_CARD_RESPONSE)

            # Format JSON
            formatted = await provider.format_json(
                raw_content=combined,
                json_schema={"type": "object"},
            )
            assert_that(formatted).is_equal_to(SAMPLE_CARD_RESPONSE_DICT)


# =============================================================================
# Additional Error Status Code Tests
# =============================================================================


class TestAdditionalErrorCodes:
    """Tests for additional HTTP error status codes."""

    @pytest.mark.asyncio
    async def test_handles_502_bad_gateway(self):
        """
        Given a 502 Bad Gateway error
        When _make_request is called
        Then None is returned
        """
        from openai import InternalServerError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 502
        error = InternalServerError(
            message="Bad Gateway",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_503_service_unavailable(self):
        """
        Given a 503 Service Unavailable error
        When _make_request is called
        Then None is returned
        """
        from openai import InternalServerError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 503
        error = InternalServerError(
            message="Service Unavailable",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_403_forbidden(self):
        """
        Given a 403 Forbidden error
        When _make_request is called
        Then None is returned
        """
        from openai import PermissionDeniedError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 403
        error = PermissionDeniedError(
            message="Forbidden",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_404_not_found(self):
        """
        Given a 404 Not Found error
        When _make_request is called
        Then None is returned
        """
        from openai import NotFoundError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 404
        error = NotFoundError(
            message="Not Found",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()

    @pytest.mark.asyncio
    async def test_handles_422_unprocessable_entity(self):
        """
        Given a 422 Unprocessable Entity error
        When _make_request is called
        Then None is returned
        """
        from openai import UnprocessableEntityError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 422
        error = UnprocessableEntityError(
            message="Unprocessable Entity",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_none()


# =============================================================================
# Message Formatting Tests
# =============================================================================


class TestMessageFormatting:
    """Tests for chat message formatting."""

    @pytest.mark.asyncio
    async def test_system_message_is_first(self):
        """
        Given generate_initial_cards is called
        When checking the chat messages
        Then the system message is first
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)
        captured_messages = []

        async def capture_call(*args, **kwargs):
            captured_messages.extend(kwargs.get("messages", []))
            return mock_response

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = capture_call
            mock_get_client.return_value = mock_client

            await provider.generate_initial_cards(
                question="Test",
                json_schema={},
            )

            assert_that(captured_messages[0]["role"]).is_equal_to("system")

    @pytest.mark.asyncio
    async def test_user_message_contains_question(self):
        """
        Given a question for card generation
        When generate_initial_cards is called
        Then the question appears in the user message
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)
        captured_messages = []

        async def capture_call(*args, **kwargs):
            captured_messages.extend(kwargs.get("messages", []))
            return mock_response

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = capture_call
            mock_get_client.return_value = mock_client

            await provider.generate_initial_cards(
                question="What is binary search?",
                json_schema={},
            )

            user_messages = [m for m in captured_messages if m["role"] == "user"]
            assert_that(len(user_messages)).is_greater_than_or_equal_to(1)
            assert_that(user_messages[-1]["content"]).contains("What is binary search?")

    @pytest.mark.asyncio
    async def test_combine_cards_includes_inputs(self):
        """
        Given combined inputs for card combination
        When combine_cards is called
        Then the inputs appear in the message content
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)
        captured_messages = []

        async def capture_call(*args, **kwargs):
            captured_messages.extend(kwargs.get("messages", []))
            return mock_response

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = capture_call
            mock_get_client.return_value = mock_client

            combined_inputs = "Card 1 content\n---\nCard 2 content"
            await provider.combine_cards(
                question="Test",
                combined_inputs=combined_inputs,
                json_schema={},
            )

            all_content = " ".join(m["content"] for m in captured_messages)
            assert_that(all_content).contains("Card 1 content")
            assert_that(all_content).contains("Card 2 content")


# =============================================================================
# Boundary and Edge Case Tests
# =============================================================================


class TestBoundaryConditions:
    """Tests for boundary conditions and edge cases."""

    @pytest.mark.asyncio
    async def test_zero_temperature(self):
        """
        Given temperature = 0
        When provider is created
        Then temperature is set to 0
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            temperature=0.0,
        )
        assert_that(provider.temperature).is_equal_to(0.0)

    @pytest.mark.asyncio
    async def test_max_temperature(self):
        """
        Given temperature = 2.0 (max typical value)
        When provider is created
        Then temperature is set correctly
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            temperature=2.0,
        )
        assert_that(provider.temperature).is_equal_to(2.0)

    @pytest.mark.asyncio
    async def test_minimum_timeout(self):
        """
        Given a very short timeout
        When provider is created
        Then timeout is set correctly
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            timeout=1.0,
        )
        assert_that(provider.timeout).is_equal_to(1.0)

    @pytest.mark.asyncio
    async def test_very_long_timeout(self):
        """
        Given a very long timeout
        When provider is created
        Then timeout is set correctly
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            timeout=600.0,
        )
        assert_that(provider.timeout).is_equal_to(600.0)

    @pytest.mark.asyncio
    async def test_empty_question(self):
        """
        Given an empty question string
        When generate_initial_cards is called
        Then the request still succeeds
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.generate_initial_cards(
                question="",
                json_schema={},
            )
            assert_that(result).is_equal_to(SAMPLE_CARD_RESPONSE)

    @pytest.mark.asyncio
    async def test_very_long_question(self):
        """
        Given a very long question string
        When generate_initial_cards is called
        Then the request still succeeds
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)
        long_question = "A" * 10000

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.generate_initial_cards(
                question=long_question,
                json_schema={},
            )
            assert_that(result).is_equal_to(SAMPLE_CARD_RESPONSE)

    @pytest.mark.asyncio
    async def test_whitespace_only_response_is_returned(self):
        """
        Given a whitespace-only response
        When _make_request is called
        Then the whitespace content is returned (not treated as empty)
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )
        whitespace_content = "   \n\t  "
        mock_response = create_mock_response(whitespace_content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            # Whitespace content is returned as-is, not treated as empty
            assert_that(result).is_equal_to(whitespace_content)

    @pytest.mark.asyncio
    async def test_single_max_retry(self):
        """
        Given max_retries = 1
        When provider is created
        Then max_retries is set correctly
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )
        assert_that(provider.max_retries).is_equal_to(1)

    @pytest.mark.asyncio
    async def test_high_max_retries(self):
        """
        Given a high max_retries value
        When provider is created
        Then max_retries is set correctly
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=10,
        )
        assert_that(provider.max_retries).is_equal_to(10)


# =============================================================================
# API Request Parameter Tests
# =============================================================================


class TestAPIRequestParameters:
    """Tests for API request parameter handling."""

    @pytest.mark.asyncio
    async def test_model_passed_to_api(self):
        """
        Given a configured model name
        When _make_request is called
        Then the model is passed to the API
        """
        provider = ConcreteOpenAIProvider(
            model="custom-model-v2",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)
        captured_kwargs = {}

        async def capture_call(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = capture_call
            mock_get_client.return_value = mock_client

            await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )

            assert_that(captured_kwargs.get("model")).is_equal_to("custom-model-v2")

    @pytest.mark.asyncio
    async def test_temperature_passed_to_api(self):
        """
        Given a configured temperature
        When _make_request is called
        Then the temperature is passed to the API
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            temperature=0.8,
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)
        captured_kwargs = {}

        async def capture_call(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = capture_call
            mock_get_client.return_value = mock_client

            await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )

            assert_that(captured_kwargs.get("temperature")).is_equal_to(0.8)

    @pytest.mark.asyncio
    async def test_max_tokens_passed_to_api(self):
        """
        Given a configured max_tokens
        When _make_request is called
        Then max_tokens is passed to the API
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_tokens=2000,
        )
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)
        captured_kwargs = {}

        async def capture_call(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = capture_call
            mock_get_client.return_value = mock_client

            await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )

            assert_that(captured_kwargs.get("max_tokens")).is_equal_to(2000)

    @pytest.mark.asyncio
    async def test_json_schema_triggers_strip_json_block(self):
        """
        Given strip_json_markers=True and json_schema
        When _make_request is called with wrapped JSON content
        Then JSON markers are stripped from the response
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            strip_json_markers=True,
        )
        # Content wrapped in JSON markers
        wrapped_content = '```json\n{"cards": []}\n```'
        mock_response = create_mock_response(wrapped_content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema={"type": "object"},
            )

            # Markers should be stripped when json_schema is provided
            assert_that(result).is_equal_to('{"cards": []}')


# =============================================================================
# Concurrent and Async Behavior Tests
# =============================================================================


class TestConcurrentBehavior:
    """Tests for concurrent and async behavior."""

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self):
        """
        Given a provider
        When multiple sequential requests are made
        Then each request returns the correct response
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            api_keys=itertools.cycle(["key1", "key2"]),
        )

        responses = [
            create_mock_response('{"card": 1}'),
            create_mock_response('{"card": 2}'),
            create_mock_response('{"card": 3}'),
        ]
        call_count = 0

        async def multi_response(*args, **kwargs):
            nonlocal call_count
            response = responses[call_count % len(responses)]
            call_count += 1
            return response

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = multi_response
            mock_get_client.return_value = mock_client

            results = []
            for i in range(3):
                result = await provider._make_request(
                    chat_messages=[{"role": "user", "content": f"test {i}"}],
                )
                results.append(result)

            assert_that(results).is_equal_to(['{"card": 1}', '{"card": 2}', '{"card": 3}'])

    @pytest.mark.asyncio
    async def test_key_rotation_on_sequential_requests(self):
        """
        Given a provider with multiple API keys
        When sequential requests are made
        Then API keys are rotated
        """
        keys = ["key1", "key2", "key3"]
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            api_keys=itertools.cycle(keys),
        )

        used_keys = []

        with patch("src.providers.openai_compatible.AsyncOpenAI") as mock_openai:
            mock_response = create_mock_response('{"result": "ok"}')
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            def capture_key(*args, **kwargs):
                used_keys.append(kwargs.get("api_key"))
                return mock_client

            mock_openai.side_effect = capture_key

            for _ in range(3):
                await provider._make_request(
                    chat_messages=[{"role": "user", "content": "test"}],
                )

            assert_that(used_keys).is_equal_to(["key1", "key2", "key3"])

    @pytest.mark.asyncio
    async def test_parallel_requests_share_key_iterator(self):
        """
        Given a provider with multiple API keys
        When parallel requests are made
        Then keys are drawn from the shared iterator
        """
        import asyncio

        keys = ["key1", "key2", "key3", "key4"]
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            api_keys=itertools.cycle(keys),
        )

        used_keys = []

        with patch("src.providers.openai_compatible.AsyncOpenAI") as mock_openai:
            mock_response = create_mock_response('{"result": "ok"}')

            async def delayed_response(*args, **kwargs):
                await asyncio.sleep(0.01)
                return mock_response

            def capture_key(*args, **kwargs):
                used_keys.append(kwargs.get("api_key"))
                mock_client = AsyncMock()
                mock_client.chat.completions.create = delayed_response
                return mock_client

            mock_openai.side_effect = capture_key

            # Run 4 requests in parallel
            tasks = [
                provider._make_request(
                    chat_messages=[{"role": "user", "content": f"test {i}"}],
                )
                for i in range(4)
            ]
            await asyncio.gather(*tasks)

            # All keys should have been used
            assert_that(set(used_keys)).is_equal_to(set(keys))


# =============================================================================
# Response Content Validation Tests
# =============================================================================


class TestResponseContentValidation:
    """Tests for response content validation and processing."""

    @pytest.mark.asyncio
    async def test_strips_leading_trailing_whitespace(self):
        """
        Given a response with leading/trailing whitespace
        When _make_request is called
        Then the content is returned with whitespace preserved (but can be stripped)
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response('  \n  {"cards": []}  \n  ')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema={"type": "object"},
            )
            # Content should be stripped
            assert_that(result.strip()).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_preserves_internal_whitespace(self):
        """
        Given content with internal whitespace
        When _make_request is called
        Then internal whitespace is preserved
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        content_with_whitespace = '{"text": "line1\\nline2\\n\\nline3"}'
        mock_response = create_mock_response(content_with_whitespace)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert_that(result).is_equal_to(content_with_whitespace)

    @pytest.mark.asyncio
    async def test_handles_nested_json_markers(self):
        """
        Given content with nested JSON code markers
        When _make_request is called with json_schema
        Then outer markers are stripped appropriately
        """
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        nested_content = '```json\n```json\n{"cards": []}\n```\n```'
        mock_response = create_mock_response(nested_content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema={"type": "object"},
            )
            # Should strip outer markers
            assert_that(result.count("```")).is_less_than(nested_content.count("```"))
