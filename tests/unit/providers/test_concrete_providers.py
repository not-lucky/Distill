"""Tests for all concrete LLM providers.

This module tests all concrete provider implementations including:
- OpenAI-compatible providers: NVIDIA, OpenRouter, Baseten, Canopywave, GoogleAntigravity
- Native SDK providers: Cerebras, GoogleGenAI, G4F, Gemini
"""

import itertools
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from assertpy import assert_that


# =============================================================================
# OpenAI-Compatible Provider Tests (thin wrappers)
# =============================================================================


class TestNvidiaProvider:
    """Tests for NvidiaProvider."""

    def test_init_default_parameters(self):
        """
        Given default initialization parameters
        When NvidiaProvider is created
        Then all default values are set correctly
        """
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert_that(provider.model).is_equal_to("test-model")
        assert_that(provider.base_url).is_equal_to("https://integrate.api.nvidia.com/v1")
        assert_that(provider.timeout).is_equal_to(900.0)
        assert_that(provider.temperature).is_equal_to(0.4)
        assert_that(provider.max_tokens).is_equal_to(16384)
        assert_that(provider.top_p).is_equal_to(0.95)

    def test_init_custom_parameters(self):
        """
        Given custom initialization parameters
        When NvidiaProvider is created
        Then all custom values are set correctly
        """
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="custom-model",
            base_url="https://custom.nvidia.com/v1",
            timeout=120.0,
            temperature=0.7,
            max_tokens=8192,
            top_p=0.8,
            max_retries=3,
            json_parse_retries=2,
        )

        assert_that(provider.model).is_equal_to("custom-model")
        assert_that(provider.base_url).is_equal_to("https://custom.nvidia.com/v1")
        assert_that(provider.timeout).is_equal_to(120.0)
        assert_that(provider.temperature).is_equal_to(0.7)
        assert_that(provider.max_tokens).is_equal_to(8192)
        assert_that(provider.top_p).is_equal_to(0.8)
        assert_that(provider.max_retries).is_equal_to(3)
        assert_that(provider.json_parse_retries).is_equal_to(2)

    def test_name_property(self):
        """
        Given an initialized NvidiaProvider
        When the name property is accessed
        Then the correct provider name is returned
        """
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert_that(provider.name).is_equal_to("llm2deck_nvidia")

    def test_extra_body_chat_template_kwargs(self):
        """
        Given an initialized NvidiaProvider
        When extra request params are retrieved
        Then thinking is enabled in chat_template_kwargs
        """
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        extra_params = provider._get_extra_request_params()
        assert_that(extra_params).contains_key("extra_body")
        assert_that(extra_params["extra_body"]["chat_template_kwargs"]["thinking"]).is_true()

    def test_extra_params_merged(self):
        """
        Given extra_params in initialization
        When extra request params are retrieved
        Then custom params are merged with defaults
        """
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            extra_params={"custom_param": "value"},
        )

        extra_params = provider._get_extra_request_params()
        assert_that(extra_params).contains_key("extra_body")
        assert_that(extra_params).contains_key("custom_param")


class TestOpenRouterProvider:
    """Tests for OpenRouterProvider."""

    def test_init_default_parameters(self):
        """
        Given default initialization parameters
        When OpenRouterProvider is created
        Then all default values are set correctly
        """
        from src.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert_that(provider.model).is_equal_to("test-model")
        assert_that(provider.base_url).is_equal_to("https://openrouter.ai/api/v1")
        assert_that(provider.timeout).is_equal_to(120.0)
        assert_that(provider.temperature).is_equal_to(0.4)
        assert_that(provider.max_tokens).is_none()
        assert_that(provider.max_retries).is_equal_to(3)

    def test_init_custom_parameters(self):
        """
        Given custom initialization parameters
        When OpenRouterProvider is created
        Then all custom values are set correctly
        """
        from src.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(
            api_keys=itertools.cycle(["key1"]),
            model="openai/gpt-4",
            base_url="https://custom.openrouter.ai/api/v1",
            timeout=60.0,
            temperature=0.5,
            max_tokens=4096,
            max_retries=5,
            json_parse_retries=4,
        )

        assert_that(provider.model).is_equal_to("openai/gpt-4")
        assert_that(provider.timeout).is_equal_to(60.0)
        assert_that(provider.max_tokens).is_equal_to(4096)
        assert_that(provider.max_retries).is_equal_to(5)

    def test_name_property(self):
        """
        Given an initialized OpenRouterProvider
        When the name property is accessed
        Then the correct provider name is returned
        """
        from src.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert_that(provider.name).is_equal_to("llm2deck_openrouter")


