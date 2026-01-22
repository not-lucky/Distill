"""Tests for all concrete LLM providers.

This module tests all concrete provider implementations including:
- OpenAI-compatible providers: NVIDIA, OpenRouter, Baseten, Canopywave, GoogleAntigravity
- Native SDK providers: Cerebras, GoogleGenAI, G4F, Gemini
"""

import itertools
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# OpenAI-Compatible Provider Tests (thin wrappers)
# =============================================================================


class TestNvidiaProvider:
    """Tests for NvidiaProvider."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert provider.model == "test-model"
        assert provider.base_url == "https://integrate.api.nvidia.com/v1"
        assert provider.timeout == 900.0
        assert provider.temperature == 0.4
        assert provider.max_tokens == 16384
        assert provider.top_p == 0.95

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
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

        assert provider.model == "custom-model"
        assert provider.base_url == "https://custom.nvidia.com/v1"
        assert provider.timeout == 120.0
        assert provider.temperature == 0.7
        assert provider.max_tokens == 8192
        assert provider.top_p == 0.8
        assert provider.max_retries == 3
        assert provider.json_parse_retries == 2

    def test_name_property(self):
        """Test name property returns correct value."""
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert provider.name == "llm2deck_nvidia"

    def test_extra_body_chat_template_kwargs(self):
        """Test that extra_body with thinking is set by default."""
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        extra_params = provider._get_extra_request_params()
        assert "extra_body" in extra_params
        assert extra_params["extra_body"]["chat_template_kwargs"]["thinking"] is True

    def test_extra_params_merged(self):
        """Test that extra_params are merged with defaults."""
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            extra_params={"custom_param": "value"},
        )

        extra_params = provider._get_extra_request_params()
        assert "extra_body" in extra_params
        assert "custom_param" in extra_params


class TestOpenRouterProvider:
    """Tests for OpenRouterProvider."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        from src.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert provider.model == "test-model"
        assert provider.base_url == "https://openrouter.ai/api/v1"
        assert provider.timeout == 120.0
        assert provider.temperature == 0.4
        assert provider.max_tokens is None
        assert provider.max_retries == 3

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
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

        assert provider.model == "openai/gpt-4"
        assert provider.timeout == 60.0
        assert provider.max_tokens == 4096
        assert provider.max_retries == 5

    def test_name_property(self):
        """Test name property returns correct value."""
        from src.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert provider.name == "llm2deck_openrouter"


class TestBasetenProvider:
    """Tests for BasetenProvider."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        from src.providers.baseten import BasetenProvider

        provider = BasetenProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert provider.model == "test-model"
        assert provider.base_url == "https://inference.baseten.co/v1"
        assert provider.timeout == 120.0
        assert provider.temperature == 0.4
        assert provider.strip_json_markers is False

    def test_init_with_strip_json_markers(self):
        """Test initialization with strip_json_markers enabled."""
        from src.providers.baseten import BasetenProvider

        provider = BasetenProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            strip_json_markers=True,
        )

        assert provider.strip_json_markers is True

    def test_name_property(self):
        """Test name property returns correct value."""
        from src.providers.baseten import BasetenProvider

        provider = BasetenProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert provider.name == "llm2deck_baseten"


class TestCanopywaveProvider:
    """Tests for CanopywaveProvider."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        from src.providers.canopywave import CanopywaveProvider

        provider = CanopywaveProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert provider.model == "test-model"
        assert provider.base_url == "https://api.xiaomimimo.com/v1"
        assert provider.timeout == 900.0
        assert provider.temperature == 0.4
        assert provider.max_tokens == 16384
        assert provider.max_retries == 5

    def test_name_property(self):
        """Test name property returns correct value."""
        from src.providers.canopywave import CanopywaveProvider

        provider = CanopywaveProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert provider.name == "llm2deck_canopywave"


