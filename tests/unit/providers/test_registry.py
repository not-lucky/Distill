"""Tests for providers/registry.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import itertools

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
        """Test that registry contains expected providers."""
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
            assert provider in PROVIDER_REGISTRY, f"Missing provider: {provider}"

    def test_registry_values_are_provider_specs(self):
        """Test that all registry values are ProviderSpec instances."""
        for name, spec in PROVIDER_REGISTRY.items():
            assert isinstance(spec, ProviderSpec), f"{name} is not a ProviderSpec"

    def test_registry_provider_classes_are_callable(self):
        """Test that all provider classes in registry are callable."""
        for name, spec in PROVIDER_REGISTRY.items():
            assert callable(spec.provider_class), f"{name} provider_class is not callable"

    def test_registry_count(self):
        """Test registry contains expected number of providers."""
        assert len(PROVIDER_REGISTRY) == 9

    def test_cerebras_spec(self):
        """Test Cerebras provider specification."""
        spec = PROVIDER_REGISTRY["cerebras"]
        assert spec.key_name == "cerebras"
        assert "reasoning_effort" in spec.extra_params
        assert spec.multi_model is False
        assert spec.no_keys is False

    def test_cerebras_spec_details(self):
        """Test Cerebras spec has correct provider class."""
        from src.providers.cerebras import CerebrasProvider
        spec = PROVIDER_REGISTRY["cerebras"]
        assert spec.provider_class is CerebrasProvider
        assert spec.uses_base_url is False
        assert spec.factory is None

    def test_openrouter_spec(self):
        """Test OpenRouter provider specification."""
        from src.providers.openrouter import OpenRouterProvider
        spec = PROVIDER_REGISTRY["openrouter"]
        assert spec.provider_class is OpenRouterProvider
        assert spec.key_name == "openrouter"
        assert spec.uses_base_url is True
        assert spec.multi_model is False

    def test_nvidia_spec(self):
        """Test NVIDIA provider specification."""
        from src.providers.nvidia import NvidiaProvider
        spec = PROVIDER_REGISTRY["nvidia"]
        assert spec.provider_class is NvidiaProvider
        assert spec.key_name == "nvidia"
        assert spec.uses_base_url is True
        assert "top_p" in spec.extra_params
        assert "extra_params" in spec.extra_params

    def test_google_antigravity_spec(self):
        """Test Google Antigravity provider specification."""
        spec = PROVIDER_REGISTRY["google_antigravity"]
        assert spec.no_keys is True
        assert spec.multi_model is True
        assert spec.uses_base_url is True

    def test_google_antigravity_spec_details(self):
        """Test Google Antigravity spec has correct provider class."""
        from src.providers.google_antigravity import GoogleAntigravityProvider
        spec = PROVIDER_REGISTRY["google_antigravity"]
        assert spec.provider_class is GoogleAntigravityProvider
        assert spec.key_name is None
        assert spec.factory is None

    def test_g4f_spec(self):
        """Test G4F provider specification."""
        spec = PROVIDER_REGISTRY["g4f"]
        assert spec.no_keys is True
        assert "provider_name" in spec.extra_params

    def test_g4f_spec_details(self):
        """Test G4F spec details."""
        with patch("src.providers.g4f_provider.AsyncClient"):
            from src.providers.g4f_provider import G4FProvider
            spec = PROVIDER_REGISTRY["g4f"]
            assert spec.provider_class is G4FProvider
            assert spec.uses_base_url is False
            assert spec.multi_model is False

    def test_canopywave_spec(self):
        """Test Canopywave provider specification."""
        from src.providers.canopywave import CanopywaveProvider
        spec = PROVIDER_REGISTRY["canopywave"]
        assert spec.provider_class is CanopywaveProvider
        assert spec.key_name == "canopywave"
        assert spec.uses_base_url is True

    def test_baseten_spec(self):
        """Test Baseten provider specification."""
        from src.providers.baseten import BasetenProvider
        spec = PROVIDER_REGISTRY["baseten"]
        assert spec.provider_class is BasetenProvider
        assert spec.key_name == "baseten"
        assert spec.uses_base_url is True
        assert "strip_json_markers" in spec.extra_params

    def test_google_genai_spec(self):
        """Test Google GenAI provider specification."""
        from src.providers.google_genai import GoogleGenAIProvider
        spec = PROVIDER_REGISTRY["google_genai"]
        assert spec.provider_class is GoogleGenAIProvider
        assert spec.key_name == "google_genai"
        assert "thinking_level" in spec.extra_params

    def test_gemini_webapi_spec(self):
        """Test Gemini WebAPI provider specification."""
        spec = PROVIDER_REGISTRY["gemini_webapi"]
        assert spec.no_keys is True
        assert spec.factory is not None


class TestProviderRegistryValidation:
    """Validation tests for provider registry."""

    def test_all_key_names_are_strings_or_none(self):
        """Test that all key_name values are strings or None."""
        for name, spec in PROVIDER_REGISTRY.items():
            assert spec.key_name is None or isinstance(spec.key_name, str), \
                f"{name} key_name is not string or None"

    def test_all_extra_params_are_lists(self):
        """Test that all extra_params are lists."""
        for name, spec in PROVIDER_REGISTRY.items():
            assert isinstance(spec.extra_params, list), \
                f"{name} extra_params is not a list"

    def test_all_extra_params_contain_strings(self):
        """Test that all extra_params contain only strings."""
        for name, spec in PROVIDER_REGISTRY.items():
            for param in spec.extra_params:
                assert isinstance(param, str), \
                    f"{name} has non-string param: {param}"

    def test_multi_model_providers_have_no_factory(self):
        """Test that multi_model providers don't have custom factories."""
        for name, spec in PROVIDER_REGISTRY.items():
            if spec.multi_model:
                assert spec.factory is None, \
                    f"{name} is multi_model but has factory"

    def test_factory_providers_have_no_multi_model(self):
        """Test that factory providers aren't multi_model."""
        for name, spec in PROVIDER_REGISTRY.items():
            if spec.factory is not None:
                assert not spec.multi_model, \
                    f"{name} has factory but is multi_model"

    def test_no_keys_providers_have_no_key_name(self):
        """Test that no_keys providers don't specify key_name."""
        for name, spec in PROVIDER_REGISTRY.items():
            if spec.no_keys:
                assert spec.key_name is None, \
                    f"{name} is no_keys but has key_name"


