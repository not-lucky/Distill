"""Tests for providers/registry.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import itertools

from assertpy import assert_that

from src.providers.registry import (
    PROVIDER_REGISTRY,
    ProviderSpec,
    create_provider_instances,
    DEFAULT_BASE_URLS,
)
from src.config.loader import ProviderConfig, DefaultsConfig


# =============================================================================
# PROVIDER_REGISTRY Tests
# =============================================================================


class TestProviderRegistry:
    """Tests for PROVIDER_REGISTRY constant."""

    def test_registry_contains_expected_providers(self):
        """
        Given the PROVIDER_REGISTRY constant
        When checking for expected providers
        Then all expected providers are present
        """
        expected = [
            "cerebras",
            "openrouter",
            "nvidia",
            "g4f",
            "canopywave",
            "baseten",
            "google_genai",
            "google_antigravity",
            "gemini_webapi",
        ]

        for provider in expected:
            assert_that(PROVIDER_REGISTRY).contains_key(provider)

    def test_registry_values_are_provider_specs(self):
        """
        Given the PROVIDER_REGISTRY
        When checking value types
        Then all values are ProviderSpec instances
        """
        for name, spec in PROVIDER_REGISTRY.items():
            assert_that(spec).is_instance_of(ProviderSpec)

    def test_registry_provider_classes_are_callable(self):
        """
        Given the PROVIDER_REGISTRY
        When checking provider classes
        Then all provider classes are callable
        """
        for name, spec in PROVIDER_REGISTRY.items():
            assert_that(callable(spec.provider_class)).is_true()

    def test_registry_count(self):
        """
        Given the PROVIDER_REGISTRY
        When counting entries
        Then it contains expected number of providers
        """
        assert_that(PROVIDER_REGISTRY).is_length(9)

    def test_cerebras_spec(self):
        """
        Given the cerebras provider specification
        When checking its fields
        Then it has correct key_name and extra_params
        """
        spec = PROVIDER_REGISTRY["cerebras"]
        assert_that(spec.key_name).is_equal_to("cerebras")
        assert_that(spec.extra_params).contains("reasoning_effort")
        assert_that(spec.multi_model).is_false()
        assert_that(spec.no_keys).is_false()

    def test_cerebras_spec_details(self):
        """
        Given the cerebras provider specification
        When checking provider class details
        Then it has correct provider class and flags
        """
        from src.providers.cerebras import CerebrasProvider
        spec = PROVIDER_REGISTRY["cerebras"]
        assert_that(spec.provider_class).is_same_as(CerebrasProvider)
        assert_that(spec.uses_base_url).is_false()
        assert_that(spec.factory).is_none()

    def test_openrouter_spec(self):
        """
        Given the openrouter provider specification
        When checking its fields
        Then it has correct configuration
        """
        from src.providers.openrouter import OpenRouterProvider
        spec = PROVIDER_REGISTRY["openrouter"]
        assert_that(spec.provider_class).is_same_as(OpenRouterProvider)
        assert_that(spec.key_name).is_equal_to("openrouter")
        assert_that(spec.uses_base_url).is_true()
        assert_that(spec.multi_model).is_false()

    def test_nvidia_spec(self):
        """
        Given the nvidia provider specification
        When checking its fields
        Then it has correct configuration with extra_params
        """
        from src.providers.nvidia import NvidiaProvider
        spec = PROVIDER_REGISTRY["nvidia"]
        assert_that(spec.provider_class).is_same_as(NvidiaProvider)
        assert_that(spec.key_name).is_equal_to("nvidia")
        assert_that(spec.uses_base_url).is_true()
        assert_that(spec.extra_params).contains("top_p")
        assert_that(spec.extra_params).contains("extra_params")

    def test_google_antigravity_spec(self):
        """
        Given the google_antigravity provider specification
        When checking its fields
        Then it has no_keys=True and multi_model=True
        """
        spec = PROVIDER_REGISTRY["google_antigravity"]
        assert_that(spec.no_keys).is_true()
        assert_that(spec.multi_model).is_true()
        assert_that(spec.uses_base_url).is_true()

    def test_google_antigravity_spec_details(self):
        """
        Given the google_antigravity provider specification
        When checking provider class details
        Then it has correct provider class
        """
        from src.providers.google_antigravity import GoogleAntigravityProvider
        spec = PROVIDER_REGISTRY["google_antigravity"]
        assert_that(spec.provider_class).is_same_as(GoogleAntigravityProvider)
        assert_that(spec.key_name).is_none()
        assert_that(spec.factory).is_none()

    def test_g4f_spec(self):
        """
        Given the g4f provider specification
        When checking its fields
        Then it has no_keys=True and provider_name in extra_params
        """
        spec = PROVIDER_REGISTRY["g4f"]
        assert_that(spec.no_keys).is_true()
        assert_that(spec.extra_params).contains("provider_name")

    def test_g4f_spec_details(self):
        """
        Given the g4f provider specification
        When checking provider class details
        Then it has correct configuration
        """
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider
            spec = PROVIDER_REGISTRY["g4f"]
            assert_that(spec.provider_class).is_same_as(G4FProvider)
            assert_that(spec.uses_base_url).is_false()
            assert_that(spec.multi_model).is_false()

    def test_canopywave_spec(self):
        """
        Given the canopywave provider specification
        When checking its fields
        Then it has correct configuration
        """
        from src.providers.canopywave import CanopywaveProvider
        spec = PROVIDER_REGISTRY["canopywave"]
        assert_that(spec.provider_class).is_same_as(CanopywaveProvider)
        assert_that(spec.key_name).is_equal_to("canopywave")
        assert_that(spec.uses_base_url).is_true()

    def test_baseten_spec(self):
        """
        Given the baseten provider specification
        When checking its fields
        Then it has correct configuration with strip_json_markers param
        """
        from src.providers.baseten import BasetenProvider
        spec = PROVIDER_REGISTRY["baseten"]
        assert_that(spec.provider_class).is_same_as(BasetenProvider)
        assert_that(spec.key_name).is_equal_to("baseten")
        assert_that(spec.uses_base_url).is_true()
        assert_that(spec.extra_params).contains("strip_json_markers")

    def test_google_genai_spec(self):
        """
        Given the google_genai provider specification
        When checking its fields
        Then it has thinking_level in extra_params
        """
        from src.providers.google_genai import GoogleGenAIProvider
        spec = PROVIDER_REGISTRY["google_genai"]
        assert_that(spec.provider_class).is_same_as(GoogleGenAIProvider)
        assert_that(spec.key_name).is_equal_to("google_genai")
        assert_that(spec.extra_params).contains("thinking_level")

    def test_gemini_webapi_spec(self):
        """
        Given the gemini_webapi provider specification
        When checking its fields
        Then it has no_keys=True and factory set
        """
        spec = PROVIDER_REGISTRY["gemini_webapi"]
        assert_that(spec.no_keys).is_true()
        assert_that(spec.factory).is_not_none()


class TestProviderRegistryValidation:
    """Validation tests for provider registry."""

    def test_all_key_names_are_strings_or_none(self):
        """
        Given the PROVIDER_REGISTRY
        When checking key_name values
        Then all are strings or None
        """
        for name, spec in PROVIDER_REGISTRY.items():
            is_valid = spec.key_name is None or isinstance(spec.key_name, str)
            assert_that(is_valid).is_true()

    def test_all_extra_params_are_lists(self):
        """
        Given the PROVIDER_REGISTRY
        When checking extra_params types
        Then all are lists
        """
        for name, spec in PROVIDER_REGISTRY.items():
            assert_that(spec.extra_params).is_instance_of(list)

    def test_all_extra_params_contain_strings(self):
        """
        Given the PROVIDER_REGISTRY
        When checking extra_params contents
        Then all contain only strings
        """
        for name, spec in PROVIDER_REGISTRY.items():
            for param in spec.extra_params:
                assert_that(param).is_instance_of(str)

    def test_multi_model_providers_have_no_factory(self):
        """
        Given multi_model providers
        When checking for factory
        Then they have no custom factory
        """
        for name, spec in PROVIDER_REGISTRY.items():
            if spec.multi_model:
                assert_that(spec.factory).is_none()

    def test_factory_providers_have_no_multi_model(self):
        """
        Given factory providers
        When checking multi_model flag
        Then it is False
        """
        for name, spec in PROVIDER_REGISTRY.items():
            if spec.factory is not None:
                assert_that(spec.multi_model).is_false()

    def test_no_keys_providers_have_no_key_name(self):
        """
        Given no_keys providers
        When checking key_name
        Then it is None
        """
        for name, spec in PROVIDER_REGISTRY.items():
            if spec.no_keys:
                assert_that(spec.key_name).is_none()


# =============================================================================
# ProviderSpec Tests
# =============================================================================


class TestProviderSpec:
    """Tests for ProviderSpec dataclass."""

    def test_create_provider_spec(self):
        """
        Given provider spec parameters
        When ProviderSpec is created
        Then all fields are set correctly
        """
        spec = ProviderSpec(
            provider_class=MagicMock,
            key_name="test",
            extra_params=["param1", "param2"],
            multi_model=True,
        )

        assert_that(spec.key_name).is_equal_to("test")
        assert_that(spec.extra_params).is_equal_to(["param1", "param2"])
        assert_that(spec.multi_model).is_true()

    def test_default_values(self):
        """
        Given only required provider_class
        When ProviderSpec is created
        Then default values are used
        """
        spec = ProviderSpec(provider_class=MagicMock)

        assert_that(spec.key_name).is_none()
        assert_that(spec.extra_params).is_equal_to([])
        assert_that(spec.multi_model).is_false()
        assert_that(spec.no_keys).is_false()
        assert_that(spec.uses_base_url).is_false()
        assert_that(spec.factory).is_none()

    def test_spec_with_all_params(self):
        """
        Given all parameters
        When ProviderSpec is created
        Then all fields are set correctly
        """
        async def mock_factory(cfg, defs):
            return []

        spec = ProviderSpec(
            provider_class=MagicMock,
            key_name="test_key",
            extra_params=["p1", "p2", "p3"],
            multi_model=True,
            no_keys=True,
            uses_base_url=True,
            factory=mock_factory,
        )

        assert_that(spec.key_name).is_equal_to("test_key")
        assert_that(spec.extra_params).is_length(3)
        assert_that(spec.multi_model).is_true()
        assert_that(spec.no_keys).is_true()
        assert_that(spec.uses_base_url).is_true()
        assert_that(spec.factory).is_same_as(mock_factory)

    def test_spec_is_dataclass(self):
        """
        Given ProviderSpec
        When checking if dataclass
        Then it is a dataclass
        """
        from dataclasses import is_dataclass
        assert_that(is_dataclass(ProviderSpec)).is_true()

    def test_spec_has_expected_fields(self):
        """
        Given ProviderSpec
        When checking its fields
        Then it has all expected fields
        """
        from dataclasses import fields
        field_names = {f.name for f in fields(ProviderSpec)}
        expected = {
            "provider_class",
            "key_name",
            "extra_params",
            "multi_model",
            "no_keys",
            "uses_base_url",
            "factory",
        }
        assert_that(field_names).is_equal_to(expected)


# =============================================================================
# DEFAULT_BASE_URLS Tests
# =============================================================================


class TestDefaultBaseUrls:
    """Tests for DEFAULT_BASE_URLS constant."""

    def test_contains_expected_providers(self):
        """
        Given DEFAULT_BASE_URLS
        When checking for expected providers
        Then all expected providers are present
        """
        assert_that(DEFAULT_BASE_URLS).contains_key("nvidia")
        assert_that(DEFAULT_BASE_URLS).contains_key("openrouter")
        assert_that(DEFAULT_BASE_URLS).contains_key("google_antigravity")
        assert_that(DEFAULT_BASE_URLS).contains_key("baseten")
        assert_that(DEFAULT_BASE_URLS).contains_key("canopywave")

    def test_nvidia_url(self):
        """
        Given DEFAULT_BASE_URLS
        When checking nvidia URL
        Then it is correct
        """
        assert_that(DEFAULT_BASE_URLS["nvidia"]).is_equal_to("https://integrate.api.nvidia.com/v1")

    def test_openrouter_url(self):
        """
        Given DEFAULT_BASE_URLS
        When checking openrouter URL
        Then it is correct
        """
        assert_that(DEFAULT_BASE_URLS["openrouter"]).is_equal_to("https://openrouter.ai/api/v1")

    def test_google_antigravity_url(self):
        """
        Given DEFAULT_BASE_URLS
        When checking google_antigravity URL
        Then it is the local server
        """
        assert_that(DEFAULT_BASE_URLS["google_antigravity"]).is_equal_to("http://127.0.0.1:8317/v1")

    def test_baseten_url(self):
        """
        Given DEFAULT_BASE_URLS
        When checking baseten URL
        Then it is correct
        """
        assert_that(DEFAULT_BASE_URLS["baseten"]).is_equal_to("https://inference.baseten.co/v1")

    def test_canopywave_url(self):
        """
        Given DEFAULT_BASE_URLS
        When checking canopywave URL
        Then it is correct
        """
        assert_that(DEFAULT_BASE_URLS["canopywave"]).is_equal_to("https://api.xiaomimimo.com/v1")

    def test_all_urls_are_strings(self):
        """
        Given DEFAULT_BASE_URLS
        When checking URL types
        Then all are strings
        """
        for name, url in DEFAULT_BASE_URLS.items():
            assert_that(url).is_instance_of(str)

    def test_all_urls_start_with_http(self):
        """
        Given DEFAULT_BASE_URLS
        When checking URL prefixes
        Then all start with http or https
        """
        for name, url in DEFAULT_BASE_URLS.items():
            starts_with_http = url.startswith("http://") or url.startswith("https://")
            assert_that(starts_with_http).is_true()

    def test_all_urls_end_with_v1(self):
        """
        Given DEFAULT_BASE_URLS
        When checking URL suffixes
        Then all end with /v1
        """
        for name, url in DEFAULT_BASE_URLS.items():
            assert_that(url).ends_with("/v1")

    def test_urls_count(self):
        """
        Given DEFAULT_BASE_URLS
        When counting entries
        Then it contains expected number of URLs
        """
        assert_that(DEFAULT_BASE_URLS).is_length(5)


# =============================================================================
# create_provider_instances Tests
# =============================================================================


class TestCreateProviderInstances:
    """Tests for create_provider_instances function."""

    @pytest.fixture
    def defaults(self):
        """Create default configuration."""
        return DefaultsConfig(
            timeout=120.0,
            temperature=0.4,
            max_tokens=None,
            max_retries=5,
            json_parse_retries=5,
        )

    @pytest.mark.asyncio
    async def test_create_single_model_provider(self, defaults):
        """
        Given a single-model provider spec
        When create_provider_instances is called
        Then one instance is created
        """
        MockProvider = MagicMock()
        mock_instance = MagicMock()
        MockProvider.return_value = mock_instance

        spec = ProviderSpec(
            provider_class=MockProvider,
            key_name="test",
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            model="test-model",
            timeout=60.0,
            temperature=0.5,
        )

        with patch("src.providers.registry.load_keys") as mock_load_keys:
            mock_load_keys.return_value = ["key1", "key2"]

            instances = await create_provider_instances("test", spec, cfg, defaults)

            assert_that(instances).is_length(1)
            MockProvider.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_multi_model_provider(self, defaults):
        """
        Given a multi-model provider spec with 3 models
        When create_provider_instances is called
        Then 3 instances are created
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            multi_model=True,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            models=["model1", "model2", "model3"],
        )

        instances = await create_provider_instances("test", spec, cfg, defaults)

        assert_that(instances).is_length(3)
        assert_that(MockProvider.call_count).is_equal_to(3)

    @pytest.mark.asyncio
    async def test_create_multi_model_provider_with_five_models(self, defaults):
        """
        Given a multi-model provider spec with 5 models
        When create_provider_instances is called
        Then 5 instances are created
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            multi_model=True,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            models=["m1", "m2", "m3", "m4", "m5"],
        )

        instances = await create_provider_instances("test", spec, cfg, defaults)

        assert_that(instances).is_length(5)

    @pytest.mark.asyncio
    async def test_create_multi_model_provider_empty_models(self, defaults):
        """
        Given a multi-model provider spec with empty models
        When create_provider_instances is called
        Then empty list is returned
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            multi_model=True,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            models=[],
        )

        instances = await create_provider_instances("test", spec, cfg, defaults)

        assert_that(instances).is_length(0)

    @pytest.mark.asyncio
    async def test_create_provider_no_keys_found(self, defaults):
        """
        Given a provider requiring keys but none found
        When create_provider_instances is called
        Then empty list is returned
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            key_name="missing_provider",
        )

        cfg = ProviderConfig(enabled=True, model="test")

        with patch("src.providers.registry.load_keys") as mock_load_keys:
            mock_load_keys.return_value = []

            instances = await create_provider_instances("test", spec, cfg, defaults)

            assert_that(instances).is_equal_to([])

    @pytest.mark.asyncio
    async def test_create_provider_with_extra_params(self, defaults):
        """
        Given a provider spec with extra_params
        When create_provider_instances is called with those params set
        Then the params are passed to the provider
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            extra_params=["reasoning_effort", "thinking_level"],
        )

        cfg = ProviderConfig(
            enabled=True,
            model="test",
            reasoning_effort="high",
            thinking_level="medium",
        )

        instances = await create_provider_instances("test", spec, cfg, defaults)

        assert_that(instances).is_length(1)
        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs["reasoning_effort"]).is_equal_to("high")
        assert_that(call_kwargs["thinking_level"]).is_equal_to("medium")

    @pytest.mark.asyncio
    async def test_create_provider_extra_params_none_skipped(self, defaults):
        """
        Given extra_params with None values
        When create_provider_instances is called
        Then None values are not passed
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            extra_params=["reasoning_effort", "thinking_level"],
        )

        cfg = ProviderConfig(
            enabled=True,
            model="test",
            reasoning_effort="high",
            # thinking_level is None
        )

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs["reasoning_effort"]).is_equal_to("high")
        assert_that(call_kwargs).does_not_contain_key("thinking_level")

    @pytest.mark.asyncio
    async def test_create_provider_uses_effective_values(self, defaults):
        """
        Given provider config and defaults
        When create_provider_instances is called
        Then effective values are used correctly
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            uses_base_url=True,
        )

        # Provider config without timeout uses default
        cfg = ProviderConfig(
            enabled=True,
            model="test",
            temperature=0.7,  # Custom temperature
        )

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs["temperature"]).is_equal_to(0.7)  # Uses config value
        assert_that(call_kwargs["timeout"]).is_equal_to(120.0)  # Uses default

    @pytest.mark.asyncio
    async def test_create_provider_with_custom_factory(self, defaults):
        """
        Given a spec with custom factory
        When create_provider_instances is called
        Then factory is used to create instances
        """
        async def custom_factory(cfg, defs):
            return [MagicMock(), MagicMock()]

        spec = ProviderSpec(
            provider_class=MagicMock,
            factory=custom_factory,
        )

        cfg = ProviderConfig(enabled=True, model="test")

        instances = await create_provider_instances("test", spec, cfg, defaults)

        assert_that(instances).is_length(2)

    @pytest.mark.asyncio
    async def test_create_provider_factory_receives_config(self, defaults):
        """
        Given a spec with custom factory
        When create_provider_instances is called
        Then factory receives correct config and defaults
        """
        received_cfg = None
        received_defs = None

        async def capturing_factory(cfg, defs):
            nonlocal received_cfg, received_defs
            received_cfg = cfg
            received_defs = defs
            return []

        spec = ProviderSpec(
            provider_class=MagicMock,
            factory=capturing_factory,
        )

        cfg = ProviderConfig(enabled=True, model="test")

        await create_provider_instances("test", spec, cfg, defaults)

        assert_that(received_cfg).is_same_as(cfg)
        assert_that(received_defs).is_same_as(defaults)

    @pytest.mark.asyncio
    async def test_create_provider_base_url_fallback(self, defaults):
        """
        Given no custom base_url
        When create_provider_instances is called
        Then DEFAULT_BASE_URLS fallback is used
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            model="test",
            base_url=None,  # No custom base URL
        )

        with patch.dict("src.providers.registry.DEFAULT_BASE_URLS", {"test": "https://default.url/v1"}):
            instances = await create_provider_instances("test", spec, cfg, defaults)

            call_kwargs = MockProvider.call_args[1]
            assert_that(call_kwargs["base_url"]).is_equal_to("https://default.url/v1")

    @pytest.mark.asyncio
    async def test_create_provider_custom_base_url(self, defaults):
        """
        Given a custom base_url
        When create_provider_instances is called
        Then custom base_url is used
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            model="test",
            base_url="https://custom.url/v1",
        )

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs["base_url"]).is_equal_to("https://custom.url/v1")

    @pytest.mark.asyncio
    async def test_create_provider_with_max_tokens(self, defaults):
        """
        Given max_tokens in config
        When create_provider_instances is called
        Then max_tokens is passed to provider
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            model="test",
            max_tokens=8192,
        )

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs["max_tokens"]).is_equal_to(8192)

    @pytest.mark.asyncio
    async def test_create_provider_max_tokens_none_not_passed(self, defaults):
        """
        Given max_tokens=None
        When create_provider_instances is called
        Then max_tokens is not passed to provider
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            model="test",
            max_tokens=None,
        )

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs).does_not_contain_key("max_tokens")

    @pytest.mark.asyncio
    async def test_create_provider_passes_retry_config(self, defaults):
        """
        Given retry configuration in defaults
        When create_provider_instances is called
        Then retry config is passed to provider
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
        )

        cfg = ProviderConfig(enabled=True, model="test")

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs["max_retries"]).is_equal_to(5)
        assert_that(call_kwargs["json_parse_retries"]).is_equal_to(5)

    @pytest.mark.asyncio
    async def test_create_provider_custom_retries(self):
        """
        Given custom retry values in defaults
        When create_provider_instances is called
        Then custom values are passed
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
        )

        defaults = DefaultsConfig(
            timeout=60.0,
            temperature=0.5,
            max_tokens=None,
            max_retries=3,
            json_parse_retries=2,
        )

        cfg = ProviderConfig(enabled=True, model="test")

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs["max_retries"]).is_equal_to(3)
        assert_that(call_kwargs["json_parse_retries"]).is_equal_to(2)

    @pytest.mark.asyncio
    async def test_create_provider_passes_model(self, defaults):
        """
        Given a model name in config
        When create_provider_instances is called
        Then model is passed to provider
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
        )

        cfg = ProviderConfig(enabled=True, model="custom-model-name")

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs["model"]).is_equal_to("custom-model-name")

    @pytest.mark.asyncio
    async def test_create_provider_with_api_keys(self, defaults):
        """
        Given API keys for a provider
        When create_provider_instances is called
        Then api_keys iterator is passed to provider
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            key_name="test",
        )

        cfg = ProviderConfig(enabled=True, model="test")

        with patch("src.providers.registry.load_keys") as mock_load_keys:
            mock_load_keys.return_value = ["key1", "key2", "key3"]

            instances = await create_provider_instances("test", spec, cfg, defaults)

            call_kwargs = MockProvider.call_args[1]
            assert_that(call_kwargs).contains_key("api_keys")
            # Verify it's a cycling iterator
            keys = call_kwargs["api_keys"]
            assert_that(next(keys)).is_equal_to("key1")
            assert_that(next(keys)).is_equal_to("key2")
            assert_that(next(keys)).is_equal_to("key3")
            assert_that(next(keys)).is_equal_to("key1")  # Cycles back