class TestGoogleAntigravityProvider:
    """Tests for GoogleAntigravityProvider."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        from src.providers.google_antigravity import GoogleAntigravityProvider

        provider = GoogleAntigravityProvider(model="test-model")

        assert provider.model == "test-model"
        assert provider.base_url == "http://127.0.0.1:8317/v1"
        assert provider.timeout == 900.0
        assert provider.temperature == 0.4
        assert provider.max_tokens == 16384
        # No API key needed for local

    def test_init_custom_base_url(self):
        """Test initialization with custom local URL."""
        from src.providers.google_antigravity import GoogleAntigravityProvider

        provider = GoogleAntigravityProvider(
            model="test-model",
            base_url="http://192.168.1.100:8080/v1",
        )

        assert provider.base_url == "http://192.168.1.100:8080/v1"

    def test_name_property(self):
        """Test name property returns correct value."""
        from src.providers.google_antigravity import GoogleAntigravityProvider

        provider = GoogleAntigravityProvider(model="test-model")
        assert provider.name == "llm2deck_google_antigravity"


# =============================================================================
# OpenAI-Compatible Providers - Request Flow Tests
# =============================================================================


class TestOpenAICompatibleProvidersRequestFlow:
    """Test request flow for all OpenAI-compatible providers."""

    @pytest.mark.asyncio
    async def test_nvidia_generate_initial_cards(self):
        """Test NvidiaProvider generate_initial_cards."""
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

            assert result == '{"cards": []}'
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_openrouter_generate_initial_cards(self):
        """Test OpenRouterProvider generate_initial_cards."""
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

            assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_baseten_generate_initial_cards(self):
        """Test BasetenProvider generate_initial_cards."""
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

            assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_canopywave_generate_initial_cards(self):
        """Test CanopywaveProvider generate_initial_cards."""
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

            assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_google_antigravity_generate_initial_cards(self):
        """Test GoogleAntigravityProvider generate_initial_cards."""
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

            assert result == '{"cards": []}'


# =============================================================================
# Cerebras Provider Tests
# =============================================================================


class TestCerebrasProvider:
    """Tests for CerebrasProvider."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )

        assert provider.model == "test-model"
        assert provider.reasoning_effort == "high"
        assert provider.max_retries == 5
        assert provider.json_parse_retries == 3

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="llama3.1-70b",
            reasoning_effort="low",
            max_retries=3,
            json_parse_retries=2,
        )

        assert provider.model == "llama3.1-70b"
        assert provider.reasoning_effort == "low"
        assert provider.max_retries == 3
        assert provider.json_parse_retries == 2

    def test_name_property(self):
        """Test name property returns correct value."""
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert provider.name == "llm2deck_cerebras"

    def test_model_property(self):
        """Test model property returns correct value."""
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="cerebras-gpt-13b",
        )
        assert provider.model == "cerebras-gpt-13b"

    def test_get_client_rotates_keys(self):
        """Test that _get_client rotates API keys."""
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
        """Test generate_initial_cards with successful response."""
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

            assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_generate_initial_cards_empty_returns_empty_string(self):
        """Test generate_initial_cards returns empty string on failure."""
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

            assert result == ""

    @pytest.mark.asyncio
    async def test_combine_cards_success(self):
        """Test combine_cards with successful response."""
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

            assert result == '{"combined": true}'

    @pytest.mark.asyncio
    async def test_format_json_success(self):
        """Test format_json with successful response."""
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

            assert result == {"formatted": True}

    @pytest.mark.asyncio
    async def test_format_json_invalid_json_retries(self):
        """Test format_json retries on invalid JSON."""
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

            assert result == {"valid": True}


# =============================================================================
# GoogleGenAI Provider Tests
# =============================================================================


