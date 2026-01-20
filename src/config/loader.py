"""Configuration file loader for LLM2Deck."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.exceptions import ConfigurationError


CONFIG_FILE = Path("config.yaml")


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""

    enabled: bool = False
    model: str = ""
    models: List[str] = field(default_factory=list)  # For providers with multiple models
    timeout: float = 120.0
    reasoning_effort: Optional[str] = None
    thinking_level: Optional[str] = None
    provider_name: Optional[str] = None  # For G4F


@dataclass
class GenerationConfig:
    """Configuration for card generation."""

    concurrent_requests: int = 8
    max_retries: int = 5
    json_parse_retries: int = 3


@dataclass
class DatabaseConfig:
    """Configuration for database."""

    path: str = "llm2deck.db"


@dataclass
class SubjectSettings:
    """Configuration settings for a subject (built-in or custom) from config.yaml."""

    enabled: bool = True
    deck_prefix: Optional[str] = None
    deck_prefix_mcq: Optional[str] = None
    prompts_dir: Optional[str] = None
    questions_file: Optional[str] = None

    def is_custom(self) -> bool:
        """Check if this is a custom subject (has prompts_dir or questions_file)."""
        return self.prompts_dir is not None or self.questions_file is not None


@dataclass
class AppConfig:
    """Top-level application configuration."""

    providers: Dict[str, ProviderConfig]
    generation: GenerationConfig
    database: DatabaseConfig
    subjects: Dict[str, SubjectSettings] = field(default_factory=dict)

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
            generation=GenerationConfig(),
            database=DatabaseConfig(),
            subjects={
                "leetcode": SubjectSettings(enabled=True),
                "cs": SubjectSettings(enabled=True),
                "physics": SubjectSettings(enabled=True),
            },
        )


def _parse_provider_config(name: str, data: Dict[str, Any]) -> ProviderConfig:
    """Parse provider configuration from YAML data."""
    return ProviderConfig(
        enabled=data.get("enabled", False),
        model=data.get("model", ""),
        models=data.get("models", []),
        timeout=data.get("timeout", 120.0),
        reasoning_effort=data.get("reasoning_effort"),
        thinking_level=data.get("thinking_level"),
        provider_name=data.get("provider_name"),
    )


def _parse_generation_config(data: Dict[str, Any]) -> GenerationConfig:
    """Parse generation configuration from YAML data."""
    return GenerationConfig(
        concurrent_requests=data.get("concurrent_requests", 8),
        max_retries=data.get("max_retries", 5),
        json_parse_retries=data.get("json_parse_retries", 3),
    )


def _parse_database_config(data: Dict[str, Any]) -> DatabaseConfig:
    """Parse database configuration from YAML data."""
    return DatabaseConfig(
        path=data.get("path", "llm2deck.db"),
    )


def _parse_subject_config(name: str, data: Dict[str, Any]) -> SubjectSettings:
    """Parse subject configuration from YAML data."""
    return SubjectSettings(
        enabled=data.get("enabled", True),
        deck_prefix=data.get("deck_prefix"),
        deck_prefix_mcq=data.get("deck_prefix_mcq"),
        prompts_dir=data.get("prompts_dir"),
        questions_file=data.get("questions_file"),
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

    # Parse providers
    providers: Dict[str, ProviderConfig] = {}
    providers_data = data.get("providers", {})
    for provider_name, provider_data in providers_data.items():
        if isinstance(provider_data, dict):
            providers[provider_name] = _parse_provider_config(provider_name, provider_data)

    # Parse generation config
    generation_data = data.get("generation", {})
    generation = _parse_generation_config(generation_data)

    # Parse database config
    database_data = data.get("database", {})
    database = _parse_database_config(database_data)

    # Parse subjects config
    subjects: Dict[str, SubjectConfig] = {}
    subjects_data = data.get("subjects", {})
    for subject_name, subject_data in subjects_data.items():
        if isinstance(subject_data, dict):
            subjects[subject_name] = _parse_subject_config(subject_name, subject_data)

    return AppConfig(
        providers=providers,
        generation=generation,
        database=database,
        subjects=subjects,
    )


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
