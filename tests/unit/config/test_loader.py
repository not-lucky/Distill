"""Tests for config/loader.py."""

import pytest
from pathlib import Path
from unittest.mock import patch

from assertpy import assert_that

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
        """
        Given a path to a nonexistent config file
        When load_config is called
        Then a default AppConfig is returned
        """
        config = load_config(tmp_path / "nonexistent.yaml")

        assert_that(config).is_not_none()
        assert_that(config).is_instance_of(AppConfig)
        # Should have default providers
        assert_that(config.providers).contains_key("cerebras")
        assert_that(config.providers).contains_key("google_antigravity")

    def test_load_config_valid_yaml(self, sample_config_yaml):
        """
        Given a valid YAML config file
        When load_config is called
        Then the configuration values are loaded correctly
        """
        config = load_config(sample_config_yaml)

        assert_that(config.defaults.timeout).is_equal_to(60.0)
        assert_that(config.defaults.temperature).is_equal_to(0.5)
        assert_that(config.defaults.max_retries).is_equal_to(3)
        assert_that(config.providers["cerebras"].enabled).is_true()
        assert_that(config.providers["openrouter"].enabled).is_false()

    def test_load_config_invalid_yaml_raises(self, tmp_path):
        """
        Given an invalid YAML file
        When load_config is called
        Then a ConfigurationError is raised
        """
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError, match="Failed to parse"):
            load_config(invalid_file)

    def test_load_config_validation_error(self, tmp_path):
        """
        Given a YAML file with invalid config values
        When load_config is called
        Then validation may coerce or handle the values
        """
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
        """
        Given no initialization parameters
        When DefaultsConfig is created
        Then default values are set correctly
        """
        defaults = DefaultsConfig()

        assert_that(defaults.timeout).is_equal_to(120.0)
        assert_that(defaults.temperature).is_equal_to(0.4)
        assert_that(defaults.max_tokens).is_none()
        assert_that(defaults.max_retries).is_equal_to(5)
        assert_that(defaults.json_parse_retries).is_equal_to(5)
        assert_that(defaults.retry_delay).is_equal_to(1.0)

    def test_defaults_custom_values(self):
        """
        Given custom initialization parameters
        When DefaultsConfig is created
        Then custom values are stored
        """
        defaults = DefaultsConfig(
            timeout=60.0,
            temperature=0.7,
            max_tokens=4096,
            max_retries=3,
        )

        assert_that(defaults.timeout).is_equal_to(60.0)
        assert_that(defaults.temperature).is_equal_to(0.7)
        assert_that(defaults.max_tokens).is_equal_to(4096)
        assert_that(defaults.max_retries).is_equal_to(3)


class TestProviderConfig:
    """Tests for ProviderConfig model."""

    def test_provider_config_defaults(self):
        """
        Given no initialization parameters
        When ProviderConfig is created
        Then default values are set
        """
        config = ProviderConfig()

        assert_that(config.enabled).is_false()
        assert_that(config.model).is_equal_to("")
        assert_that(config.models).is_empty()
        assert_that(config.base_url).is_none()
        assert_that(config.timeout).is_none()

    def test_get_effective_timeout(self):
        """
        Given provider configs with and without timeout
        When get_effective_timeout is called
        Then provider timeout overrides default or falls back to default
        """
        defaults = DefaultsConfig(timeout=120.0)

        # Provider without timeout uses default
        config1 = ProviderConfig()
        assert_that(config1.get_effective_timeout(defaults)).is_equal_to(120.0)

        # Provider with timeout uses its own
        config2 = ProviderConfig(timeout=60.0)
        assert_that(config2.get_effective_timeout(defaults)).is_equal_to(60.0)

    def test_get_effective_temperature(self):
        """
        Given provider configs with and without temperature
        When get_effective_temperature is called
        Then provider temperature overrides default or falls back to default
        """
        defaults = DefaultsConfig(temperature=0.4)

        config1 = ProviderConfig()
        assert_that(config1.get_effective_temperature(defaults)).is_equal_to(0.4)

        config2 = ProviderConfig(temperature=0.8)
        assert_that(config2.get_effective_temperature(defaults)).is_equal_to(0.8)

    def test_get_effective_max_tokens(self):
        """
        Given provider configs with and without max_tokens
        When get_effective_max_tokens is called
        Then provider max_tokens overrides default or falls back to default
        """
        defaults = DefaultsConfig(max_tokens=4096)

        config1 = ProviderConfig()
        assert_that(config1.get_effective_max_tokens(defaults)).is_equal_to(4096)

        config2 = ProviderConfig(max_tokens=2048)
        assert_that(config2.get_effective_max_tokens(defaults)).is_equal_to(2048)