class TestGoogleGenAIProvider:
    """Tests for GoogleGenAIProvider."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="gemini-3-pro-preview",
        )

        assert provider.model == "gemini-3-pro-preview"
        assert provider.thinking_level == "high"
        assert provider.max_retries == 5
        assert provider.json_parse_retries == 3

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="gemini-3-flash-preview",
            thinking_level="medium",
            max_retries=3,
            json_parse_retries=2,
        )

        assert provider.model == "gemini-3-flash-preview"
        assert provider.thinking_level == "medium"
        assert provider.max_retries == 3
        assert provider.json_parse_retries == 2

    def test_name_property(self):
        """Test name property returns correct value."""
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
        )
        assert provider.name == "llm2deck_google_genai"

    def test_model_property(self):
        """Test model property returns correct value."""
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="gemini-3-pro",
        )
        assert provider.model == "gemini-3-pro"

    def test_get_client_rotates_keys(self):
        """Test that _get_client rotates API keys."""
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
        """Test generate_initial_cards with successful response."""
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

            assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_generate_initial_cards_empty_returns_empty_string(self):
        """Test generate_initial_cards returns empty string on failure."""
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

            assert result == ""

    @pytest.mark.asyncio
    async def test_combine_cards_success(self):
        """Test combine_cards with successful response."""
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

            assert result == '{"combined": true}'

    @pytest.mark.asyncio
    async def test_format_json_success(self):
        """Test format_json with successful response."""
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

            assert result == {"formatted": True}


# =============================================================================
# G4F Provider Tests
# =============================================================================


class TestG4FProvider:
    """Tests for G4FProvider."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model")

            assert provider.model == "test-model"
            assert provider.provider_name == "LMArena"
            assert provider.max_retries == 3
            assert provider.json_parse_retries == 3

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(
                model="custom-model",
                provider_name="DDG",
                max_retries=5,
                json_parse_retries=2,
            )

            assert provider.model == "custom-model"
            assert provider.provider_name == "DDG"
            assert provider.max_retries == 5
            assert provider.json_parse_retries == 2

    def test_name_property(self):
        """Test name property returns correct value."""
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="test-model")
            assert provider.name == "llm2deck_g4f"

    def test_model_property(self):
        """Test model property returns correct value."""
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider

            provider = G4FProvider(model="gpt-4o")
            assert provider.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_generate_initial_cards_success(self):
        """Test generate_initial_cards with successful response."""
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

            assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_generate_initial_cards_strips_json_markers(self):
        """Test generate_initial_cards strips JSON code block markers."""
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

            assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_generate_initial_cards_strips_generic_code_block(self):
        """Test generate_initial_cards strips generic code block markers."""
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

            assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_combine_cards_success(self):
        """Test combine_cards with successful response."""
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

            assert result == '{"combined": true}'

    @pytest.mark.asyncio
    async def test_format_json_success(self):
        """Test format_json with successful response."""
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

            assert result == {"formatted": True}

    @pytest.mark.asyncio
    async def test_format_json_returns_none_on_failure(self):
        """Test format_json returns None after max retries."""
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

            assert result is None


# =============================================================================
# Gemini (Web API) Provider Tests
# =============================================================================


class TestGeminiProvider:
    """Tests for GeminiProvider (web API).

    Note: GeminiProvider is incomplete - it doesn't implement format_json,
    making it an abstract class. These tests use a mock implementation.
    """

    def test_gemini_provider_is_abstract(self):
        """Test that GeminiProvider cannot be instantiated directly.

        GeminiProvider is missing the format_json implementation,
        making it abstract.
        """
        from src.providers.gemini import GeminiProvider

        mock_client = MagicMock()
        with pytest.raises(TypeError, match="abstract"):
            GeminiProvider(gemini_client=mock_client)

    def test_gemini_module_defines_expected_attributes(self):
        """Test that the gemini module has expected structure."""
        from src.providers import gemini

        assert hasattr(gemini, "GeminiProvider")
        assert hasattr(gemini, "logger")

    def test_gemini_provider_has_expected_methods(self):
        """Test that GeminiProvider defines expected method signatures."""
        from src.providers.gemini import GeminiProvider

        # Check class-level attributes and methods exist
        assert hasattr(GeminiProvider, "generate_initial_cards")
        assert hasattr(GeminiProvider, "combine_cards")
        assert hasattr(GeminiProvider, "name")
        assert hasattr(GeminiProvider, "model")