# =============================================================================
# ProviderSpec Tests
# =============================================================================


class TestProviderSpec:
    """Tests for ProviderSpec dataclass."""

    def test_create_provider_spec(self):
        """Test creating a ProviderSpec."""
        spec = ProviderSpec(
            provider_class=MagicMock,
            key_name="test",
            extra_params=["param1", "param2"],
            multi_model=True,
        )

        assert spec.key_name == "test"
        assert spec.extra_params == ["param1", "param2"]
        assert spec.multi_model is True

    def test_default_values(self):
        """Test ProviderSpec default values."""
        spec = ProviderSpec(provider_class=MagicMock)

        assert spec.key_name is None
        assert spec.extra_params == []
        assert spec.multi_model is False
        assert spec.no_keys is False
        assert spec.uses_base_url is False
        assert spec.factory is None

    def test_spec_with_all_params(self):
        """Test creating spec with all parameters."""
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

        assert spec.key_name == "test_key"
        assert len(spec.extra_params) == 3
        assert spec.multi_model is True
        assert spec.no_keys is True
        assert spec.uses_base_url is True
        assert spec.factory is mock_factory

    def test_spec_is_dataclass(self):
        """Test that ProviderSpec is a dataclass."""
        from dataclasses import is_dataclass
        assert is_dataclass(ProviderSpec)

    def test_spec_has_expected_fields(self):
        """Test that ProviderSpec has expected fields."""
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
        assert field_names == expected


