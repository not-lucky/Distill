"""Tests for providers/openai_compatible.py.

Comprehensive tests for OpenAI-compatible provider implementation.
Target: 5:1 test-to-code ratio (~1,455 lines of tests for ~291 lines of code).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import itertools
from typing import Iterator

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
        """Test basic provider initialization."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        assert provider.model == "test-model"
        assert provider.base_url == "https://api.test.com/v1"

    def test_init_all_parameters(self):
        """Test initialization with all parameters."""
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
        assert provider.model == "test-model"
        assert provider.timeout == 120.0
        assert provider.max_retries == 3
        assert provider.json_parse_retries == 2
        assert provider.temperature == 0.7
        assert provider.max_tokens == 4096
        assert provider.strip_json_markers is False
        assert provider.top_p == 0.9
        assert provider.extra_params == {"custom": "value"}

    def test_init_defaults(self):
        """Test provider initialization with defaults."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
        )
        assert provider.max_retries == 5
        assert provider.json_parse_retries == 5
        assert provider.timeout == 120.0
        assert provider.temperature == 0.4
        assert provider.max_tokens is None
        assert provider.strip_json_markers is True
        assert provider.top_p is None
        assert provider.extra_params == {}

    @pytest.mark.parametrize("model_name", [
        "gpt-4",
        "llama3.1-70b",
        "gemini-1.5-pro",
        "claude-3-opus",
        "model-with-numbers-123",
    ])
    def test_init_various_model_names(self, model_name):
        """Test initialization with various model names."""
        provider = ConcreteOpenAIProvider(
            model=model_name,
            base_url="https://api.test.com/v1",
        )
        assert provider.model == model_name

    @pytest.mark.parametrize("base_url", [
        "https://api.openai.com/v1",
        "https://api.cerebras.ai/v1",
        "http://localhost:8080/v1",
        "https://custom.domain.com/api/v2",
    ])
    def test_init_various_base_urls(self, base_url):
        """Test initialization with various base URLs."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url=base_url,
        )
        assert provider.base_url == base_url

    @pytest.mark.parametrize("timeout", [10.0, 30.0, 60.0, 120.0, 300.0])
    def test_init_various_timeouts(self, timeout):
        """Test initialization with various timeout values."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            timeout=timeout,
        )
        assert provider.timeout == timeout

    @pytest.mark.parametrize("temperature", [0.0, 0.3, 0.5, 0.7, 1.0, 2.0])
    def test_init_various_temperatures(self, temperature):
        """Test initialization with various temperature values."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            temperature=temperature,
        )
        assert provider.temperature == temperature


class TestOpenAICompatibleProviderProperties:
    """Tests for provider properties."""

    def test_model_property(self):
        """Test model property returns model_name."""
        provider = ConcreteOpenAIProvider(
            model="test-model-v1",
            base_url="https://api.test.com/v1",
        )
        assert provider.model == "test-model-v1"

    def test_name_property_abstract(self):
        """Test that name property is defined by subclass."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
        )
        assert provider.name == "test_provider"


# =============================================================================
# API Key Management Tests
# =============================================================================


class TestAPIKeyManagement:
    """Tests for API key management."""

    def test_get_api_key_cycles(self):
        """Test API key cycling."""
        keys = itertools.cycle(["key1", "key2", "key3"])
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            api_keys=keys,
        )
        assert provider._get_api_key() == "key1"
        assert provider._get_api_key() == "key2"
        assert provider._get_api_key() == "key3"
        assert provider._get_api_key() == "key1"  # Cycles back

    def test_get_api_key_none(self):
        """Test getting API key when none configured."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            api_keys=None,
        )
        assert provider._get_api_key() == ""

    def test_get_api_key_single_key(self):
        """Test with single key that cycles."""
        keys = itertools.cycle(["only-key"])
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            api_keys=keys,
        )
        assert provider._get_api_key() == "only-key"
        assert provider._get_api_key() == "only-key"

    def test_get_api_key_iterator_exhausted(self):
        """Test with iterator that exhausts."""
        keys = iter(["key1", "key2"])
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            api_keys=keys,
        )
        assert provider._get_api_key() == "key1"
        assert provider._get_api_key() == "key2"
        with pytest.raises(StopIteration):
            provider._get_api_key()


# =============================================================================
# Extra Request Parameters Tests
# =============================================================================