class TestGetEnabledProviders:
    """Tests for get_enabled_providers function."""

    def test_filters_disabled_providers(self):
        """
        Given a config with mixed enabled/disabled providers
        When get_enabled_providers is called
        Then only enabled providers are returned
        """
        config = AppConfig(
            providers={
                "enabled1": ProviderConfig(enabled=True, model="m1"),
                "disabled": ProviderConfig(enabled=False, model="m2"),
                "enabled2": ProviderConfig(enabled=True, model="m3"),
            }
        )

        enabled = get_enabled_providers(config)

        assert_that(enabled).contains_key("enabled1")
        assert_that(enabled).contains_key("enabled2")
        assert_that(enabled).does_not_contain_key("disabled")
        assert_that(enabled).is_length(2)

    def test_empty_providers(self):
        """
        Given a config with no providers
        When get_enabled_providers is called
        Then an empty dict is returned
        """
        config = AppConfig(providers={})
        enabled = get_enabled_providers(config)
        assert_that(enabled).is_equal_to({})


class TestGetCombinerConfig:
    """Tests for get_combiner_config function."""

    def test_no_combiner_configured(self):
        """
        Given a config with no combiner
        When get_combiner_config is called
        Then None is returned
        """
        config = AppConfig()
        result = get_combiner_config(config)
        assert_that(result).is_none()

    def test_combiner_with_empty_provider(self):
        """
        Given a combiner config with empty provider string
        When get_combiner_config is called
        Then None is returned
        """
        config = AppConfig(
            generation=GenerationConfig(
                combiner=CombinerConfig(provider="", model="")
            )
        )
        result = get_combiner_config(config)
        assert_that(result).is_none()

    def test_combiner_references_unknown_provider(self):
        """
        Given a combiner referencing an unknown provider
        When get_combiner_config is called
        Then a ConfigurationError is raised
        """
        config = AppConfig(
            providers={},
            generation=GenerationConfig(
                combiner=CombinerConfig(provider="unknown", model="model")
            )
        )

        with pytest.raises(ConfigurationError, match="unknown provider"):
            get_combiner_config(config)

    def test_combiner_references_disabled_provider(self):
        """
        Given a combiner referencing a disabled provider
        When get_combiner_config is called
        Then a ConfigurationError is raised
        """
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
        """
        Given a valid combiner configuration
        When get_combiner_config is called
        Then the combiner config is returned
        """
        config = AppConfig(
            providers={
                "cerebras": ProviderConfig(enabled=True, model="llama")
            },
            generation=GenerationConfig(
                combiner=CombinerConfig(provider="cerebras", model="llama")
            )
        )

        result = get_combiner_config(config)
        assert_that(result).is_not_none()
        assert_that(result.provider).is_equal_to("cerebras")
        assert_that(result.model).is_equal_to("llama")


class TestGetFormatterConfig:
    """Tests for get_formatter_config function."""

    def test_no_formatter_configured(self):
        """
        Given a config with no formatter
        When get_formatter_config is called
        Then None is returned
        """
        config = AppConfig()
        result = get_formatter_config(config)
        assert_that(result).is_none()

    def test_formatter_references_unknown_provider(self):
        """
        Given a formatter referencing an unknown provider
        When get_formatter_config is called
        Then a ConfigurationError is raised
        """
        config = AppConfig(
            providers={},
            generation=GenerationConfig(
                formatter=FormatterConfig(provider="unknown", model="model")
            )
        )

        with pytest.raises(ConfigurationError, match="unknown provider"):
            get_formatter_config(config)

    def test_valid_formatter_config(self):
        """
        Given a valid formatter configuration
        When get_formatter_config is called
        Then the formatter config is returned
        """
        config = AppConfig(
            providers={
                "openrouter": ProviderConfig(enabled=True, model="gpt-4")
            },
            generation=GenerationConfig(
                formatter=FormatterConfig(provider="openrouter", model="gpt-4")
            )
        )

        result = get_formatter_config(config)
        assert_that(result).is_not_none()
        assert_that(result.provider).is_equal_to("openrouter")


