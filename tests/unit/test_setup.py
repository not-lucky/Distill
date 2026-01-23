"""Tests for src/setup.py - initialize_providers function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from assertpy import assert_that

from src.config.loader import (
    AppConfig,
    DefaultsConfig,
    GenerationConfig,
    ProviderConfig,
    CombinerConfig,
    FormatterConfig,
    PathsConfig,
)
from src.providers.base import LLMProvider


class MockProvider(LLMProvider):
    """Simple mock provider for testing."""

    def __init__(self, name: str = "mock", model: str = "mock-model"):
        self._name = name
        self._model = model

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    async def generate_initial_cards(self, question, json_schema, prompt_template=None):
        return "{}"

    async def combine_cards(self, question, combined_inputs, json_schema, combine_prompt_template=None):
        return "{}"

    async def format_json(self, raw_content, json_schema):
        return {}


class TestInitializeProviders:
    """Tests for initialize_providers function."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock AppConfig with minimal settings."""
        return AppConfig(
            defaults=DefaultsConfig(),
            providers={
                "cerebras": ProviderConfig(enabled=True, model="llama-70b"),
                "openrouter": ProviderConfig(enabled=False),
            },
            generation=GenerationConfig(),
            paths=PathsConfig(),
        )

    @pytest.fixture
    def mock_config_with_combiner(self):
        """Config with explicit combiner set."""
        return AppConfig(
            defaults=DefaultsConfig(),
            providers={
                "cerebras": ProviderConfig(enabled=True, model="llama-70b"),
                "google_antigravity": ProviderConfig(enabled=True, model="gemini-pro"),
            },
            generation=GenerationConfig(
                combiner=CombinerConfig(
                    provider="google_antigravity",
                    model="gemini-pro",
                    also_generate=False,
                )
            ),
            paths=PathsConfig(),
        )

    @pytest.fixture
    def mock_config_empty(self):
        """Config with no providers enabled."""
        return AppConfig(
            defaults=DefaultsConfig(),
            providers={
                "cerebras": ProviderConfig(enabled=False),
                "openrouter": ProviderConfig(enabled=False),
            },
            generation=GenerationConfig(),
            paths=PathsConfig(),
        )

    async def test_initialize_providers_normal_flow(self, mock_config):
        """
        Given a config with enabled providers
        When initialize_providers is called
        Then it returns a tuple with active providers, combiner, and formatter
        """
        from src.setup import initialize_providers

        mock_provider = MockProvider(name="cerebras", model="llama-70b")

        with patch("src.setup.load_config", return_value=mock_config), \
             patch("src.setup.get_combiner_config", return_value=None), \
             patch("src.setup.get_formatter_config", return_value=None), \
             patch("src.setup.create_provider_instances", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = [mock_provider]

            generators, combiner, formatter = await initialize_providers()

            assert_that(generators).is_length(1)
            assert_that(generators[0].name).is_equal_to("cerebras")
            assert_that(combiner).is_none()
            assert_that(formatter).is_none()

    async def test_initialize_providers_no_providers_enabled(self, mock_config_empty):
        """
        Given a config with no providers enabled
        When initialize_providers is called
        Then it returns empty generators list and logs error
        """
        from src.setup import initialize_providers

        with patch("src.setup.load_config", return_value=mock_config_empty), \
             patch("src.setup.get_combiner_config", return_value=None), \
             patch("src.setup.get_formatter_config", return_value=None), \
             patch("src.setup.logger") as mock_logger:

            generators, combiner, formatter = await initialize_providers()

            assert_that(generators).is_empty()
            assert_that(combiner).is_none()
            assert_that(formatter).is_none()
            mock_logger.error.assert_called_once()

    async def test_initialize_providers_combiner_only_mode(self, mock_config_with_combiner):
        """
        Given a config where combiner has also_generate=false
        When initialize_providers is called
        Then combiner is not included in generators list
        """
        from src.setup import initialize_providers

        cerebras_provider = MockProvider(name="cerebras", model="llama-70b")
        combiner_provider = MockProvider(name="google_antigravity", model="gemini-pro")

        combiner_cfg = CombinerConfig(
            provider="google_antigravity",
            model="gemini-pro",
            also_generate=False,
        )

        async def mock_create(name, spec, cfg, defaults):
            if name == "cerebras":
                return [cerebras_provider]
            elif name == "google_antigravity":
                return [combiner_provider]
            return []

        with patch("src.setup.load_config", return_value=mock_config_with_combiner), \
             patch("src.setup.get_combiner_config", return_value=combiner_cfg), \
             patch("src.setup.get_formatter_config", return_value=None), \
             patch("src.setup.create_provider_instances", side_effect=mock_create):

            generators, combiner, formatter = await initialize_providers()

            # Combiner should be set but NOT in generators
            assert_that(combiner).is_not_none()
            assert_that(combiner.name).is_equal_to("google_antigravity")
            # Only cerebras should be in generators, not the combiner
            assert_that(generators).is_length(1)
            assert_that(generators[0].name).is_equal_to("cerebras")

    async def test_initialize_providers_handles_provider_init_failure(self, mock_config):
        """
        Given a config where one provider fails to initialize
        When initialize_providers is called
        Then it logs warning and continues with remaining providers
        """
        from src.setup import initialize_providers

        async def mock_create_with_failure(name, spec, cfg, defaults):
            if name == "cerebras":
                raise Exception("Connection failed")
            return []

        with patch("src.setup.load_config", return_value=mock_config), \
             patch("src.setup.get_combiner_config", return_value=None), \
             patch("src.setup.get_formatter_config", return_value=None), \
             patch("src.setup.create_provider_instances", side_effect=mock_create_with_failure), \
             patch("src.setup.logger") as mock_logger:

            generators, combiner, formatter = await initialize_providers()

            # Should have logged the warning
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert_that(warning_call).contains("cerebras")

    async def test_initialize_providers_multiple_providers(self):
        """
        Given a config with multiple enabled providers
        When initialize_providers is called
        Then all providers are returned in generators list
        """
        from src.setup import initialize_providers

        config = AppConfig(
            defaults=DefaultsConfig(),
            providers={
                "cerebras": ProviderConfig(enabled=True, model="llama-70b"),
                "openrouter": ProviderConfig(enabled=True, model="gpt-4"),
            },
            generation=GenerationConfig(),
            paths=PathsConfig(),
        )

        provider1 = MockProvider(name="cerebras", model="llama-70b")
        provider2 = MockProvider(name="openrouter", model="gpt-4")

        async def mock_create(name, spec, cfg, defaults):
            if name == "cerebras":
                return [provider1]
            elif name == "openrouter":
                return [provider2]
            return []

        with patch("src.setup.load_config", return_value=config), \
             patch("src.setup.get_combiner_config", return_value=None), \
             patch("src.setup.get_formatter_config", return_value=None), \
             patch("src.setup.create_provider_instances", side_effect=mock_create):

            generators, combiner, formatter = await initialize_providers()

            assert_that(generators).is_length(2)
            names = [p.name for p in generators]
            assert_that(names).contains("cerebras", "openrouter")

    async def test_initialize_providers_with_formatter(self):
        """
        Given a config with formatter configured
        When initialize_providers is called
        Then formatter is returned separately
        """
        from src.setup import initialize_providers

        config = AppConfig(
            defaults=DefaultsConfig(),
            providers={
                "cerebras": ProviderConfig(enabled=True, model="llama-70b"),
            },
            generation=GenerationConfig(
                formatter=FormatterConfig(
                    provider="cerebras",
                    model="llama-70b",
                    also_generate=True,
                )
            ),
            paths=PathsConfig(),
        )

        provider = MockProvider(name="cerebras", model="llama-70b")
        formatter_cfg = FormatterConfig(
            provider="cerebras",
            model="llama-70b",
            also_generate=True,
        )

        with patch("src.setup.load_config", return_value=config), \
             patch("src.setup.get_combiner_config", return_value=None), \
             patch("src.setup.get_formatter_config", return_value=formatter_cfg), \
             patch("src.setup.create_provider_instances", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = [provider]

            generators, combiner, formatter = await initialize_providers()

            # With also_generate=True, provider should be in generators AND be formatter
            assert_that(generators).is_length(1)
            assert_that(formatter).is_not_none()
            assert_that(formatter.name).is_equal_to("cerebras")
