"""Configuration file loader for LLM2Deck."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from src.exceptions import ConfigurationError


CONFIG_FILE = Path("config.yaml")


class DefaultsConfig(BaseModel):
    """Global default settings for all providers."""

    timeout: float = 120.0
    temperature: float = 0.4
    max_tokens: Optional[int] = None
    max_retries: int = 5
    json_parse_retries: int = 5
    retry_delay: float = 1.0
    retry_min_wait: float = 1.0
    retry_max_wait: float = 10.0


class KeyPathsConfig(BaseModel):
    """Configuration for API key file paths."""

    cerebras: str = "api_keys.json"
    openrouter: str = "openrouter_apikeys.json"
    gemini: str = "python3ds.json"
    nvidia: str = "nvidia_keys.json"
    canopywave: str = "canopywave_keys.json"
    baseten: str = "baseten_keys.json"
    google_genai: str = "google_genai_keys.json"


class PathsConfig(BaseModel):
    """Configuration for file paths."""

    archival_dir: str = "anki_cards_archival"
    markdown_dir: str = "anki_cards_markdown"
    timestamp_format: str = "%Y%m%dT%H%M%S"
    key_paths: KeyPathsConfig = Field(default_factory=KeyPathsConfig)


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    enabled: bool = False
    model: str = ""
    models: List[str] = Field(default_factory=list)  # For providers with multiple models
    base_url: Optional[str] = None  # Optional base URL override
    timeout: Optional[float] = None  # None means use defaults
    temperature: Optional[float] = None  # None means use defaults
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    strip_json_markers: Optional[bool] = None
    extra_params: Optional[Dict[str, Any]] = None  # Provider-specific parameters
    reasoning_effort: Optional[str] = None
    thinking_level: Optional[str] = None
    provider_name: Optional[str] = None  # For G4F

    def get_effective_timeout(self, defaults: "DefaultsConfig") -> float:
        """Get timeout, falling back to defaults if not set."""
        return self.timeout if self.timeout is not None else defaults.timeout

    def get_effective_temperature(self, defaults: "DefaultsConfig") -> float:
        """Get temperature, falling back to defaults if not set."""
        return self.temperature if self.temperature is not None else defaults.temperature

    def get_effective_max_tokens(self, defaults: "DefaultsConfig") -> Optional[int]:
        """Get max_tokens, falling back to defaults if not set."""
        return self.max_tokens if self.max_tokens is not None else defaults.max_tokens


class CombinerConfig(BaseModel):
    """Configuration for the combiner provider."""

    provider: str = ""  # Provider name (e.g., "cerebras", "google_antigravity")
    model: str = ""  # Model to use for combining
    also_generate: bool = True  # If True, combiner also does initial generation


class FormatterConfig(BaseModel):
    """Configuration for the JSON formatter provider."""

    provider: str = ""  # Provider name (e.g., "cerebras", "openrouter")
    model: str = ""  # Model to use for formatting
    also_generate: bool = True  # If True, formatter also does initial generation


class GenerationConfig(BaseModel):
    """Configuration for card generation."""

    concurrent_requests: int = 8
    request_delay: float = 0.0  # Delay in seconds between starting each request within a batch
    max_retries: int = 5
    json_parse_retries: int = 3
    combiner: Optional[CombinerConfig] = None  # Explicit combiner configuration
    formatter: Optional[FormatterConfig] = None  # JSON formatter configuration


class DatabaseConfig(BaseModel):
    """Configuration for database."""

    path: str = "llm2deck.db"


class SubjectSettings(BaseModel):
    """Configuration settings for a subject (built-in or custom) from config.yaml."""

    enabled: bool = True
    deck_prefix: Optional[str] = None
    deck_prefix_mcq: Optional[str] = None
    prompts_dir: Optional[str] = None
    questions_file: Optional[str] = None

    def is_custom(self) -> bool:
        """Check if this is a custom subject (has prompts_dir or questions_file)."""
        return self.prompts_dir is not None or self.questions_file is not None


class AppConfig(BaseModel):
    """Top-level application configuration."""

    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    subjects: Dict[str, SubjectSettings] = Field(default_factory=dict)

    @classmethod
    def default(cls) -> "AppConfig":
        """Return default configuration when no config file exists."""
        return cls(
            providers={
                "cerebras": ProviderConfig(
                    enabled=True,
                    model="gpt-oss-120b",
                    reasoning_effort="high",
                ),
                "google_antigravity": ProviderConfig(
                    enabled=True,
                    models=["gemini-3-pro-preview", "gemini-claude-sonnet-4-5-thinking"],
                ),
            },
            subjects={
                "leetcode": SubjectSettings(enabled=True),
                "cs": SubjectSettings(enabled=True),
                "physics": SubjectSettings(enabled=True),
            },
        )


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """
    Load configuration from config.yaml.

    Args:
        config_path: Optional path to config file. Defaults to CONFIG_FILE.

    Returns:
        AppConfig with parsed configuration.

    Raises:
        ConfigurationError: If config file exists but cannot be parsed.
    """
    path = config_path or CONFIG_FILE

    if not path.exists():
        return AppConfig.default()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Failed to parse {path}: {e}")

    try:
        return AppConfig.model_validate(data)
    except Exception as e:
        raise ConfigurationError(f"Configuration validation failed: {e}")


def get_enabled_providers(config: Optional[AppConfig] = None) -> Dict[str, ProviderConfig]:
    """
    Get only enabled providers from configuration.

    Args:
        config: Optional AppConfig. Will load from file if not provided.

    Returns:
        Dict of provider name to ProviderConfig for enabled providers only.
    """
    if config is None:
        config = load_config()

    return {name: cfg for name, cfg in config.providers.items() if cfg.enabled}


def get_combiner_config(config: Optional[AppConfig] = None) -> Optional[CombinerConfig]:
    """
    Get the combiner configuration.

    Args:
        config: Optional AppConfig. Will load from file if not provided.

    Returns:
        CombinerConfig if configured, None otherwise.

    Raises:
        ConfigurationError: If combiner references a disabled or non-existent provider.
    """
    if config is None:
        config = load_config()

    combiner = config.generation.combiner
    if combiner is None or not combiner.provider:
        return None

    # Validate the combiner provider exists and is enabled
    provider_cfg = config.providers.get(combiner.provider)
    if provider_cfg is None:
        raise ConfigurationError(
            f"Combiner references unknown provider: '{combiner.provider}'"
        )
    if not provider_cfg.enabled:
        raise ConfigurationError(
            f"Combiner provider '{combiner.provider}' is not enabled"
        )

    # Validate model exists for multi-model providers
    if provider_cfg.models and combiner.model not in provider_cfg.models:
        raise ConfigurationError(
            f"Combiner model '{combiner.model}' not found in provider '{combiner.provider}' models: {provider_cfg.models}"
        )

    return combiner


def get_formatter_config(config: Optional[AppConfig] = None) -> Optional[FormatterConfig]:
    """
    Get the formatter configuration.

    Args:
        config: Optional AppConfig. Will load from file if not provided.

    Returns:
        FormatterConfig if configured, None otherwise.

    Raises:
        ConfigurationError: If formatter references a disabled or non-existent provider.
    """
    if config is None:
        config = load_config()

    formatter = config.generation.formatter
    if formatter is None or not formatter.provider:
        return None

    # Validate the formatter provider exists and is enabled
    provider_cfg = config.providers.get(formatter.provider)
    if provider_cfg is None:
        raise ConfigurationError(
            f"Formatter references unknown provider: '{formatter.provider}'"
        )
    if not provider_cfg.enabled:
        raise ConfigurationError(
            f"Formatter provider '{formatter.provider}' is not enabled"
        )

    # Validate model exists for multi-model providers
    if provider_cfg.models and formatter.model not in provider_cfg.models:
        raise ConfigurationError(
            f"Formatter model '{formatter.model}' not found in provider '{formatter.provider}' models: {provider_cfg.models}"
        )

    return formatter


def get_enabled_subjects(config: Optional[AppConfig] = None) -> Dict[str, SubjectSettings]:
    """
    Get only enabled subjects from configuration.

    Args:
        config: Optional AppConfig. Will load from file if not provided.

    Returns:
        Dict of subject name to SubjectSettings for enabled subjects only.
    """
    if config is None:
        config = load_config()

    return {name: cfg for name, cfg in config.subjects.items() if cfg.enabled}


# Allow overriding config path via environment variable
if os.getenv("LLM2DECK_CONFIG"):
    CONFIG_FILE = Path(os.environ["LLM2DECK_CONFIG"])
