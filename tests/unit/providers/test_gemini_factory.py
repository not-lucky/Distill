"""Tests for src/providers/gemini_factory.py - Gemini provider factory."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from assertpy import assert_that

from src.providers.gemini_factory import create_gemini_providers


@pytest.fixture
def mock_provider_config():
    """Create a mock ProviderConfig."""
    config = MagicMock()
    config.enabled = True
    config.model = "gemini-pro"
    return config


@pytest.fixture
def mock_defaults_config():
    """Create a mock DefaultsConfig."""
    defaults = MagicMock()
    defaults.timeout = 60.0
    defaults.temperature = 0.5
    return defaults


@pytest.fixture
def valid_credentials():
    """Return valid Gemini credentials data."""
    return [
        {"Secure_1PSID": "session_id_1", "Secure_1PSIDTS": "timestamp_1"},
        {"Secure_1PSID": "session_id_2", "Secure_1PSIDTS": "timestamp_2"},
    ]


class TestCreateGeminiProviders:
    """Tests for create_gemini_providers function."""

    @pytest.mark.asyncio
    async def test_create_providers_success(self, tmp_path, mock_provider_config, mock_defaults_config, valid_credentials):
        """
        Given valid credentials file
        When create_gemini_providers is called
        Then it returns list of providers
        """
        creds_file = tmp_path / "gemini_keys.json"
        creds_file.write_text(json.dumps(valid_credentials))

        with patch("src.providers.gemini_factory.get_key_path", return_value=creds_file):
            with patch("gemini_webapi.GeminiClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.init = AsyncMock()
                MockClient.return_value = mock_client_instance

                with patch("src.providers.gemini.GeminiProvider") as MockProvider:
                    mock_provider = MagicMock()
                    MockProvider.return_value = mock_provider

                    result = await create_gemini_providers(mock_provider_config, mock_defaults_config)

                    assert_that(result).is_length(2)
                    assert_that(MockClient.call_count).is_equal_to(2)
                    assert_that(mock_client_instance.init.call_count).is_equal_to(2)

    @pytest.mark.asyncio
    async def test_create_providers_file_not_found(self, tmp_path, mock_provider_config, mock_defaults_config):
        """
        Given missing credentials file
        When create_gemini_providers is called
        Then it returns empty list and logs warning
        """
        nonexistent = tmp_path / "nonexistent.json"

        with patch("src.providers.gemini_factory.get_key_path", return_value=nonexistent):
            with patch("src.providers.gemini_factory.logger") as mock_logger:
                result = await create_gemini_providers(mock_provider_config, mock_defaults_config)

                assert_that(result).is_empty()
                mock_logger.warning.assert_called()
                warning_message = mock_logger.warning.call_args[0][0]
                assert_that(warning_message).contains("not found")

    @pytest.mark.asyncio
    async def test_create_providers_malformed_json(self, tmp_path, mock_provider_config, mock_defaults_config):
        """
        Given credentials file with invalid JSON
        When create_gemini_providers is called
        Then it returns empty list and logs error
        """
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ invalid json }")

        with patch("src.providers.gemini_factory.get_key_path", return_value=bad_file):
            with patch("src.providers.gemini_factory.logger") as mock_logger:
                result = await create_gemini_providers(mock_provider_config, mock_defaults_config)

                assert_that(result).is_empty()
                mock_logger.error.assert_called()
                error_message = mock_logger.error.call_args[0][0]
                assert_that(error_message).contains("Failed to load")

    @pytest.mark.asyncio
    async def test_create_providers_client_init_failure(self, tmp_path, mock_provider_config, mock_defaults_config, valid_credentials):
        """
        Given valid credentials but client init fails
        When create_gemini_providers is called
        Then it logs error and returns empty list
        """
        creds_file = tmp_path / "gemini_keys.json"
        creds_file.write_text(json.dumps(valid_credentials))

        with patch("src.providers.gemini_factory.get_key_path", return_value=creds_file):
            with patch("gemini_webapi.GeminiClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.init = AsyncMock(side_effect=Exception("Auth failed"))
                MockClient.return_value = mock_client_instance

                with patch("src.providers.gemini_factory.logger") as mock_logger:
                    result = await create_gemini_providers(mock_provider_config, mock_defaults_config)

                    assert_that(result).is_empty()
                    # Should log error for each failed init
                    assert_that(mock_logger.error.call_count).is_greater_than_or_equal_to(1)
                    # Should log warning about no clients initialized
                    mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_create_providers_partial_success(self, tmp_path, mock_provider_config, mock_defaults_config, valid_credentials):
        """
        Given multiple credentials where one fails
        When create_gemini_providers is called
        Then it returns providers for successful ones
        """
        creds_file = tmp_path / "gemini_keys.json"
        creds_file.write_text(json.dumps(valid_credentials))

        with patch("src.providers.gemini_factory.get_key_path", return_value=creds_file):
            with patch("gemini_webapi.GeminiClient") as MockClient:
                # First call succeeds, second fails
                mock_success_client = AsyncMock()
                mock_success_client.init = AsyncMock()

                mock_fail_client = AsyncMock()
                mock_fail_client.init = AsyncMock(side_effect=Exception("Auth failed"))

                MockClient.side_effect = [mock_success_client, mock_fail_client]

                with patch("src.providers.gemini.GeminiProvider") as MockProvider:
                    mock_provider = MagicMock()
                    MockProvider.return_value = mock_provider

                    with patch("src.providers.gemini_factory.logger") as mock_logger:
                        result = await create_gemini_providers(mock_provider_config, mock_defaults_config)

                        # One provider should succeed
                        assert_that(result).is_length(1)
                        # Error logged for the failed one
                        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_create_providers_empty_credentials(self, tmp_path, mock_provider_config, mock_defaults_config):
        """
        Given credentials file with empty list
        When create_gemini_providers is called
        Then it returns empty list
        """
        creds_file = tmp_path / "gemini_keys.json"
        creds_file.write_text(json.dumps([]))

        with patch("src.providers.gemini_factory.get_key_path", return_value=creds_file):
            with patch("src.providers.gemini_factory.logger") as mock_logger:
                result = await create_gemini_providers(mock_provider_config, mock_defaults_config)

                assert_that(result).is_empty()
                mock_logger.warning.assert_called()