class TestCreateProviderInstancesMultiModel:
    """Tests specifically for multi-model provider creation."""

    @pytest.fixture
    def defaults(self):
        """Create default configuration."""
        return DefaultsConfig(
            timeout=120.0,
            temperature=0.4,
            max_tokens=4096,
            max_retries=5,
            json_parse_retries=5,
        )

    @pytest.mark.asyncio
    async def test_multi_model_each_gets_correct_model(self, defaults):
        """
        Given a multi-model provider with multiple models
        When create_provider_instances is called
        Then each instance gets the correct model name
        """
        MockProvider = MagicMock()
        models_used = []

        def capture_model(**kwargs):
            models_used.append(kwargs.get("model"))
            return MagicMock()

        MockProvider.side_effect = capture_model

        spec = ProviderSpec(
            provider_class=MockProvider,
            multi_model=True,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            models=["llama-70b", "mistral-large", "claude-opus"],
        )

        await create_provider_instances("test", spec, cfg, defaults)

        assert_that(models_used).is_equal_to(["llama-70b", "mistral-large", "claude-opus"])

    @pytest.mark.asyncio
    async def test_multi_model_uses_same_base_url(self, defaults):
        """
        Given a multi-model provider with custom base_url
        When create_provider_instances is called
        Then all instances get the same base_url
        """
        MockProvider = MagicMock()
        base_urls_used = []

        def capture_base_url(**kwargs):
            base_urls_used.append(kwargs.get("base_url"))
            return MagicMock()

        MockProvider.side_effect = capture_base_url

        spec = ProviderSpec(
            provider_class=MockProvider,
            multi_model=True,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            models=["m1", "m2"],
            base_url="https://custom.url/v1",
        )

        await create_provider_instances("test", spec, cfg, defaults)

        assert_that(all(url == "https://custom.url/v1" for url in base_urls_used)).is_true()

    @pytest.mark.asyncio
    async def test_multi_model_uses_effective_values(self, defaults):
        """
        Given a multi-model provider with custom timeout/temperature
        When create_provider_instances is called
        Then all instances use effective values
        """
        MockProvider = MagicMock()
        captured_params = []

        def capture_params(**kwargs):
            captured_params.append({
                "timeout": kwargs.get("timeout"),
                "temperature": kwargs.get("temperature"),
                "max_tokens": kwargs.get("max_tokens"),
            })
            return MagicMock()

        MockProvider.side_effect = capture_params

        spec = ProviderSpec(
            provider_class=MockProvider,
            multi_model=True,
            no_keys=True,
            uses_base_url=True,
        )

        cfg = ProviderConfig(
            enabled=True,
            models=["m1", "m2"],
            timeout=60.0,
            temperature=0.8,
        )

        await create_provider_instances("test", spec, cfg, defaults)

        for params in captured_params:
            assert_that(params["timeout"]).is_equal_to(60.0)
            assert_that(params["temperature"]).is_equal_to(0.8)
            assert_that(params["max_tokens"]).is_equal_to(4096)  # From defaults