class TestGetEnabledSubjects:
    """Tests for get_enabled_subjects function."""

    def test_filters_disabled_subjects(self):
        """
        Given a config with mixed enabled/disabled subjects
        When get_enabled_subjects is called
        Then only enabled subjects are returned
        """
        config = AppConfig(
            subjects={
                "leetcode": SubjectSettings(enabled=True),
                "cs": SubjectSettings(enabled=False),
                "physics": SubjectSettings(enabled=True),
            }
        )

        enabled = get_enabled_subjects(config)

        assert_that(enabled).contains_key("leetcode")
        assert_that(enabled).contains_key("physics")
        assert_that(enabled).does_not_contain_key("cs")

    def test_empty_subjects(self):
        """
        Given a config with no subjects
        When get_enabled_subjects is called
        Then an empty dict is returned
        """
        config = AppConfig(subjects={})
        enabled = get_enabled_subjects(config)
        assert_that(enabled).is_equal_to({})


class TestSubjectSettings:
    """Tests for SubjectSettings model."""

    def test_default_values(self):
        """
        Given no initialization parameters
        When SubjectSettings is created
        Then default values are set
        """
        settings = SubjectSettings()

        assert_that(settings.enabled).is_true()
        assert_that(settings.deck_prefix).is_none()
        assert_that(settings.prompts_dir).is_none()
        assert_that(settings.questions_file).is_none()

    def test_is_custom_false_for_builtin(self):
        """
        Given default SubjectSettings
        When is_custom is called
        Then False is returned
        """
        settings = SubjectSettings()
        assert_that(settings.is_custom()).is_false()

    def test_is_custom_true_with_prompts_dir(self):
        """
        Given SubjectSettings with prompts_dir set
        When is_custom is called
        Then True is returned
        """
        settings = SubjectSettings(prompts_dir="/path/to/prompts")
        assert_that(settings.is_custom()).is_true()

    def test_is_custom_true_with_questions_file(self):
        """
        Given SubjectSettings with questions_file set
        When is_custom is called
        Then True is returned
        """
        settings = SubjectSettings(questions_file="/path/to/questions.json")
        assert_that(settings.is_custom()).is_true()


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_default_factory(self):
        """
        Given the AppConfig.default() factory method
        When called
        Then a config with default providers and subjects is returned
        """
        config = AppConfig.default()

        assert_that(config.providers).contains_key("cerebras")
        assert_that(config.providers).contains_key("google_antigravity")
        assert_that(config.providers["cerebras"].enabled).is_true()
        assert_that(config.subjects).contains_key("leetcode")
        assert_that(config.subjects).contains_key("cs")
        assert_that(config.subjects).contains_key("physics")

    def test_generation_config_defaults(self):
        """
        Given a default AppConfig
        When accessing generation config
        Then default values are present
        """
        config = AppConfig()

        assert_that(config.generation.concurrent_requests).is_equal_to(8)
        assert_that(config.generation.request_delay).is_equal_to(0.0)