class TestBasetenProvider:
    """Tests for BasetenProvider."""

    def test_init_default_parameters(self):
        """
        Given default initialization parameters
        When BasetenProvider is created
        Then all default values are set correctly
        """
        from src.providers.baseten import BasetenProvider

        provider = BasetenProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert_that(provider.model).is_equal_to("test-model")
        assert_that(provider.base_url).is_equal_to("https://inference.baseten.co/v1")
        assert_that(provider.timeout).is_equal_to(120.0)
        assert_that(provider.temperature).is_equal_to(0.4)
        assert_that(provider.strip_json_markers).is_false()

    def test_init_with_strip_json_markers(self):
        """
        Given strip_json_markers=True
        When BasetenProvider is created
        Then strip_json_markers is enabled
        """
        from src.providers.baseten import BasetenProvider

        provider = BasetenProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            strip_json_markers=True,
        )

        assert_that(provider.strip_json_markers).is_true()

    def test_name_property(self):
        """
        Given an initialized BasetenProvider
        When the name property is accessed
        Then the correct provider name is returned
        """
        from src.providers.baseten import BasetenProvider

        provider = BasetenProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert_that(provider.name).is_equal_to("llm2deck_baseten")


class TestCanopywaveProvider:
    """Tests for CanopywaveProvider."""

    def test_init_default_parameters(self):
        """
        Given default initialization parameters
        When CanopywaveProvider is created
        Then all default values are set correctly
        """
        from src.providers.canopywave import CanopywaveProvider

        provider = CanopywaveProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert_that(provider.model).is_equal_to("test-model")
        assert_that(provider.base_url).is_equal_to("https://api.xiaomimimo.com/v1")
        assert_that(provider.timeout).is_equal_to(900.0)
        assert_that(provider.temperature).is_equal_to(0.4)
        assert_that(provider.max_tokens).is_equal_to(16384)
        assert_that(provider.max_retries).is_equal_to(5)

    def test_name_property(self):
        """
        Given an initialized CanopywaveProvider
        When the name property is accessed
        Then the correct provider name is returned
        """
        from src.providers.canopywave import CanopywaveProvider

        provider = CanopywaveProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert_that(provider.name).is_equal_to("llm2deck_canopywave")


class TestGoogleAntigravityProvider:
    """Tests for GoogleAntigravityProvider."""

    def test_init_default_parameters(self):
        """
        Given default initialization parameters
        When GoogleAntigravityProvider is created
        Then all default values are set correctly (no API key needed for local)
        """
        from src.providers.google_antigravity import GoogleAntigravityProvider

        provider = GoogleAntigravityProvider(model="test-model")

        assert_that(provider.model).is_equal_to("test-model")
        assert_that(provider.base_url).is_equal_to("http://127.0.0.1:8317/v1")
        assert_that(provider.timeout).is_equal_to(900.0)
        assert_that(provider.temperature).is_equal_to(0.4)
        assert_that(provider.max_tokens).is_equal_to(16384)

    def test_init_custom_base_url(self):
        """
        Given a custom base URL
        When GoogleAntigravityProvider is created
        Then the custom URL is used
        """
        from src.providers.google_antigravity import GoogleAntigravityProvider

        provider = GoogleAntigravityProvider(
            model="test-model",
            base_url="http://192.168.1.100:8080/v1",
        )

        assert_that(provider.base_url).is_equal_to("http://192.168.1.100:8080/v1")

    def test_name_property(self):
        """
        Given an initialized GoogleAntigravityProvider
        When the name property is accessed
        Then the correct provider name is returned
        """
        from src.providers.google_antigravity import GoogleAntigravityProvider

        provider = GoogleAntigravityProvider(model="test-model")
        assert_that(provider.name).is_equal_to("llm2deck_google_antigravity")


# =============================================================================
# OpenAI-Compatible Providers - Request Flow Tests
# =============================================================================