class TestCreateProviderInstancesEdgeCases:
    """Edge case tests for create_provider_instances."""

    @pytest.fixture
    def defaults(self):
        """Create default configuration."""
        return DefaultsConfig(
            timeout=120.0,
            temperature=0.4,
            max_tokens=None,
            max_retries=5,
            json_parse_retries=5,
        )

    @pytest.mark.asyncio
    async def test_provider_without_uses_base_url_no_base_url_passed(self, defaults):
        """
        Given a provider without uses_base_url
        When create_provider_instances is called
        Then base_url is not passed
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            uses_base_url=False,
        )

        cfg = ProviderConfig(
            enabled=True,
            model="test",
            base_url="https://should.not.use/v1",
        )

        await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert_that(call_kwargs).does_not_contain_key("base_url")
        assert_that(call_kwargs).does_not_contain_key("timeout")
        assert_that(call_kwargs).does_not_contain_key("temperature")

    @pytest.mark.asyncio
    async def test_provider_with_single_key(self, defaults):
        """
        Given a provider with single API key
        When create_provider_instances is called
        Then key is cycled correctly
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            key_name="test",
        )

        cfg = ProviderConfig(enabled=True, model="test")

        with patch("src.providers.registry.load_keys") as mock_load_keys:
            mock_load_keys.return_value = ["only_one_key"]

            instances = await create_provider_instances("test", spec, cfg, defaults)

            assert_that(instances).is_length(1)
            call_kwargs = MockProvider.call_args[1]
            keys = call_kwargs["api_keys"]
            assert_that(next(keys)).is_equal_to("only_one_key")
            assert_that(next(keys)).is_equal_to("only_one_key")  # Cycles

    @pytest.mark.asyncio
    async def test_empty_extra_params_list(self, defaults):
        """
        Given empty extra_params list
        When create_provider_instances is called
        Then it succeeds
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            extra_params=[],
        )

        cfg = ProviderConfig(enabled=True, model="test")

        instances = await create_provider_instances("test", spec, cfg, defaults)

        assert_that(instances).is_length(1)

    @pytest.mark.asyncio
    async def test_nonexistent_extra_param_skipped(self, defaults):
        """
        Given nonexistent extra_param in spec
        When create_provider_instances is called
        Then it succeeds without error
        """
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            extra_params=["nonexistent_param"],
        )

        cfg = ProviderConfig(enabled=True, model="test")

        # Should not raise
        instances = await create_provider_instances("test", spec, cfg, defaults)
        assert_that(instances).is_length(1)


# =============================================================================
# Parametrized Tests
# =============================================================================


class TestProviderSpecParametrized:
    """Parametrized tests for provider specifications."""

    @pytest.mark.parametrize("provider_name,expected_key", [
        ("cerebras", "cerebras"),
        ("openrouter", "openrouter"),
        ("nvidia", "nvidia"),
        ("canopywave", "canopywave"),
        ("baseten", "baseten"),
        ("google_genai", "google_genai"),
    ])
    def test_providers_requiring_keys(self, provider_name, expected_key):
        """
        Given providers that require API keys
        When checking their key_name
        Then it matches expected value
        """
        spec = PROVIDER_REGISTRY[provider_name]
        assert_that(spec.key_name).is_equal_to(expected_key)

    @pytest.mark.parametrize("provider_name", [
        "g4f",
        "google_antigravity",
        "gemini_webapi",
    ])
    def test_providers_without_keys(self, provider_name):
        """
        Given providers that don't require API keys
        When checking their no_keys flag
        Then it is True and key_name is None
        """
        spec = PROVIDER_REGISTRY[provider_name]
        assert_that(spec.no_keys).is_true()
        assert_that(spec.key_name).is_none()

    @pytest.mark.parametrize("provider_name", [
        "nvidia",
        "openrouter",
        "canopywave",
        "baseten",
        "google_antigravity",
    ])
    def test_openai_compatible_providers(self, provider_name):
        """
        Given OpenAI-compatible providers
        When checking uses_base_url flag
        Then it is True
        """
        spec = PROVIDER_REGISTRY[provider_name]
        assert_that(spec.uses_base_url).is_true()

    @pytest.mark.parametrize("provider_name", [
        "cerebras",
        "g4f",
        "google_genai",
        "gemini_webapi",
    ])
    def test_non_openai_compatible_providers(self, provider_name):
        """
        Given non-OpenAI-compatible providers
        When checking uses_base_url flag
        Then it is False
        """
        spec = PROVIDER_REGISTRY[provider_name]
        assert_that(spec.uses_base_url).is_false()


class TestDefaultBaseUrlsParametrized:
    """Parametrized tests for default base URLs."""

    @pytest.mark.parametrize("provider,expected_domain", [
        ("nvidia", "nvidia.com"),
        ("openrouter", "openrouter.ai"),
        ("baseten", "baseten.co"),
        ("canopywave", "xiaomimimo.com"),
    ])
    def test_urls_contain_expected_domain(self, provider, expected_domain):
        """
        Given a provider URL
        When checking its domain
        Then it contains expected domain
        """
        url = DEFAULT_BASE_URLS[provider]
        assert_that(url).contains(expected_domain)

    @pytest.mark.parametrize("provider", list(DEFAULT_BASE_URLS.keys()))
    def test_all_urls_valid_format(self, provider):
        """
        Given a provider URL
        When checking its format
        Then it starts with http and contains /v1
        """
        url = DEFAULT_BASE_URLS[provider]
        assert_that(url).starts_with("http")
        assert_that(url).contains("/v1")
