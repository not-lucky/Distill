"""Tests for src/config/keys.py - API key loading functions."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from assertpy import assert_that

from src.config.keys import (
    load_keys,
    get_key_path,
    _extract_api_key,
    _extract_openrouter_key,
    _extract_flexible,
    _get_key_paths_from_config,
    KEY_CONFIGS,
)


class TestExtractorFunctions:
    """Tests for key extractor helper functions."""

    def test_extract_api_key_valid_data(self):
        """
        Given a list of dicts with api_key field
        When _extract_api_key is called
        Then it returns a list of keys
        """
        data = [
            {"api_key": "key1", "other": "data"},
            {"api_key": "key2"},
            {"no_key": "value"},  # Should be skipped
        ]
        result = _extract_api_key(data)
        assert_that(result).is_equal_to(["key1", "key2"])

    def test_extract_api_key_empty_list(self):
        """
        Given an empty list
        When _extract_api_key is called
        Then it returns an empty list
        """
        result = _extract_api_key([])
        assert_that(result).is_empty()

    def test_extract_openrouter_key_valid_data(self):
        """
        Given a list with OpenRouter's nested format
        When _extract_openrouter_key is called
        Then it extracts keys from data.key path
        """
        data = [
            {"data": {"key": "or_key1"}},
            {"data": {"key": "or_key2"}},
            {"data": {}},  # Missing key, should be skipped
            {"other": "data"},  # Missing data, should be skipped
        ]
        result = _extract_openrouter_key(data)
        assert_that(result).is_equal_to(["or_key1", "or_key2"])

    def test_extract_flexible_with_strings(self):
        """
        Given a list of strings
        When _extract_flexible is called
        Then it returns the strings as-is
        """
        data = ["key1", "key2", "key3"]
        result = _extract_flexible(data)
        assert_that(result).is_equal_to(["key1", "key2", "key3"])

    def test_extract_flexible_with_dicts(self):
        """
        Given a list of dicts with api_key
        When _extract_flexible is called
        Then it delegates to _extract_api_key
        """
        data = [{"api_key": "key1"}, {"api_key": "key2"}]
        result = _extract_flexible(data)
        assert_that(result).is_equal_to(["key1", "key2"])

    def test_extract_flexible_empty_list(self):
        """
        Given an empty list
        When _extract_flexible is called
        Then it returns an empty list
        """
        result = _extract_flexible([])
        assert_that(result).is_empty()


class TestGetKeyPath:
    """Tests for get_key_path function."""

    def test_get_key_path_returns_default(self):
        """
        Given a known provider and no env/config override
        When get_key_path is called
        Then it returns the default path
        """
        # Clear cache to ensure fresh lookup
        _get_key_paths_from_config.cache_clear()

        with patch.dict("os.environ", {}, clear=True), \
             patch("src.config.keys._get_key_paths_from_config", return_value=None):
            result = get_key_path("cerebras")
            assert_that(str(result)).is_equal_to("api_keys.json")

    def test_get_key_path_env_var_priority(self):
        """
        Given an environment variable is set
        When get_key_path is called
        Then it returns the env var value (highest priority)
        """
        _get_key_paths_from_config.cache_clear()

        with patch.dict("os.environ", {"CEREBRAS_KEYS_FILE_PATH": "/custom/path.json"}):
            result = get_key_path("cerebras")
            assert_that(str(result)).is_equal_to("/custom/path.json")

    def test_get_key_path_unknown_provider(self):
        """
        Given an unknown provider name
        When get_key_path is called
        Then it returns a generated default path
        """
        _get_key_paths_from_config.cache_clear()

        with patch.dict("os.environ", {}, clear=True), \
             patch("src.config.keys._get_key_paths_from_config", return_value=None):
            result = get_key_path("unknown_provider")
            assert_that(str(result)).is_equal_to("unknown_provider_keys.json")


class TestLoadKeys:
    """Tests for load_keys async function."""

    async def test_load_keys_valid_file(self, tmp_path):
        """
        Given a valid JSON file with keys
        When load_keys is called
        Then it returns a list of keys
        """
        keys_file = tmp_path / "api_keys.json"
        keys_file.write_text(json.dumps([
            {"api_key": "key1"},
            {"api_key": "key2"},
            {"api_key": "key3"},
        ]))

        mock_config = MagicMock()
        mock_config.path = keys_file
        mock_config.extractor = _extract_api_key

        with patch.dict("src.config.keys.KEY_CONFIGS", {"test_provider": mock_config}):
            result = await load_keys("test_provider")

            assert_that(result).is_length(3)
            assert_that(set(result)).is_equal_to({"key1", "key2", "key3"})

    async def test_load_keys_file_not_found(self, tmp_path):
        """
        Given a non-existent file path
        When load_keys is called
        Then it returns empty list and logs warning
        """
        nonexistent = tmp_path / "nonexistent.json"

        mock_config = MagicMock()
        mock_config.path = nonexistent
        mock_config.extractor = _extract_api_key

        with patch.dict("src.config.keys.KEY_CONFIGS", {"test_provider": mock_config}), \
             patch("src.config.keys.logger") as mock_logger:
            result = await load_keys("test_provider")

            assert_that(result).is_empty()
            mock_logger.warning.assert_called()

    async def test_load_keys_malformed_json(self, tmp_path):
        """
        Given a file with invalid JSON
        When load_keys is called
        Then it returns empty list and logs error
        """
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{ invalid json }")

        mock_config = MagicMock()
        mock_config.path = bad_json
        mock_config.extractor = _extract_api_key

        with patch.dict("src.config.keys.KEY_CONFIGS", {"test_provider": mock_config}), \
             patch("src.config.keys.logger") as mock_logger:
            result = await load_keys("test_provider")

            assert_that(result).is_empty()
            mock_logger.error.assert_called()

    async def test_load_keys_unknown_provider(self):
        """
        Given an unknown provider name
        When load_keys is called
        Then it returns empty list and logs warning
        """
        with patch("src.config.keys.logger") as mock_logger:
            result = await load_keys("completely_unknown_provider")

            assert_that(result).is_empty()
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert_that(warning_call).contains("Unknown provider")

    async def test_load_keys_empty_keys(self, tmp_path):
        """
        Given a file that exists but yields no keys
        When load_keys is called
        Then it returns empty list and logs warning
        """
        empty_keys = tmp_path / "empty.json"
        empty_keys.write_text(json.dumps([]))

        mock_config = MagicMock()
        mock_config.path = empty_keys
        mock_config.extractor = _extract_api_key

        with patch.dict("src.config.keys.KEY_CONFIGS", {"test_provider": mock_config}), \
             patch("src.config.keys.logger") as mock_logger:
            result = await load_keys("test_provider")

            assert_that(result).is_empty()
            mock_logger.warning.assert_called()

    async def test_load_keys_shuffles_keys(self, tmp_path):
        """
        Given a file with multiple keys
        When load_keys is called multiple times
        Then the order should vary (keys are shuffled)
        """
        keys_file = tmp_path / "api_keys.json"
        # Create enough keys to make shuffling observable
        many_keys = [{"api_key": f"key_{i}"} for i in range(20)]
        keys_file.write_text(json.dumps(many_keys))

        mock_config = MagicMock()
        mock_config.path = keys_file
        mock_config.extractor = _extract_api_key

        with patch.dict("src.config.keys.KEY_CONFIGS", {"test_provider": mock_config}):
            results = []
            for _ in range(5):
                result = await load_keys("test_provider")
                results.append(tuple(result))

            # With 20 keys and 5 iterations, we expect at least some different orderings
            unique_orderings = set(results)
            assert_that(len(unique_orderings)).is_greater_than(1)


class TestKeyConfigs:
    """Tests for KEY_CONFIGS registry."""

    def test_key_configs_has_expected_providers(self):
        """
        Given the KEY_CONFIGS registry
        Then it should contain entries for all major providers
        """
        expected_providers = ["cerebras", "openrouter", "nvidia", "canopywave", "baseten", "google_genai"]
        for provider in expected_providers:
            assert_that(KEY_CONFIGS).contains_key(provider)

    def test_key_configs_entries_have_path_and_extractor(self):
        """
        Given any entry in KEY_CONFIGS
        Then it should have path and extractor attributes
        """
        for name, config in KEY_CONFIGS.items():
            assert_that(config.path).is_not_none()
            assert_that(config.extractor).is_not_none()
            assert_that(callable(config.extractor)).is_true()