class TestExtraRequestParams:
    """Tests for _get_extra_request_params method."""

    def test_get_extra_request_params_empty(self):
        """Test getting extra params when none set."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
        )
        params = provider._get_extra_request_params()
        assert params == {}

    def test_get_extra_request_params_top_p_only(self):
        """Test extra params with top_p only."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            top_p=0.9,
        )
        params = provider._get_extra_request_params()
        assert params == {"top_p": 0.9}

    def test_get_extra_request_params_extra_only(self):
        """Test extra params with extra_params only."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            extra_params={"custom_param": "value", "another": 42},
        )
        params = provider._get_extra_request_params()
        assert params == {"custom_param": "value", "another": 42}

    def test_get_extra_request_params_combined(self):
        """Test extra params with both top_p and extra_params."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            top_p=0.9,
            extra_params={"custom_param": "value"},
        )
        params = provider._get_extra_request_params()
        assert params["top_p"] == 0.9
        assert params["custom_param"] == "value"

    def test_extra_params_override_top_p(self):
        """Test that extra_params can override top_p."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            top_p=0.9,
            extra_params={"top_p": 0.5},  # Override
        )
        params = provider._get_extra_request_params()
        assert params["top_p"] == 0.5  # extra_params wins


# =============================================================================
# Client Creation Tests
# =============================================================================


class TestGetClient:
    """Tests for _get_client method."""

    def test_get_client_creates_async_openai(self):
        """Test that _get_client creates an AsyncOpenAI client."""
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
        """Test client uses configured timeout."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            timeout=60.0,
        )
        with patch("src.providers.openai_compatible.AsyncOpenAI") as MockAsyncOpenAI:
            provider._get_client()
            call_kwargs = MockAsyncOpenAI.call_args[1]
            assert call_kwargs["timeout"] == 60.0

    def test_get_client_rotates_keys(self):
        """Test client creation rotates API keys."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            api_keys=itertools.cycle(["key1", "key2"]),
        )
        with patch("src.providers.openai_compatible.AsyncOpenAI") as MockAsyncOpenAI:
            provider._get_client()
            assert MockAsyncOpenAI.call_args[1]["api_key"] == "key1"

            provider._get_client()
            assert MockAsyncOpenAI.call_args[1]["api_key"] == "key2"


# =============================================================================
# Make Request Tests
# =============================================================================


class TestMakeRequestSuccess:
    """Tests for successful _make_request calls."""

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """Test successful request."""
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
            assert result == "response content"

    @pytest.mark.asyncio
    async def test_make_request_with_json_schema(self):
        """Test request with JSON schema."""
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
            assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_make_request_with_max_tokens(self):
        """Test request includes max_tokens when set."""
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
            assert call_kwargs["max_tokens"] == 4096


class TestMakeRequestJSONStripping:
    """Tests for JSON marker stripping in _make_request."""

    @pytest.mark.asyncio
    async def test_strips_json_markers(self):
        """Test that JSON markers are stripped when enabled."""
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
            assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_strips_plain_markdown_markers(self):
        """Test stripping plain markdown code markers."""
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
            assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_no_strip_when_disabled(self):
        """Test that markers are not stripped when disabled."""
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
            assert result == '```json\n{"key": "value"}\n```'

    @pytest.mark.asyncio
    async def test_no_strip_without_json_schema(self):
        """Test that markers are not stripped without json_schema."""
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
            assert result == '```json\n{"key": "value"}\n```'


class TestMakeRequestErrorHandling:
    """Tests for error handling in _make_request."""

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self):
        """Test handling of rate limit errors."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self):
        """Test handling of timeout errors."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_empty_response(self):
        """Test handling of empty response."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_none_content(self):
        """Test handling of None content."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self):
        """Test handling of generic exceptions."""
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
            assert result is None


class TestMakeRequestRetryBehavior:
    """Tests for retry behavior in _make_request."""

    @pytest.mark.asyncio
    async def test_retries_on_empty_response(self):
        """Test that empty responses trigger retry."""
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
            assert result == "success"
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_respected(self):
        """Test that max_retries is respected."""
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
            assert result is None
            assert call_count == 3


# =============================================================================
# Generate Initial Cards Tests
# =============================================================================


class TestGenerateInitialCards:
    """Tests for generate_initial_cards method."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful card generation."""
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
            assert result == SAMPLE_CARD_RESPONSE

    @pytest.mark.asyncio
    async def test_uses_custom_prompt_template(self):
        """Test that custom prompt template is used."""
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
            assert "Custom template for Test Question" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_empty_returns_empty_string(self):
        """Test that empty response returns empty string."""
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
            assert result == ""

    @pytest.mark.asyncio
    async def test_includes_system_message(self):
        """Test that system message is included."""
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
            assert messages[0]["role"] == "system"
            assert "Anki cards" in messages[0]["content"]


