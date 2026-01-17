"""Unit tests for CerebrasProvider."""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
import itertools


class TestCerebrasProviderProperties:
    """Test CerebrasProvider properties."""

    def test_cerebras_provider_name(self, cerebras_provider):
        """Test that provider name is correct."""
        assert cerebras_provider.name == "llm2deck_cerebras"

    def test_cerebras_provider_model(self, cerebras_provider):
        """Test that model name is set correctly."""
        assert cerebras_provider.model == "gpt-oss-120b"

    def test_cerebras_provider_reasoning_effort_default(self, mock_cerebras_keys):
        """Test default reasoning effort is 'high'."""
        from src.providers.cerebras import CerebrasProvider
        provider = CerebrasProvider(api_keys=mock_cerebras_keys, model="gpt-oss-120b")
        assert provider.reasoning_effort == "high"

    def test_cerebras_provider_custom_reasoning_effort(self, mock_cerebras_keys):
        """Test custom reasoning effort."""
        from src.providers.cerebras import CerebrasProvider
        provider = CerebrasProvider(
            api_keys=mock_cerebras_keys,
            model="gpt-oss-120b",
            reasoning_effort="low"
        )
        assert provider.reasoning_effort == "low"


class TestCerebrasProviderGeneration:
    """Test CerebrasProvider generation methods."""

    @pytest.fixture
    def mock_cerebras_sdk(self):
        """Mock the Cerebras SDK."""
        with patch("src.providers.cerebras.Cerebras") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_generate_initial_cards_success(
        self, cerebras_provider, mock_cerebras_sdk, sample_card_json
    ):
        """Test successful initial card generation."""
        # Setup mock response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = sample_card_json

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_cerebras_sdk.return_value = mock_client

        # Call the method
        result = await cerebras_provider.generate_initial_cards(
            question="Min Stack",
            json_schema={"type": "object"},
            prompt_template=None
        )

        # Verify
        assert result == sample_card_json
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_initial_cards_returns_empty_on_failure(
        self, cerebras_provider, mock_cerebras_sdk
    ):
        """Test that generation returns empty string after max retries."""
        # Setup mock to always fail
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_cerebras_sdk.return_value = mock_client

        # Reduce retries for faster test
        cerebras_provider.max_retries = 2

        # Call with short sleep patch
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await cerebras_provider.generate_initial_cards(
                question="Test",
                json_schema={"type": "object"}
            )

        assert result == ""

    @pytest.mark.asyncio
    async def test_combine_cards_success(
        self, cerebras_provider, mock_cerebras_sdk, sample_card_json, sample_card_dict
    ):
        """Test successful card combination."""
        # Setup mock response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = sample_card_json

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_cerebras_sdk.return_value = mock_client

        # Call the method
        result = await cerebras_provider.combine_cards(
            question="Min Stack",
            combined_inputs="Set 1: {...}",
            json_schema={"type": "object"}
        )

        # Verify - should return parsed dict
        assert result is not None
        assert "cards" in result

    @pytest.mark.asyncio
    async def test_combine_cards_json_decode_error_retry(
        self, cerebras_provider, mock_cerebras_sdk
    ):
        """Test that JSON decode errors trigger retry."""
        # Setup mock with invalid JSON first, then valid
        mock_completion_invalid = MagicMock()
        mock_completion_invalid.choices = [MagicMock()]
        mock_completion_invalid.choices[0].message.content = "not valid json"

        mock_completion_valid = MagicMock()
        mock_completion_valid.choices = [MagicMock()]
        mock_completion_valid.choices[0].message.content = '{"cards": []}'

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            mock_completion_invalid,
            mock_completion_valid
        ]
        mock_cerebras_sdk.return_value = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await cerebras_provider.combine_cards(
                question="Test",
                combined_inputs="...",
                json_schema={"type": "object"}
            )

        assert result == {"cards": []}

    @pytest.mark.asyncio
    async def test_combine_cards_returns_none_on_all_failures(
        self, cerebras_provider, mock_cerebras_sdk
    ):
        """Test combine_cards returns None after all retries fail."""
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "invalid json forever"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_cerebras_sdk.return_value = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await cerebras_provider.combine_cards(
                question="Test",
                combined_inputs="...",
                json_schema={"type": "object"}
            )

        assert result is None