# =============================================================================
# Provider Inheritance Tests
# =============================================================================


class TestProviderInheritance:
    """Tests to verify all providers inherit from LLMProvider."""

    def test_openai_compatible_providers_inherit_correctly(self):
        """Test that OpenAI-compatible providers inherit from OpenAICompatibleProvider."""
        from src.providers.openai_compatible import OpenAICompatibleProvider
        from src.providers.nvidia import NvidiaProvider
        from src.providers.openrouter import OpenRouterProvider
        from src.providers.baseten import BasetenProvider
        from src.providers.canopywave import CanopywaveProvider
        from src.providers.google_antigravity import GoogleAntigravityProvider

        assert issubclass(NvidiaProvider, OpenAICompatibleProvider)
        assert issubclass(OpenRouterProvider, OpenAICompatibleProvider)
        assert issubclass(BasetenProvider, OpenAICompatibleProvider)
        assert issubclass(CanopywaveProvider, OpenAICompatibleProvider)
        assert issubclass(GoogleAntigravityProvider, OpenAICompatibleProvider)

    def test_all_providers_inherit_from_llmprovider(self):
        """Test that all providers inherit from LLMProvider."""
        from src.providers.base import LLMProvider
        from src.providers.cerebras import CerebrasProvider
        from src.providers.google_genai import GoogleGenAIProvider
        from src.providers.gemini import GeminiProvider

        assert issubclass(CerebrasProvider, LLMProvider)
        assert issubclass(GoogleGenAIProvider, LLMProvider)
        assert issubclass(GeminiProvider, LLMProvider)

        # G4F needs patching
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider
            assert issubclass(G4FProvider, LLMProvider)


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
        """Test OpenRouterProvider accepts various model names."""
        from src.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(
            api_keys=itertools.cycle(["key1"]),
            model=model_name,
        )

        assert provider.model == model_name

    @pytest.mark.parametrize("thinking_level", [
        "low",
        "medium",
        "high",
        "minimal",
    ])
    def test_google_genai_thinking_levels(self, thinking_level):
        """Test GoogleGenAIProvider accepts various thinking levels."""
        from src.providers.google_genai import GoogleGenAIProvider

        provider = GoogleGenAIProvider(
            api_keys=itertools.cycle(["key1"]),
            model="gemini-3-flash-preview",
            thinking_level=thinking_level,
        )

        assert provider.thinking_level == thinking_level

    @pytest.mark.parametrize("reasoning_effort", [
        "low",
        "medium",
        "high",
    ])
    def test_cerebras_reasoning_efforts(self, reasoning_effort):
        """Test CerebrasProvider accepts various reasoning efforts."""
        from src.providers.cerebras import CerebrasProvider

        provider = CerebrasProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            reasoning_effort=reasoning_effort,
        )

        assert provider.reasoning_effort == reasoning_effort

    @pytest.mark.parametrize("timeout", [30.0, 60.0, 120.0, 300.0, 600.0, 900.0])
    def test_nvidia_accepts_various_timeouts(self, timeout):
        """Test NvidiaProvider accepts various timeout values."""
        from src.providers.nvidia import NvidiaProvider

        provider = NvidiaProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            timeout=timeout,
        )

        assert provider.timeout == timeout

    @pytest.mark.parametrize("max_tokens", [1024, 2048, 4096, 8192, 16384, 32768])
    def test_canopywave_accepts_various_max_tokens(self, max_tokens):
        """Test CanopywaveProvider accepts various max_tokens values."""
        from src.providers.canopywave import CanopywaveProvider

        provider = CanopywaveProvider(
            api_keys=itertools.cycle(["key1"]),
            model="test-model",
            max_tokens=max_tokens,
        )

        assert provider.max_tokens == max_tokens
