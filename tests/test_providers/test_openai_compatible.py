"""Tests for providers/openai_compatible.py."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import itertools

from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.base import RateLimitError, TimeoutError, EmptyResponseError

from conftest import SAMPLE_CARD_RESPONSE, SAMPLE_CARD_RESPONSE_DICT


class ConcreteOpenAIProvider(OpenAICompatibleProvider):
    """Concrete implementation for testing."""

    @property
    def name(self) -> str:
        return "test_provider"


class TestOpenAICompatibleProvider:
    """Tests for OpenAICompatibleProvider class."""

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

    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.model == "test-model"
        assert provider.base_url == "https://api.test.com/v1"
        assert provider.timeout == 60.0
        assert provider.temperature == 0.5
        assert provider.name == "test_provider"

    def test_init_with_defaults(self):
        """Test provider initialization with defaults."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
        )

        assert provider.max_retries == 5
        assert provider.json_parse_retries == 5
        assert provider.strip_json_markers is True
        assert provider.max_tokens is None

    def test_init_with_custom_retries(self):
        """Test provider with custom retry settings."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            max_retries=3,
            json_parse_retries=2,
        )

        assert provider.max_retries == 3
        assert provider.json_parse_retries == 2

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

    def test_get_extra_request_params(self):
        """Test getting extra request parameters."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
            top_p=0.9,
            extra_params={"custom_param": "value"},
        )

        params = provider._get_extra_request_params()

        assert params["top_p"] == 0.9
        assert params["custom_param"] == "value"

    def test_get_extra_request_params_empty(self):
        """Test getting extra params when none set."""
        provider = ConcreteOpenAIProvider(
            model="model",
            base_url="https://api.test.com/v1",
        )

        params = provider._get_extra_request_params()
        assert params == {}


class TestGenerateInitialCards:
    """Tests for generate_initial_cards method."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock OpenAI response."""
        mock_choice = MagicMock()
        mock_choice.message.content = SAMPLE_CARD_RESPONSE

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        return mock_completion

    @pytest.mark.asyncio
    async def test_generate_initial_cards_success(self, mock_response):
        """Test successful card generation."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Binary Search",
                json_schema={"type": "object"},
                prompt_template="Generate cards for {question}",
            )

            assert result == SAMPLE_CARD_RESPONSE
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_initial_cards_empty_returns_empty_string(self):
        """Test that empty response returns empty string."""
        mock_choice = MagicMock()
        mock_choice.message.content = ""

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test",
                json_schema={},
            )

            # Empty response after retries exhausted
            assert result == ""


class TestCombineCards:
    """Tests for combine_cards method."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock OpenAI response."""
        mock_choice = MagicMock()
        mock_choice.message.content = SAMPLE_CARD_RESPONSE

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        return mock_completion

    @pytest.mark.asyncio
    async def test_combine_cards_success(self, mock_response):
        """Test successful card combining."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.combine_cards(
                question="Binary Search",
                combined_inputs="Set 1:\n{...}\n\nSet 2:\n{...}",
                json_schema={"type": "object"},
                combine_prompt_template="Combine: {inputs}",
            )

            assert result == SAMPLE_CARD_RESPONSE


class TestFormatJson:
    """Tests for format_json method."""

    @pytest.mark.asyncio
    async def test_format_json_success(self):
        """Test successful JSON formatting."""
        mock_choice = MagicMock()
        mock_choice.message.content = SAMPLE_CARD_RESPONSE

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
            mock_get_client.return_value = mock_client

            result = await provider.format_json(
                raw_content="Some raw content to format",
                json_schema={"type": "object"},
            )

            assert result == SAMPLE_CARD_RESPONSE_DICT

    @pytest.mark.asyncio
    async def test_format_json_retries_on_invalid_json(self):
        """Test that format_json retries on invalid JSON."""
        call_count = 0

        async def create_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_choice = MagicMock()
            if call_count < 3:
                mock_choice.message.content = "invalid json"
            else:
                mock_choice.message.content = SAMPLE_CARD_RESPONSE
            mock_completion = MagicMock()
            mock_completion.choices = [mock_choice]
            return mock_completion

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


class TestMakeRequest:
    """Tests for _make_request method."""

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """Test successful request."""
        mock_choice = MagicMock()
        mock_choice.message.content = "response content"

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )

            assert result == "response content"

    @pytest.mark.asyncio
    async def test_make_request_strips_json_markers(self):
        """Test that JSON markers are stripped when enabled."""
        mock_choice = MagicMock()
        mock_choice.message.content = '```json\n{"key": "value"}\n```'

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            strip_json_markers=True,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
                json_schema={"type": "object"},  # json_schema triggers stripping
            )

            assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_make_request_handles_rate_limit(self):
        """Test handling of rate limit errors."""
        from openai import RateLimitError as OpenAIRateLimitError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()

            # Create a proper mock for the rate limit error
            mock_response = MagicMock()
            mock_response.status_code = 429

            error = OpenAIRateLimitError(
                message="Rate limit exceeded",
                response=mock_response,
                body=None,
            )
            mock_client.chat.completions.create = AsyncMock(side_effect=error)
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )

            # Should return None after retries exhausted
            assert result is None

    @pytest.mark.asyncio
    async def test_make_request_with_max_tokens(self):
        """Test request includes max_tokens when set."""
        mock_choice = MagicMock()
        mock_choice.message.content = "response"

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_tokens=4096,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
            mock_get_client.return_value = mock_client

            await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )

            # Verify max_tokens was passed
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["max_tokens"] == 4096


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
