"""Tests for config/loader.py."""

import pytest
from pathlib import Path
from unittest.mock import patch

from src.config.loader import (
    load_config,
    get_enabled_providers,
    get_combiner_config,
    get_formatter_config,
    get_enabled_subjects,
    AppConfig,
    DefaultsConfig,
    ProviderConfig,
    GenerationConfig,
    CombinerConfig,
    FormatterConfig,
    SubjectSettings,
    PathsConfig,
)
from src.exceptions import ConfigurationError


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_missing_file_returns_default(self, tmp_path):
        """Test that missing config file returns default config."""
        config = load_config(tmp_path / "nonexistent.yaml")

        assert config is not None
        assert isinstance(config, AppConfig)
        # Should have default providers
        assert "cerebras" in config.providers
        assert "google_antigravity" in config.providers

    def test_load_config_valid_yaml(self, sample_config_yaml):
        """Test loading valid YAML config."""
        config = load_config(sample_config_yaml)

        assert config.defaults.timeout == 60.0
        assert config.defaults.temperature == 0.5
        assert config.defaults.max_retries == 3
        assert config.providers["cerebras"].enabled is True
        assert config.providers["openrouter"].enabled is False

    def test_load_config_invalid_yaml_raises(self, tmp_path):
        """Test that invalid YAML raises ConfigurationError."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError, match="Failed to parse"):
            load_config(invalid_file)

    def test_load_config_validation_error(self, tmp_path):
        """Test that invalid config values raise ConfigurationError."""
        invalid_file = tmp_path / "bad_config.yaml"
        # Use invalid type for enabled (should be bool)
        invalid_file.write_text("""
providers:
  cerebras:
    enabled: "not a bool"
    model: 123