class TestOpenAICompatibleProvidersRequestFlow:
    """Test request flow for all OpenAI-compatible providers."""

    @pytest.mark.asyncio
    async def test_nvidia_generate_initial_cards(self):
        """
        Given an initialized NvidiaProvider with mocked client
        When generate_initial_cards is called
        Then the response content is returned correctly
        """
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"cards": []}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_openrouter_generate_initial_cards(self):
        """
        Given an initialized OpenRouterProvider with mocked client
        When generate_initial_cards is called
        Then the response content is returned correctly
        """
        from src.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"cards": []}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_baseten_generate_initial_cards(self):
        """
        Given an initialized BasetenProvider with mocked client
        When generate_initial_cards is called
        Then the response content is returned correctly
        """
        from src.providers.baseten import BasetenProvider

        provider = BasetenProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"cards": []}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_canopywave_generate_initial_cards(self):
        """
        Given an initialized CanopywaveProvider with mocked client
        When generate_initial_cards is called
        Then the response content is returned correctly
        """
        from src.providers.canopywave import CanopywaveProvider

        provider = CanopywaveProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"cards": []}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_google_antigravity_generate_initial_cards(self):
        """
        Given an initialized GoogleAntigravityProvider with mocked client
        When generate_initial_cards is called
        Then the response content is returned correctly
        """
        from src.providers.google_antigravity import GoogleAntigravityProvider

        provider = GoogleAntigravityProvider(model="test-model")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"cards": []}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')


# =============================================================================
# Cerebras Provider Tests
# =============================================================================


