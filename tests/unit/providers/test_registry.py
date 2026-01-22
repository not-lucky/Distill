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

    def test_cerebras_spec(self):
        """Test Cerebras provider specification."""
        spec = PROVIDER_REGISTRY["cerebras"]
        assert spec.key_name == "cerebras"
        assert "reasoning_effort" in spec.extra_params
        assert spec.multi_model is False
        assert spec.no_keys is False

    def test_google_antigravity_spec(self):
        """Test Google Antigravity provider specification."""
        spec = PROVIDER_REGISTRY["google_antigravity"]
        assert spec.no_keys is True
        assert spec.multi_model is True
        assert spec.uses_base_url is True

    def test_g4f_spec(self):
        """Test G4F provider specification."""
        spec = PROVIDER_REGISTRY["g4f"]
        assert spec.no_keys is True
        assert "provider_name" in spec.extra_params


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