# =============================================================================
# DEFAULT_BASE_URLS Tests
# =============================================================================


class TestDefaultBaseUrls:
    """Tests for DEFAULT_BASE_URLS constant."""

    def test_contains_expected_providers(self):
        """Test that DEFAULT_BASE_URLS contains expected providers."""
        assert "nvidia" in DEFAULT_BASE_URLS
        assert "openrouter" in DEFAULT_BASE_URLS
        assert "google_antigravity" in DEFAULT_BASE_URLS
        assert "baseten" in DEFAULT_BASE_URLS
        assert "canopywave" in DEFAULT_BASE_URLS

    def test_nvidia_url(self):
        """Test Nvidia default URL."""
        assert DEFAULT_BASE_URLS["nvidia"] == "https://integrate.api.nvidia.com/v1"

    def test_openrouter_url(self):
        """Test OpenRouter default URL."""
        assert DEFAULT_BASE_URLS["openrouter"] == "https://openrouter.ai/api/v1"

    def test_google_antigravity_url(self):
        """Test Google Antigravity default URL (local server)."""
        assert DEFAULT_BASE_URLS["google_antigravity"] == "http://127.0.0.1:8317/v1"

    def test_baseten_url(self):
        """Test Baseten default URL."""
        assert DEFAULT_BASE_URLS["baseten"] == "https://inference.baseten.co/v1"

    def test_canopywave_url(self):
        """Test Canopywave default URL."""
        assert DEFAULT_BASE_URLS["canopywave"] == "https://api.xiaomimimo.com/v1"

    def test_all_urls_are_strings(self):
        """Test all URLs are strings."""
        for name, url in DEFAULT_BASE_URLS.items():
            assert isinstance(url, str), f"{name} URL is not a string"

    def test_all_urls_start_with_http(self):
        """Test all URLs start with http or https."""
        for name, url in DEFAULT_BASE_URLS.items():
            assert url.startswith("http://") or url.startswith("https://"), \
                f"{name} URL doesn't start with http(s)"

    def test_all_urls_end_with_v1(self):
        """Test all URLs end with /v1."""
        for name, url in DEFAULT_BASE_URLS.items():
            assert url.endswith("/v1"), f"{name} URL doesn't end with /v1"

    def test_urls_count(self):
        """Test expected number of default URLs."""
        assert len(DEFAULT_BASE_URLS) == 5


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
        """Test creating a single-model provider."""
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

            assert len(instances) == 1
            MockProvider.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_multi_model_provider(self, defaults):
        """Test creating a multi-model provider."""
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

        assert len(instances) == 3
        assert MockProvider.call_count == 3

    @pytest.mark.asyncio
    async def test_create_multi_model_provider_with_five_models(self, defaults):
        """Test creating multi-model provider with five models."""
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

        assert len(instances) == 5

    @pytest.mark.asyncio
    async def test_create_multi_model_provider_empty_models(self, defaults):
        """Test creating multi-model provider with no models."""
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

        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_create_provider_no_keys_found(self, defaults):
        """Test creating provider when no keys found returns empty list."""
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            key_name="missing_provider",
        )

        cfg = ProviderConfig(enabled=True, model="test")

        with patch("src.providers.registry.load_keys") as mock_load_keys:
            mock_load_keys.return_value = []

            instances = await create_provider_instances("test", spec, cfg, defaults)

            assert instances == []

    @pytest.mark.asyncio
    async def test_create_provider_with_extra_params(self, defaults):
        """Test creating provider with extra parameters."""
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

        assert len(instances) == 1
        call_kwargs = MockProvider.call_args[1]
        assert call_kwargs["reasoning_effort"] == "high"
        assert call_kwargs["thinking_level"] == "medium"

    @pytest.mark.asyncio
    async def test_create_provider_extra_params_none_skipped(self, defaults):
        """Test that None extra params are not passed."""
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
        assert call_kwargs["reasoning_effort"] == "high"
        assert "thinking_level" not in call_kwargs

    @pytest.mark.asyncio
    async def test_create_provider_uses_effective_values(self, defaults):
        """Test that effective values from config/defaults are used."""
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
        assert call_kwargs["temperature"] == 0.7  # Uses config value
        assert call_kwargs["timeout"] == 120.0  # Uses default

    @pytest.mark.asyncio
    async def test_create_provider_with_custom_factory(self, defaults):
        """Test creating provider with custom factory function."""
        async def custom_factory(cfg, defs):
            return [MagicMock(), MagicMock()]

        spec = ProviderSpec(
            provider_class=MagicMock,
            factory=custom_factory,
        )

        cfg = ProviderConfig(enabled=True, model="test")

        instances = await create_provider_instances("test", spec, cfg, defaults)

        assert len(instances) == 2

    @pytest.mark.asyncio
    async def test_create_provider_factory_receives_config(self, defaults):
        """Test that factory receives correct config."""
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

        assert received_cfg is cfg
        assert received_defs is defaults

    @pytest.mark.asyncio
    async def test_create_provider_base_url_fallback(self, defaults):
        """Test that base_url falls back to DEFAULT_BASE_URLS."""
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
            assert call_kwargs["base_url"] == "https://default.url/v1"

    @pytest.mark.asyncio
    async def test_create_provider_custom_base_url(self, defaults):
        """Test that custom base_url overrides default."""
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
        assert call_kwargs["base_url"] == "https://custom.url/v1"

    @pytest.mark.asyncio
    async def test_create_provider_with_max_tokens(self, defaults):
        """Test creating provider with max_tokens."""
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
        assert call_kwargs["max_tokens"] == 8192

    @pytest.mark.asyncio
    async def test_create_provider_max_tokens_none_not_passed(self, defaults):
        """Test that max_tokens=None is not passed to provider."""
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
        assert "max_tokens" not in call_kwargs

    @pytest.mark.asyncio
    async def test_create_provider_passes_retry_config(self, defaults):
        """Test that retry configuration is passed to provider."""
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
        )

        cfg = ProviderConfig(enabled=True, model="test")

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert call_kwargs["max_retries"] == 5
        assert call_kwargs["json_parse_retries"] == 5

    @pytest.mark.asyncio
    async def test_create_provider_custom_retries(self):
        """Test custom retry values are passed."""
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
        assert call_kwargs["max_retries"] == 3
        assert call_kwargs["json_parse_retries"] == 2

    @pytest.mark.asyncio
    async def test_create_provider_passes_model(self, defaults):
        """Test that model is passed to provider."""
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
        )

        cfg = ProviderConfig(enabled=True, model="custom-model-name")

        instances = await create_provider_instances("test", spec, cfg, defaults)

        call_kwargs = MockProvider.call_args[1]
        assert call_kwargs["model"] == "custom-model-name"

    @pytest.mark.asyncio
    async def test_create_provider_with_api_keys(self, defaults):
        """Test that api_keys are passed as iterator."""
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
            assert "api_keys" in call_kwargs
            # Verify it's a cycling iterator
            keys = call_kwargs["api_keys"]
            assert next(keys) == "key1"
            assert next(keys) == "key2"
            assert next(keys) == "key3"
            assert next(keys) == "key1"  # Cycles back


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
        """Test that each instance gets correct model name."""
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

        assert models_used == ["llama-70b", "mistral-large", "claude-opus"]

    @pytest.mark.asyncio
    async def test_multi_model_uses_same_base_url(self, defaults):
        """Test all instances get same base_url."""
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

        assert all(url == "https://custom.url/v1" for url in base_urls_used)

    @pytest.mark.asyncio
    async def test_multi_model_uses_effective_values(self, defaults):
        """Test multi-model uses effective timeout/temperature."""
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
            assert params["timeout"] == 60.0
            assert params["temperature"] == 0.8
            assert params["max_tokens"] == 4096  # From defaults


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
        """Test provider without uses_base_url doesn't get base_url."""
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
        assert "base_url" not in call_kwargs
        assert "timeout" not in call_kwargs
        assert "temperature" not in call_kwargs

    @pytest.mark.asyncio
    async def test_provider_with_single_key(self, defaults):
        """Test provider works with single API key."""
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            key_name="test",
        )

        cfg = ProviderConfig(enabled=True, model="test")

        with patch("src.providers.registry.load_keys") as mock_load_keys:
            mock_load_keys.return_value = ["only_one_key"]

            instances = await create_provider_instances("test", spec, cfg, defaults)

            assert len(instances) == 1
            call_kwargs = MockProvider.call_args[1]
            keys = call_kwargs["api_keys"]
            assert next(keys) == "only_one_key"
            assert next(keys) == "only_one_key"  # Cycles

    @pytest.mark.asyncio
    async def test_empty_extra_params_list(self, defaults):
        """Test provider with empty extra_params list."""
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            extra_params=[],
        )

        cfg = ProviderConfig(enabled=True, model="test")

        instances = await create_provider_instances("test", spec, cfg, defaults)

        assert len(instances) == 1

    @pytest.mark.asyncio
    async def test_nonexistent_extra_param_skipped(self, defaults):
        """Test nonexistent extra param doesn't cause error."""
        MockProvider = MagicMock()

        spec = ProviderSpec(
            provider_class=MockProvider,
            no_keys=True,
            extra_params=["nonexistent_param"],
        )

        cfg = ProviderConfig(enabled=True, model="test")

        # Should not raise
        instances = await create_provider_instances("test", spec, cfg, defaults)
        assert len(instances) == 1


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
        """Test providers that require API keys have correct key_name."""
        spec = PROVIDER_REGISTRY[provider_name]
        assert spec.key_name == expected_key

    @pytest.mark.parametrize("provider_name", [
        "g4f",
        "google_antigravity",
        "gemini_webapi",
    ])
    def test_providers_without_keys(self, provider_name):
        """Test providers that don't require API keys."""
        spec = PROVIDER_REGISTRY[provider_name]
        assert spec.no_keys is True
        assert spec.key_name is None

    @pytest.mark.parametrize("provider_name", [
        "nvidia",
        "openrouter",
        "canopywave",
        "baseten",
        "google_antigravity",
    ])
    def test_openai_compatible_providers(self, provider_name):
        """Test OpenAI-compatible providers use base_url."""
        spec = PROVIDER_REGISTRY[provider_name]
        assert spec.uses_base_url is True

    @pytest.mark.parametrize("provider_name", [
        "cerebras",
        "g4f",
        "google_genai",
        "gemini_webapi",
    ])
    def test_non_openai_compatible_providers(self, provider_name):
        """Test non-OpenAI-compatible providers don't use base_url."""
        spec = PROVIDER_REGISTRY[provider_name]
        assert spec.uses_base_url is False


class TestDefaultBaseUrlsParametrized:
    """Parametrized tests for default base URLs."""

    @pytest.mark.parametrize("provider,expected_domain", [
        ("nvidia", "nvidia.com"),
        ("openrouter", "openrouter.ai"),
        ("baseten", "baseten.co"),
        ("canopywave", "xiaomimimo.com"),
    ])
    def test_urls_contain_expected_domain(self, provider, expected_domain):
        """Test URLs contain expected domain."""
        url = DEFAULT_BASE_URLS[provider]
        assert expected_domain in url

    @pytest.mark.parametrize("provider", list(DEFAULT_BASE_URLS.keys()))
    def test_all_urls_valid_format(self, provider):
        """Test all URLs have valid format."""
        url = DEFAULT_BASE_URLS[provider]
        assert url.startswith("http")
        assert "/v1" in url