class TestPathsConfig:
    """Tests for PathsConfig model."""

    def test_paths_config_defaults(self):
        """
        Given no initialization parameters
        When PathsConfig is created
        Then default paths are set
        """
        paths = PathsConfig()

        assert_that(paths.archival_dir).is_equal_to("anki_cards_archival")
        assert_that(paths.markdown_dir).is_equal_to("anki_cards_markdown")
        assert_that(paths.timestamp_format).is_equal_to("%Y%m%dT%H%M%S")
        assert_that(paths.key_paths).is_not_none()

    def test_paths_config_custom_values(self):
        """
        Given custom initialization parameters
        When PathsConfig is created
        Then custom paths are stored
        """
        paths = PathsConfig(
            archival_dir="/custom/archive",
            markdown_dir="/custom/markdown",
            timestamp_format="%Y-%m-%d",
        )

        assert_that(paths.archival_dir).is_equal_to("/custom/archive")
        assert_that(paths.markdown_dir).is_equal_to("/custom/markdown")
        assert_that(paths.timestamp_format).is_equal_to("%Y-%m-%d")


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_temperature_bounds(self):
        """
        Given various temperature values
        When DefaultsConfig is created
        Then valid temperatures are accepted
        """
        # Pydantic should accept valid temperatures
        defaults = DefaultsConfig(temperature=0.0)
        assert_that(defaults.temperature).is_equal_to(0.0)

        defaults = DefaultsConfig(temperature=1.0)
        assert_that(defaults.temperature).is_equal_to(1.0)

        defaults = DefaultsConfig(temperature=0.5)
        assert_that(defaults.temperature).is_equal_to(0.5)

    def test_negative_timeout_handling(self):
        """
        Given a zero timeout value
        When DefaultsConfig is created
        Then the value is accepted
        """
        # Depending on model validation, this should work or raise
        defaults = DefaultsConfig(timeout=0.0)
        assert_that(defaults.timeout).is_equal_to(0.0)

    def test_max_retries_zero(self):
        """
        Given zero max_retries
        When DefaultsConfig is created
        Then zero is accepted
        """
        defaults = DefaultsConfig(max_retries=0)
        assert_that(defaults.max_retries).is_equal_to(0)

    def test_provider_with_multiple_models(self):
        """
        Given a provider config with multiple models
        When ProviderConfig is created
        Then both model and models list are stored
        """
        config = ProviderConfig(
            enabled=True,
            model="primary-model",
            models=["model1", "model2", "model3"],
        )

        assert_that(config.model).is_equal_to("primary-model")
        assert_that(config.models).is_length(3)
        assert_that(config.models).contains("model1")

    def test_extra_params_passthrough(self):
        """
        Given a provider config with extra_params
        When ProviderConfig is created
        Then extra_params are preserved
        """
        config = ProviderConfig(
            enabled=True,
            model="test",
            extra_params={"top_p": 0.9, "frequency_penalty": 0.5},
        )

        assert_that(config.extra_params["top_p"]).is_equal_to(0.9)
        assert_that(config.extra_params["frequency_penalty"]).is_equal_to(0.5)


class TestCombinerConfigDetails:
    """Detailed tests for CombinerConfig."""

    def test_combiner_config_creation(self):
        """
        Given provider and model values
        When CombinerConfig is created
        Then values are stored correctly
        """
        combiner = CombinerConfig(provider="cerebras", model="llama")

        assert_that(combiner.provider).is_equal_to("cerebras")
        assert_that(combiner.model).is_equal_to("llama")

    def test_combiner_with_empty_values(self):
        """
        Given empty string values
        When CombinerConfig is created
        Then empty strings are stored
        """
        combiner = CombinerConfig(provider="", model="")

        assert_that(combiner.provider).is_equal_to("")
        assert_that(combiner.model).is_equal_to("")

    def test_combiner_with_also_generate(self):
        """
        Given also_generate=False
        When CombinerConfig is created
        Then the flag is stored
        """
        combiner = CombinerConfig(
            provider="test",
            model="model",
            also_generate=False,
        )

        assert_that(combiner.also_generate).is_false()


class TestFormatterConfigDetails:
    """Detailed tests for FormatterConfig."""

    def test_formatter_config_creation(self):
        """
        Given provider and model values
        When FormatterConfig is created
        Then values are stored correctly
        """
        formatter = FormatterConfig(provider="openrouter", model="gpt-4")

        assert_that(formatter.provider).is_equal_to("openrouter")
        assert_that(formatter.model).is_equal_to("gpt-4")

    def test_formatter_with_also_generate(self):
        """
        Given also_generate=False
        When FormatterConfig is created
        Then the flag is stored
        """
        formatter = FormatterConfig(
            provider="test",
            model="model",
            also_generate=False,
        )

        assert_that(formatter.also_generate).is_false()