class TestCerebrasProvider:
    """Tests for CerebrasProvider."""

    def test_init_default_parameters(self):
        """
        Given default initialization parameters
        When CerebrasProvider is created
        Then all default values are set correctly
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert_that(provider.model).is_equal_to("test-model")
        assert_that(provider.reasoning_effort).is_equal_to("high")
        assert_that(provider.max_retries).is_equal_to(5)
        assert_that(provider.json_parse_retries).is_equal_to(3)

    def test_init_custom_parameters(self):
        """
        Given custom initialization parameters
        When CerebrasProvider is created
        Then all custom values are set correctly
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="llama3.1-70b",
            reasoning_effort="low",
            max_retries=3,
            json_parse_retries=2,
        )

        assert_that(provider.model).is_equal_to("llama3.1-70b")
        assert_that(provider.reasoning_effort).is_equal_to("low")
        assert_that(provider.max_retries).is_equal_to(3)
        assert_that(provider.json_parse_retries).is_equal_to(2)

    def test_name_property(self):
        """
        Given an initialized CerebrasProvider
        When the name property is accessed
        Then the correct provider name is returned
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert_that(provider.name).is_equal_to("llm2deck_cerebras")

    def test_model_property(self):
        """
        Given an initialized CerebrasProvider
        When the model property is accessed
        Then the correct model name is returned
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="cerebras-gpt-13b",
        )
        assert_that(provider.model).is_equal_to("cerebras-gpt-13b")

    def test_get_client_rotates_keys(self):
        """
        Given a CerebrasProvider with multiple API keys
        When _get_client is called multiple times
        Then API keys are rotated in order
        """
        from src.providers.cerebras import CerebrasProvider

        keys = ["key1", "key2", "key3"]
        provider = CerebrasProvider(
            api_keys=itertools.cycle(keys),
            model="test-model",
        )

        with patch("src.providers.cerebras.Cerebras") as mock_cerebras:
            provider._get_client()
            mock_cerebras.assert_called_with(api_key="key1")

            provider._get_client()
            mock_cerebras.assert_called_with(api_key="key2")

            provider._get_client()
            mock_cerebras.assert_called_with(api_key="key3")

    @pytest.mark.asyncio
    async def test_generate_initial_cards_success(self):
        """
        Given a CerebrasProvider with mocked successful response
        When generate_initial_cards is called
        Then the response content is returned correctly
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = '{"cards": []}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_generate_initial_cards_empty_returns_empty_string(self):
        """
        Given a CerebrasProvider with None response content
        When generate_initial_cards is called
        Then an empty string is returned
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            max_retries=1,
        )

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = None

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to("")

    @pytest.mark.asyncio
    async def test_combine_cards_success(self):
        """
        Given a CerebrasProvider with mocked successful response
        When combine_cards is called
        Then the response content is returned correctly
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = '{"combined": true}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_get_client.return_value = mock_client

            result = await provider.combine_cards(
                question="Test question",
                combined_inputs="Card 1\n---\nCard 2",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"combined": true}')

    @pytest.mark.asyncio
    async def test_format_json_success(self):
        """
        Given a CerebrasProvider with mocked successful response
        When format_json is called
        Then parsed JSON is returned
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = '{"formatted": true}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_get_client.return_value = mock_client

            result = await provider.format_json(
                raw_content="Some raw content",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to({"formatted": True})

    @pytest.mark.asyncio
    async def test_format_json_invalid_json_retries(self):
        """
        Given a CerebrasProvider with initial invalid JSON response
        When format_json is called
        Then it retries and returns valid JSON on success
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            json_parse_retries=2,
        )

        responses = [
            "not valid json",
            '{"valid": true}',
        ]
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = responses[call_count]
            call_count += 1
            return mock_completion

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = side_effect
            mock_get_client.return_value = mock_client

            result = await provider.format_json(
                raw_content="content",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to({"valid": True})


# =============================================================================
# GoogleGenAI Provider Tests
# =============================================================================


class TestGoogleGenAIProvider:
    """Tests for GoogleGenAIProvider."""

    def test_init_default_parameters(self):
        """
        Given default initialization parameters
        When GoogleGenAIProvider is created
        Then all default values are set correctly
        """
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="gemini-3-pro-preview",
        )

        assert_that(provider.model).is_equal_to("gemini-3-pro-preview")
        assert_that(provider.thinking_level).is_equal_to("high")
        assert_that(provider.max_retries).is_equal_to(5)
        assert_that(provider.json_parse_retries).is_equal_to(3)

    def test_init_custom_parameters(self):
        """
        Given custom initialization parameters
        When GoogleGenAIProvider is created
        Then all custom values are set correctly
        """
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="gemini-3-flash-preview",
            thinking_level="medium",
            max_retries=3,
            json_parse_retries=2,
        )

        assert_that(provider.model).is_equal_to("gemini-3-flash-preview")
        assert_that(provider.thinking_level).is_equal_to("medium")
        assert_that(provider.max_retries).is_equal_to(3)
        assert_that(provider.json_parse_retries).is_equal_to(2)

    def test_name_property(self):
        """
        Given an initialized GoogleGenAIProvider
        When the name property is accessed
        Then the correct provider name is returned
        """
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert_that(provider.name).is_equal_to("llm2deck_google_genai")

    def test_model_property(self):
        """
        Given an initialized GoogleGenAIProvider
        When the model property is accessed
        Then the correct model name is returned
        """
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="gemini-3-pro",
        )
        assert_that(provider.model).is_equal_to("gemini-3-pro")

    def test_get_client_rotates_keys(self):
        """
        Given a GoogleGenAIProvider with multiple API keys
        When _get_client is called multiple times
        Then API keys are rotated in order
        """
        from src.providers.google_genai import GoogleGenAIProvider

        keys = ["key1", "key2"]
        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(keys),
            model="test-model",
        )

        with patch("src.providers.google_genai.genai.Client") as mock_client_class:
            provider._get_client()
            mock_client_class.assert_called_with(api_key="key1")

            provider._get_client()
            mock_client_class.assert_called_with(api_key="key2")

    @pytest.mark.asyncio
    async def test_generate_initial_cards_success(self):
        """
        Given a GoogleGenAIProvider with mocked successful response
        When generate_initial_cards is called
        Then the response text is returned correctly
        """
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_response = MagicMock()
        mock_response.text = '{"cards": []}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_generate_initial_cards_empty_returns_empty_string(self):
        """
        Given a GoogleGenAIProvider with None response text
        When generate_initial_cards is called
        Then an empty string is returned
        """
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.text = None

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to("")

    @pytest.mark.asyncio
    async def test_combine_cards_success(self):
        """
        Given a GoogleGenAIProvider with mocked successful response
        When combine_cards is called
        Then the response text is returned correctly
        """
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_response = MagicMock()
        mock_response.text = '{"combined": true}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await provider.combine_cards(
                question="Test question",
                combined_inputs="Card 1\n---\nCard 2",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"combined": true}')

    @pytest.mark.asyncio
    async def test_format_json_success(self):
        """
        Given a GoogleGenAIProvider with mocked successful response
        When format_json is called
        Then parsed JSON is returned
        """
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        mock_response = MagicMock()
        mock_response.text = '{"formatted": true}'

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await provider.format_json(
                raw_content="Some raw content",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to({"formatted": True})


# =============================================================================
# G4F Provider Tests
# =============================================================================


class TestG4FProvider:
    """Tests for G4FProvider."""

    def test_init_default_parameters(self):
        """
        Given default initialization parameters
        When G4FProvider is created
        Then all default values are set correctly
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model")

            assert_that(provider.model).is_equal_to("test-model")
            assert_that(provider.provider_name).is_equal_to("LMArena")
            assert_that(provider.max_retries).is_equal_to(3)
            assert_that(provider.json_parse_retries).is_equal_to(3)

    def test_init_custom_parameters(self):
        """
        Given custom initialization parameters
        When G4FProvider is created
        Then all custom values are set correctly
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(
                model="custom-model",
                provider_name="DDG",
                max_retries=5,
                json_parse_retries=2,
            )

            assert_that(provider.model).is_equal_to("custom-model")
            assert_that(provider.provider_name).is_equal_to("DDG")
            assert_that(provider.max_retries).is_equal_to(5)
            assert_that(provider.json_parse_retries).is_equal_to(2)

    def test_name_property(self):
        """
        Given an initialized G4FProvider
        When the name property is accessed
        Then the correct provider name is returned
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model")
            assert_that(provider.name).is_equal_to("llm2deck_g4f")

    def test_model_property(self):
        """
        Given an initialized G4FProvider
        When the model property is accessed
        Then the correct model name is returned
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="gpt-4o")
            assert_that(provider.model).is_equal_to("gpt-4o")

    @pytest.mark.asyncio
    async def test_generate_initial_cards_success(self):
        """
        Given a G4FProvider with mocked successful response
        When generate_initial_cards is called
        Then the response content is returned correctly
        """
        with patch("src.providers.g4f_provider.AsyncClient") as mock_client_class:
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model")

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"cards": []}'

            provider.async_client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_generate_initial_cards_strips_json_markers(self):
        """
        Given response with JSON code block markers
        When generate_initial_cards is called
        Then the markers are stripped and clean JSON is returned
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model")

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '```json\n{"cards": []}\n```'

            provider.async_client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_generate_initial_cards_strips_generic_code_block(self):
        """
        Given response with generic code block markers
        When generate_initial_cards is called
        Then the markers are stripped and clean JSON is returned
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model")

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '```\n{"cards": []}\n```'

            provider.async_client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            result = await provider.generate_initial_cards(
                question="Test question",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_combine_cards_success(self):
        """
        Given a G4FProvider with mocked successful response
        When combine_cards is called
        Then the response content is returned correctly
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model")

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"combined": true}'

            provider.async_client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            result = await provider.combine_cards(
                question="Test question",
                combined_inputs="Card 1\n---\nCard 2",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to('{"combined": true}')

    @pytest.mark.asyncio
    async def test_format_json_success(self):
        """
        Given a G4FProvider with mocked successful response
        When format_json is called
        Then parsed JSON is returned
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model")

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"formatted": true}'

            provider.async_client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            result = await provider.format_json(
                raw_content="Some raw content",
                json_schema={"type": "object"},
            )

            assert_that(result).is_equal_to({"formatted": True})

    @pytest.mark.asyncio
    async def test_format_json_returns_none_on_failure(self):
        """
        Given a G4FProvider with invalid JSON response after max retries
        When format_json is called
        Then None is returned
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model", json_parse_retries=1)

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "not valid json"

            provider.async_client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            result = await provider.format_json(
                raw_content="Some raw content",
                json_schema={"type": "object"},
            )

            assert_that(result).is_none()


# =============================================================================
# Gemini (Web API) Provider Tests
# =============================================================================


class TestGeminiProvider:
    """Tests for GeminiProvider (web API).

    Note: GeminiProvider is incomplete - it doesn't implement format_json,
    making it an abstract class. These tests use a mock implementation.
    """

    def test_gemini_provider_is_abstract(self):
        """
        Given the GeminiProvider class
        When attempting to instantiate directly
        Then TypeError is raised due to missing abstract method
        """
        from src.providers.gemini import GeminiProvider

        mock_client = MagicMock()
        with pytest.raises(TypeError, match="abstract"):
            GeminiProvider(gemini_client=mock_client)

    def test_gemini_module_defines_expected_attributes(self):
        """
        Given the gemini module
        When checking its attributes
        Then expected classes and attributes exist
        """
        from src.providers import gemini

        assert_that(hasattr(gemini, "GeminiProvider")).is_true()
        assert_that(hasattr(gemini, "logger")).is_true()

    def test_gemini_provider_has_expected_methods(self):
        """
        Given the GeminiProvider class
        When checking its method signatures
        Then all expected methods exist
        """
        from src.providers.gemini import GeminiProvider

        assert_that(hasattr(GeminiProvider, "generate_initial_cards")).is_true()
        assert_that(hasattr(GeminiProvider, "combine_cards")).is_true()
        assert_that(hasattr(GeminiProvider, "name")).is_true()
        assert_that(hasattr(GeminiProvider, "model")).is_true()


# =============================================================================
# Provider Inheritance Tests
# =============================================================================


class TestProviderInheritance:
    """Tests to verify all providers inherit from LLMProvider."""

    def test_openai_compatible_providers_inherit_correctly(self):
        """
        Given OpenAI-compatible provider classes
        When checking their inheritance
        Then all inherit from OpenAICompatibleProvider
        """
        from src.providers.openai_compatible import OpenAICompatibleProvider
        from src.providers.nvidia import NvidiaProvider
        from src.providers.openrouter import OpenRouterProvider
        from src.providers.baseten import BasetenProvider
        from src.providers.canopywave import CanopywaveProvider
        from src.providers.google_antigravity import GoogleAntigravityProvider

        assert_that(issubclass(NvidiaProvider, OpenAICompatibleProvider)).is_true()
        assert_that(issubclass(OpenRouterProvider, OpenAICompatibleProvider)).is_true()
        assert_that(issubclass(BasetenProvider, OpenAICompatibleProvider)).is_true()
        assert_that(issubclass(CanopywaveProvider, OpenAICompatibleProvider)).is_true()
        assert_that(issubclass(GoogleAntigravityProvider, OpenAICompatibleProvider)).is_true()

    def test_all_providers_inherit_from_llmprovider(self):
        """
        Given all provider classes
        When checking their inheritance
        Then all inherit from LLMProvider
        """
        from src.providers.base import LLMProvider
        from src.providers.cerebras import CerebrasProvider
        from src.providers.google_genai import GoogleGenAIProvider
        from src.providers.gemini import GeminiProvider

        assert_that(issubclass(CerebrasProvider, LLMProvider)).is_true()
        assert_that(issubclass(GoogleGenAIProvider, LLMProvider)).is_true()
        assert_that(issubclass(GeminiProvider, LLMProvider)).is_true()

        # G4F needs patching
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider
            assert_that(issubclass(G4FProvider, LLMProvider)).is_true()


# =============================================================================
# Parametrized Provider Tests
# =============================================================================


class TestProviderVariations:
    """Parametrized tests for provider variations."""

    @pytest.mark.parametrize("model_name", [
        "gpt-4",
        "llama3.1-70b",
        "gemini-pro",
        "claude-3-opus",
        "mistral-large",
    ])
    def test_openrouter_accepts_various_models(self, model_name):
        """
        Given various model names
        When OpenRouterProvider is created
        Then the model is accepted and stored correctly
        """
        from src.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(
            api_keys=itertools.cycle(["key1"]),
            model=model_name,
        )

        assert_that(provider.model).is_equal_to(model_name)

    @pytest.mark.parametrize("thinking_level", [
        "low",
        "medium",
        "high",
        "minimal",
    ])
    def test_google_genai_thinking_levels(self, thinking_level):
        """
        Given various thinking levels
        When GoogleGenAIProvider is created
        Then the thinking level is accepted and stored correctly
        """
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="gemini-3-flash-preview",
            thinking_level=thinking_level,
        )

        assert_that(provider.thinking_level).is_equal_to(thinking_level)

    @pytest.mark.parametrize("reasoning_effort", [
        "low",
        "medium",
        "high",
    ])
    def test_cerebras_reasoning_efforts(self, reasoning_effort):
        """
        Given various reasoning efforts
        When CerebrasProvider is created
        Then the reasoning effort is accepted and stored correctly
        """
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            reasoning_effort=reasoning_effort,
        )

        assert_that(provider.reasoning_effort).is_equal_to(reasoning_effort)

    @pytest.mark.parametrize("timeout", [30.0, 60.0, 120.0, 300.0, 600.0, 900.0])
    def test_nvidia_accepts_various_timeouts(self, timeout):
        """
        Given various timeout values
        When NvidiaProvider is created
        Then the timeout is accepted and stored correctly
        """
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            timeout=timeout,
        )

        assert_that(provider.timeout).is_equal_to(timeout)

    @pytest.mark.parametrize("max_tokens", [1024, 2048, 4096, 8192, 16384, 32768])
    def test_canopywave_accepts_various_max_tokens(self, max_tokens):
        """
        Given various max_tokens values
        When CanopywaveProvider is created
        Then the max_tokens is accepted and stored correctly
        """
        from src.providers.canopywave import CanopywaveProvider

        provider = CanopywaveProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            max_tokens=max_tokens,
        )

        assert_that(provider.max_tokens).is_equal_to(max_tokens)