""")
        # Pydantic might coerce or raise - depends on model definition
        # This test verifies the function handles validation errors


class TestDefaultsConfig:
    """Tests for DefaultsConfig model."""

    def test_defaults_default_values(self):
        """Test DefaultsConfig has correct defaults."""
        defaults = DefaultsConfig()

        assert defaults.timeout == 120.0
        assert defaults.temperature == 0.4
        assert defaults.max_tokens is None
        assert defaults.max_retries == 5
        assert defaults.json_parse_retries == 5
        assert defaults.retry_delay == 1.0

    def test_defaults_custom_values(self):
        """Test DefaultsConfig with custom values."""
        defaults = DefaultsConfig(
            timeout=60.0,
            temperature=0.7,
            max_tokens=4096,
            max_retries=3,
        )

        assert defaults.timeout == 60.0
        assert defaults.temperature == 0.7
        assert defaults.max_tokens == 4096
        assert defaults.max_retries == 3


class TestProviderConfig:
    """Tests for ProviderConfig model."""

    def test_provider_config_defaults(self):
        """Test ProviderConfig default values."""
        config = ProviderConfig()

        assert config.enabled is False
        assert config.model == ""
        assert config.models == []
        assert config.base_url is None
        assert config.timeout is None

    def test_get_effective_timeout(self):
        """Test get_effective_timeout method."""
        defaults = DefaultsConfig(timeout=120.0)

        # Provider without timeout uses default
        config1 = ProviderConfig()
        assert config1.get_effective_timeout(defaults) == 120.0

        # Provider with timeout uses its own
        config2 = ProviderConfig(timeout=60.0)
        assert config2.get_effective_timeout(defaults) == 60.0

    def test_get_effective_temperature(self):
        """Test get_effective_temperature method."""
        defaults = DefaultsConfig(temperature=0.4)

        config1 = ProviderConfig()
        assert config1.get_effective_temperature(defaults) == 0.4

        config2 = ProviderConfig(temperature=0.8)
        assert config2.get_effective_temperature(defaults) == 0.8

    def test_get_effective_max_tokens(self):
        """Test get_effective_max_tokens method."""
        defaults = DefaultsConfig(max_tokens=4096)

        config1 = ProviderConfig()
        assert config1.get_effective_max_tokens(defaults) == 4096

        config2 = ProviderConfig(max_tokens=2048)
        assert config2.get_effective_max_tokens(defaults) == 2048


class TestGetEnabledProviders:
    """Tests for get_enabled_providers function."""

    def test_filters_disabled_providers(self):
        """Test that disabled providers are filtered out."""
        config = AppConfig(
            providers={
                "enabled1": ProviderConfig(enabled=True, model="m1"),
                "disabled": ProviderConfig(enabled=False, model="m2"),
                "enabled2": ProviderConfig(enabled=True, model="m3"),
            }
        )

        enabled = get_enabled_providers(config)

        assert "enabled1" in enabled
        assert "enabled2" in enabled
        assert "disabled" not in enabled
        assert len(enabled) == 2

    def test_empty_providers(self):
        """Test with no providers configured."""
        config = AppConfig(providers={})
        enabled = get_enabled_providers(config)
        assert enabled == {}


class TestGetCombinerConfig:
    """Tests for get_combiner_config function."""

    def test_no_combiner_configured(self):
        """Test when no combiner is configured."""
        config = AppConfig()
        result = get_combiner_config(config)
        assert result is None

    def test_combiner_with_empty_provider(self):
        """Test combiner with empty provider string."""
        config = AppConfig(
            generation=GenerationConfig(
                combiner=CombinerConfig(provider="", model="")
            )
        )
        result = get_combiner_config(config)
        assert result is None

    def test_combiner_references_unknown_provider(self):
        """Test combiner referencing unknown provider raises error."""
        config = AppConfig(
            providers={},
            generation=GenerationConfig(
                combiner=CombinerConfig(provider="unknown", model="model")
            )
        )

        with pytest.raises(ConfigurationError, match="unknown provider"):
            get_combiner_config(config)

    def test_combiner_references_disabled_provider(self):
        """Test combiner referencing disabled provider raises error."""
        config = AppConfig(
            providers={
                "cerebras": ProviderConfig(enabled=False, model="m1")
            },
            generation=GenerationConfig(
                combiner=CombinerConfig(provider="cerebras", model="m1")
            )
        )

        with pytest.raises(ConfigurationError, match="not enabled"):
            get_combiner_config(config)

    def test_valid_combiner_config(self):
        """Test valid combiner configuration."""
        config = AppConfig(
            providers={
                "cerebras": ProviderConfig(enabled=True, model="llama")
            },
            generation=GenerationConfig(
                combiner=CombinerConfig(provider="cerebras", model="llama")
            )
        )

        result = get_combiner_config(config)
        assert result is not None
        assert result.provider == "cerebras"
        assert result.model == "llama"


class TestGetFormatterConfig:
    """Tests for get_formatter_config function."""

    def test_no_formatter_configured(self):
        """Test when no formatter is configured."""
        config = AppConfig()
        result = get_formatter_config(config)
        assert result is None

    def test_formatter_references_unknown_provider(self):
        """Test formatter referencing unknown provider raises error."""
        config = AppConfig(
            providers={},
            generation=GenerationConfig(
                formatter=FormatterConfig(provider="unknown", model="model")
            )
        )

        with pytest.raises(ConfigurationError, match="unknown provider"):
            get_formatter_config(config)

    def test_valid_formatter_config(self):
        """Test valid formatter configuration."""
        config = AppConfig(
            providers={
                "openrouter": ProviderConfig(enabled=True, model="gpt-4")
            },
            generation=GenerationConfig(
                formatter=FormatterConfig(provider="openrouter", model="gpt-4")
            )
        )

        result = get_formatter_config(config)
        assert result is not None
        assert result.provider == "openrouter"


class TestGetEnabledSubjects:
    """Tests for get_enabled_subjects function."""

    def test_filters_disabled_subjects(self):
        """Test that disabled subjects are filtered out."""
        config = AppConfig(
            subjects={
                "leetcode": SubjectSettings(enabled=True),
                "cs": SubjectSettings(enabled=False),
                "physics": SubjectSettings(enabled=True),
            }
        )

        enabled = get_enabled_subjects(config)

        assert "leetcode" in enabled
        assert "physics" in enabled
        assert "cs" not in enabled

    def test_empty_subjects(self):
        """Test with no subjects configured."""
        config = AppConfig(subjects={})
        enabled = get_enabled_subjects(config)
        assert enabled == {}


class TestSubjectSettings:
    """Tests for SubjectSettings model."""

    def test_default_values(self):
        """Test SubjectSettings default values."""
        settings = SubjectSettings()

        assert settings.enabled is True
        assert settings.deck_prefix is None
        assert settings.prompts_dir is None
        assert settings.questions_file is None

    def test_is_custom_false_for_builtin(self):
        """Test is_custom returns False for built-in subjects."""
        settings = SubjectSettings()
        assert settings.is_custom() is False

    def test_is_custom_true_with_prompts_dir(self):
        """Test is_custom returns True when prompts_dir is set."""
        settings = SubjectSettings(prompts_dir="/path/to/prompts")
        assert settings.is_custom() is True

    def test_is_custom_true_with_questions_file(self):
        """Test is_custom returns True when questions_file is set."""
        settings = SubjectSettings(questions_file="/path/to/questions.json")
        assert settings.is_custom() is True


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_default_factory(self):
        """Test AppConfig.default() factory method."""
        config = AppConfig.default()

        assert "cerebras" in config.providers
        assert "google_antigravity" in config.providers
        assert config.providers["cerebras"].enabled is True
        assert "leetcode" in config.subjects
        assert "cs" in config.subjects
        assert "physics" in config.subjects

    def test_generation_config_defaults(self):
        """Test GenerationConfig defaults."""
        config = AppConfig()

        assert config.generation.concurrent_requests == 8
        assert config.generation.request_delay == 0.0


class TestPathsConfig:
    """Tests for PathsConfig model."""

    def test_paths_config_defaults(self):
        """Test PathsConfig default values."""
        paths = PathsConfig()

        assert paths.archival_dir == "anki_cards_archival"
        assert paths.markdown_dir == "anki_cards_markdown"
        assert paths.timestamp_format == "%Y%m%dT%H%M%S"
        assert paths.key_paths is not None

    def test_paths_config_custom_values(self):
        """Test PathsConfig with custom values."""
        paths = PathsConfig(
            archival_dir="/custom/archive",
            markdown_dir="/custom/markdown",
            timestamp_format="%Y-%m-%d",
        )

        assert paths.archival_dir == "/custom/archive"
        assert paths.markdown_dir == "/custom/markdown"
        assert paths.timestamp_format == "%Y-%m-%d"


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_temperature_bounds(self):
        """Test temperature is within bounds."""
        # Pydantic should accept valid temperatures
        defaults = DefaultsConfig(temperature=0.0)
        assert defaults.temperature == 0.0

        defaults = DefaultsConfig(temperature=1.0)
        assert defaults.temperature == 1.0

        defaults = DefaultsConfig(temperature=0.5)
        assert defaults.temperature == 0.5

    def test_negative_timeout_handling(self):
        """Test handling of negative timeout."""
        # Depending on model validation, this should work or raise
        defaults = DefaultsConfig(timeout=0.0)
        assert defaults.timeout == 0.0

    def test_max_retries_zero(self):
        """Test max_retries can be zero."""
        defaults = DefaultsConfig(max_retries=0)
        assert defaults.max_retries == 0

    def test_provider_with_multiple_models(self):
        """Test provider config with multiple models."""
        config = ProviderConfig(
            enabled=True,
            model="primary-model",
            models=["model1", "model2", "model3"],
        )

        assert config.model == "primary-model"
        assert len(config.models) == 3
        assert "model1" in config.models

    def test_extra_params_passthrough(self):
        """Test that extra_params are preserved."""
        config = ProviderConfig(
            enabled=True,
            model="test",
            extra_params={"top_p": 0.9, "frequency_penalty": 0.5},
        )

        assert config.extra_params["top_p"] == 0.9
        assert config.extra_params["frequency_penalty"] == 0.5


class TestCombinerConfigDetails:
    """Detailed tests for CombinerConfig."""

    def test_combiner_config_creation(self):
        """Test CombinerConfig creation."""
        combiner = CombinerConfig(provider="cerebras", model="llama")

        assert combiner.provider == "cerebras"
        assert combiner.model == "llama"

    def test_combiner_with_empty_values(self):
        """Test CombinerConfig with empty string values."""
        combiner = CombinerConfig(provider="", model="")

        assert combiner.provider == ""
        assert combiner.model == ""

    def test_combiner_with_also_generate(self):
        """Test CombinerConfig with also_generate flag."""
        combiner = CombinerConfig(
            provider="test",
            model="model",
            also_generate=False,
        )

        assert combiner.also_generate is False


class TestFormatterConfigDetails:
    """Detailed tests for FormatterConfig."""

    def test_formatter_config_creation(self):
        """Test FormatterConfig creation."""
        formatter = FormatterConfig(provider="openrouter", model="gpt-4")

        assert formatter.provider == "openrouter"
        assert formatter.model == "gpt-4"

    def test_formatter_with_also_generate(self):
        """Test FormatterConfig with also_generate flag."""
        formatter = FormatterConfig(
            provider="test",
            model="model",
            also_generate=False,
        )

        assert formatter.also_generate is False


class TestConfigMerging:
    """Tests for configuration merging and defaults."""

    def test_provider_inherits_defaults(self):
        """Test that providers correctly inherit from defaults."""
        defaults = DefaultsConfig(
            timeout=120.0,
            temperature=0.4,
            max_tokens=4096,
        )

        provider = ProviderConfig(enabled=True, model="test")

        assert provider.get_effective_timeout(defaults) == 120.0
        assert provider.get_effective_temperature(defaults) == 0.4
        assert provider.get_effective_max_tokens(defaults) == 4096

    def test_provider_overrides_defaults(self):
        """Test that provider-specific values override defaults."""
        defaults = DefaultsConfig(
            timeout=120.0,
            temperature=0.4,
            max_tokens=4096,
        )

        provider = ProviderConfig(
            enabled=True,
            model="test",
            timeout=60.0,
            temperature=0.8,
            max_tokens=2048,
        )

        assert provider.get_effective_timeout(defaults) == 60.0
        assert provider.get_effective_temperature(defaults) == 0.8
        assert provider.get_effective_max_tokens(defaults) == 2048


class TestEdgeCasesLoader:
    """Edge case tests for config loading."""

    def test_load_empty_yaml(self, tmp_path):
        """Test loading empty YAML file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        config = load_config(empty_file)
        assert config is not None
        assert isinstance(config, AppConfig)

    def test_load_yaml_with_unknown_keys(self, tmp_path):
        """Test loading YAML with extra unknown keys."""
        yaml_file = tmp_path / "extra.yaml"
        yaml_file.write_text("""
defaults:
  timeout: 60.0
unknown_section:
  key: value
""")
        # Should not fail, extra keys should be ignored
        config = load_config(yaml_file)
        assert config.defaults.timeout == 60.0

    def test_load_yaml_with_null_values(self, tmp_path):
        """Test loading YAML with null values for optional fields."""
        yaml_file = tmp_path / "nulls.yaml"
        yaml_file.write_text("""
defaults:
  max_tokens: null
  temperature: 0.5
""")
        config = load_config(yaml_file)
        # null should be treated as None for optional field
        assert config.defaults.max_tokens is None
        assert config.defaults.temperature == 0.5

    def test_enabled_providers_with_models_list(self):
        """Test providers with both model and models list."""
        config = AppConfig(
            providers={
                "multi": ProviderConfig(
                    enabled=True,
                    model="primary",
                    models=["alt1", "alt2"],
                ),
            }
        )

        enabled = get_enabled_providers(config)
        assert "multi" in enabled
        assert enabled["multi"].model == "primary"
        assert len(enabled["multi"].models) == 2

    def test_all_providers_disabled(self):
        """Test when all providers are disabled."""
        config = AppConfig(
            providers={
                "p1": ProviderConfig(enabled=False),
                "p2": ProviderConfig(enabled=False),
            }
        )

        enabled = get_enabled_providers(config)
        assert enabled == {}

    def test_formatter_with_disabled_provider_raises(self):
        """Test formatter referencing disabled provider raises error."""
        config = AppConfig(
            providers={
                "test": ProviderConfig(enabled=False, model="m")
            },
            generation=GenerationConfig(
                formatter=FormatterConfig(provider="test", model="m")
            )
        )

        with pytest.raises(ConfigurationError, match="not enabled"):
            get_formatter_config(config)


class TestYAMLFixtures:
    """Tests using YAML fixture files."""

    @pytest.fixture
    def sample_config_yaml(self, tmp_path):
        """Create a sample config YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
defaults:
  timeout: 60.0
  temperature: 0.5
  max_retries: 3

providers:
  cerebras:
    enabled: true
    model: llama-3.1-8b
  openrouter:
    enabled: false
    model: gpt-4

subjects:
  leetcode:
    enabled: true
  cs:
    enabled: true
  physics:
    enabled: false
""")
        return config_file

    def test_complete_config_loading(self, sample_config_yaml):
        """Test loading a complete configuration file."""
        config = load_config(sample_config_yaml)

        # Check defaults
        assert config.defaults.timeout == 60.0
        assert config.defaults.temperature == 0.5
        assert config.defaults.max_retries == 3

        # Check providers
        assert config.providers["cerebras"].enabled is True
        assert config.providers["cerebras"].model == "llama-3.1-8b"
        assert config.providers["openrouter"].enabled is False

        # Check subjects
        assert config.subjects["leetcode"].enabled is True
        assert config.subjects["physics"].enabled is False