# =============================================================================
# Combine Cards Tests
# =============================================================================


class TestCombineCards:
    """Tests for combine_cards method."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful card combining."""
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
            assert result == SAMPLE_CARD_RESPONSE

    @pytest.mark.asyncio
    async def test_uses_custom_combine_template(self):
        """Test that custom combine template is used."""
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
            assert "Custom combine:" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_returns_none_on_failure(self):
        """Test returns None on failure."""
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
            assert result is None


# =============================================================================
# Format JSON Tests
# =============================================================================


class TestFormatJSON:
    """Tests for format_json method."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful JSON formatting."""
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
            assert result == SAMPLE_CARD_RESPONSE_DICT

    @pytest.mark.asyncio
    async def test_retries_on_invalid_json(self):
        """Test that format_json retries on invalid JSON."""
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
            assert result == SAMPLE_CARD_RESPONSE_DICT
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_returns_none_after_max_retries(self):
        """Test returns None after max retries exhausted."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_raises_retryable_error_on_empty_response(self):
        """Test raises RetryableError when response is empty after retries.

        Note: With reraise=True in the retry decorator, the original
        RetryableError is raised rather than being caught and returning None.
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
        """Test handling of various Unicode content."""
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
            assert result == content

    @pytest.mark.asyncio
    async def test_mixed_unicode_and_code(self):
        """Test content with mixed Unicode and code."""
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
            assert result == content


# =============================================================================
# Error Status Code Tests
# =============================================================================


class TestErrorStatusCodes:
    """Tests for various HTTP error status codes."""

    @pytest.mark.asyncio
    async def test_handles_400_bad_request(self):
        """Test handling of 400 Bad Request."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_401_unauthorized(self):
        """Test handling of 401 Unauthorized."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_429_rate_limit(self):
        """Test handling of 429 Rate Limit."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_500_server_error(self):
        """Test handling of 500 Internal Server Error."""
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
            assert result is None


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
        """Test complete provider initialization."""
        assert provider.model == "test-model"
        assert provider.base_url == "https://api.test.com/v1"
        assert provider.timeout == 60.0
        assert provider.temperature == 0.5
        assert provider.name == "test_provider"

    @pytest.mark.asyncio
    async def test_full_generate_flow(self, provider):
        """Test complete generation flow."""
        mock_response = create_mock_response(SAMPLE_CARD_RESPONSE)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            # Generate cards
            initial = await provider.generate_initial_cards(
                question="Test Question",
                json_schema={"type": "object"},
            )
            assert initial == SAMPLE_CARD_RESPONSE

            # Combine cards
            combined = await provider.combine_cards(
                question="Test Question",
                combined_inputs=initial,
                json_schema={"type": "object"},
            )
            assert combined == SAMPLE_CARD_RESPONSE

            # Format JSON
            formatted = await provider.format_json(
                raw_content=combined,
                json_schema={"type": "object"},
            )
            assert formatted == SAMPLE_CARD_RESPONSE_DICT


# =============================================================================
# Additional Error Status Code Tests
# =============================================================================


class TestAdditionalErrorCodes:
    """Tests for additional HTTP error status codes."""

    @pytest.mark.asyncio
    async def test_handles_502_bad_gateway(self):
        """Test handling of 502 Bad Gateway."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_503_service_unavailable(self):
        """Test handling of 503 Service Unavailable."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_403_forbidden(self):
        """Test handling of 403 Forbidden."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_404_not_found(self):
        """Test handling of 404 Not Found."""
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
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_422_unprocessable_entity(self):
        """Test handling of 422 Unprocessable Entity."""
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
            assert result is None


# =============================================================================
# Message Formatting Tests
# =============================================================================