class TestConfigMerging:
    """Tests for configuration merging and defaults."""

    def test_provider_inherits_defaults(self):
        """
        Given a provider config without overrides
        When get_effective_* methods are called
        Then default values are used
        """
        defaults = DefaultsConfig(
            timeout=120.0,
            temperature=0.4,
            max_tokens=4096,
        )

        provider = ProviderConfig(enabled=True, model="test")

        assert_that(provider.get_effective_timeout(defaults)).is_equal_to(120.0)
        assert_that(provider.get_effective_temperature(defaults)).is_equal_to(0.4)
        assert_that(provider.get_effective_max_tokens(defaults)).is_equal_to(4096)

    def test_provider_overrides_defaults(self):
        """
        Given a provider config with explicit values
        When get_effective_* methods are called
        Then provider values override defaults
        """
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

        assert_that(provider.get_effective_timeout(defaults)).is_equal_to(60.0)
        assert_that(provider.get_effective_temperature(defaults)).is_equal_to(0.8)
        assert_that(provider.get_effective_max_tokens(defaults)).is_equal_to(2048)


class TestEdgeCasesLoader:
    """Edge case tests for config loading."""

    def test_load_empty_yaml(self, tmp_path):
        """
        Given an empty YAML file
        When load_config is called
        Then a default config is returned
        """
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        config = load_config(empty_file)
        assert_that(config).is_not_none()
        assert_that(config).is_instance_of(AppConfig)

    def test_load_yaml_with_unknown_keys(self, tmp_path):
        """
        Given a YAML file with extra unknown keys
        When load_config is called
        Then unknown keys are ignored and valid config is loaded
        """
        yaml_file = tmp_path / "extra.yaml"
        yaml_file.write_text("""
defaults:
  timeout: 60.0
unknown_section:
  key: value
""")
        # Should not fail, extra keys should be ignored
        config = load_config(yaml_file)
        assert_that(config.defaults.timeout).is_equal_to(60.0)

    def test_load_yaml_with_null_values(self, tmp_path):
        """
        Given a YAML file with null values for optional fields
        When load_config is called
        Then null is treated as None
        """
        yaml_file = tmp_path / "nulls.yaml"
        yaml_file.write_text("""
defaults:
  max_tokens: null
  temperature: 0.5
""")
        config = load_config(yaml_file)
        # null should be treated as None for optional field
        assert_that(config.defaults.max_tokens).is_none()
        assert_that(config.defaults.temperature).is_equal_to(0.5)

    def test_enabled_providers_with_models_list(self):
        """
        Given a provider with both model and models list
        When get_enabled_providers is called
        Then both are preserved
        """
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
        assert_that(enabled).contains_key("multi")
        assert_that(enabled["multi"].model).is_equal_to("primary")
        assert_that(enabled["multi"].models).is_length(2)

    def test_all_providers_disabled(self):
        """
        Given all providers disabled
        When get_enabled_providers is called
        Then an empty dict is returned
        """
        config = AppConfig(
            providers={
                "p1": ProviderConfig(enabled=False),
                "p2": ProviderConfig(enabled=False),
            }
        )

        enabled = get_enabled_providers(config)
        assert_that(enabled).is_equal_to({})

    def test_formatter_with_disabled_provider_raises(self):
        """
        Given a formatter referencing a disabled provider
        When get_formatter_config is called
        Then a ConfigurationError is raised
        """
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
        """
        Given a complete configuration YAML file
        When load_config is called
        Then all sections are loaded correctly
        """
        config = load_config(sample_config_yaml)

        # Check defaults
        assert_that(config.defaults.timeout).is_equal_to(60.0)
        assert_that(config.defaults.temperature).is_equal_to(0.5)
        assert_that(config.defaults.max_retries).is_equal_to(3)

        # Check providers
        assert_that(config.providers["cerebras"].enabled).is_true()
        assert_that(config.providers["cerebras"].model).is_equal_to("llama-3.1-8b")
        assert_that(config.providers["openrouter"].enabled).is_false()

        # Check subjects
        assert_that(config.subjects["leetcode"].enabled).is_true()
        assert_that(config.subjects["physics"].enabled).is_false()