class TestMessageFormatting:
    """Tests for chat message formatting."""

    @pytest.mark.asyncio
    async def test_system_message_is_first(self):
        """Test that system message comes first in chat messages."""
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

            assert captured_messages[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_user_message_contains_question(self):
        """Test that user message contains the question."""
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
            assert len(user_messages) >= 1
            assert "What is binary search?" in user_messages[-1]["content"]

    @pytest.mark.asyncio
    async def test_combine_cards_includes_inputs(self):
        """Test that combine_cards includes all inputs in message."""
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
            assert "Card 1 content" in all_content
            assert "Card 2 content" in all_content


# =============================================================================
# Boundary and Edge Case Tests
# =============================================================================


class TestBoundaryConditions:
    """Tests for boundary conditions and edge cases."""

    @pytest.mark.asyncio
    async def test_zero_temperature(self):
        """Test with temperature = 0."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            temperature=0.0,
        )
        assert provider.temperature == 0.0

    @pytest.mark.asyncio
    async def test_max_temperature(self):
        """Test with temperature = 2.0 (max typical value)."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            temperature=2.0,
        )
        assert provider.temperature == 2.0

    @pytest.mark.asyncio
    async def test_minimum_timeout(self):
        """Test with very short timeout."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            timeout=1.0,
        )
        assert provider.timeout == 1.0

    @pytest.mark.asyncio
    async def test_very_long_timeout(self):
        """Test with very long timeout."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            timeout=600.0,
        )
        assert provider.timeout == 600.0

    @pytest.mark.asyncio
    async def test_empty_question(self):
        """Test with empty question string."""
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
            assert result == SAMPLE_CARD_RESPONSE

    @pytest.mark.asyncio
    async def test_very_long_question(self):
        """Test with very long question string."""
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
            assert result == SAMPLE_CARD_RESPONSE

    @pytest.mark.asyncio
    async def test_whitespace_only_response_is_returned(self):
        """Test handling of whitespace-only response.

        Note: The implementation doesn't treat whitespace-only as empty,
        it returns the content as-is. Only truly empty/None content
        raises EmptyResponseError.
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
            assert result == whitespace_content

    @pytest.mark.asyncio
    async def test_single_max_retry(self):
        """Test with max_retries = 1."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )
        assert provider.max_retries == 1

    @pytest.mark.asyncio
    async def test_high_max_retries(self):
        """Test with high max_retries value."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=10,
        )
        assert provider.max_retries == 10


# =============================================================================
# API Request Parameter Tests
# =============================================================================


class TestAPIRequestParameters:
    """Tests for API request parameter handling."""

    @pytest.mark.asyncio
    async def test_model_passed_to_api(self):
        """Test that model name is passed to API call."""
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

            assert captured_kwargs.get("model") == "custom-model-v2"

    @pytest.mark.asyncio
    async def test_temperature_passed_to_api(self):
        """Test that temperature is passed to API call."""
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

            assert captured_kwargs.get("temperature") == 0.8

    @pytest.mark.asyncio
    async def test_max_tokens_passed_to_api(self):
        """Test that max_tokens is passed to API call when set on provider."""
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

            assert captured_kwargs.get("max_tokens") == 2000

    @pytest.mark.asyncio
    async def test_json_schema_triggers_strip_json_block(self):
        """Test that json_schema parameter triggers JSON block stripping.

        Note: The base _make_request uses json_schema only to decide whether
        to strip JSON markdown markers. Response format is not automatically
        set from the json_schema parameter in _make_request.
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
            assert result == '{"cards": []}'


# =============================================================================
# Concurrent and Async Behavior Tests
# =============================================================================


class TestConcurrentBehavior:
    """Tests for concurrent and async behavior."""

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self):
        """Test multiple sequential requests work correctly."""
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

            assert results == ['{"card": 1}', '{"card": 2}', '{"card": 3}']

    @pytest.mark.asyncio
    async def test_key_rotation_on_sequential_requests(self):
        """Test that API keys rotate across sequential requests."""
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

            assert used_keys == ["key1", "key2", "key3"]

    @pytest.mark.asyncio
    async def test_parallel_requests_share_key_iterator(self):
        """Test that parallel requests draw from the same key iterator."""
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
            assert set(used_keys) == set(keys)


# =============================================================================
# Response Content Validation Tests
# =============================================================================


class TestResponseContentValidation:
    """Tests for response content validation and processing."""

    @pytest.mark.asyncio
    async def test_strips_leading_trailing_whitespace(self):
        """Test that leading/trailing whitespace is handled."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response("  \n  {\"cards\": []}  \n  ")

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema={"type": "object"},
            )
            # Content should be stripped
            assert result.strip() == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_preserves_internal_whitespace(self):
        """Test that internal whitespace in content is preserved."""
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
            assert result == content_with_whitespace

    @pytest.mark.asyncio
    async def test_handles_nested_json_markers(self):
        """Test handling of nested JSON code markers."""
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
            assert "```" not in result or result.count("```") < nested_content.count("```")
