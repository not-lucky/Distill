"""Prompt loading utilities for LLM2Deck."""

import os
import warnings
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Optional, Tuple


class PromptLoader:
    """
    Lazy-loading prompt loader with caching.

    Prompts are loaded on first access and cached for subsequent use.
    The prompts directory can be configured via LLM2DECK_PROMPTS_DIR environment variable.
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize the PromptLoader.

        Args:
            prompts_dir: Optional custom prompts directory. If not provided,
                         resolves from LLM2DECK_PROMPTS_DIR env var or default location.
        """
        self._prompts_dir = prompts_dir or self._resolve_prompts_dir()

    @staticmethod
    def _resolve_prompts_dir() -> Path:
        """Resolve the prompts directory from environment or default."""
        env_dir = os.getenv("LLM2DECK_PROMPTS_DIR")
        if env_dir:
            return Path(env_dir)
        return Path(__file__).parent / "data" / "prompts"

    @property
    def prompts_dir(self) -> Path:
        """Get the configured prompts directory."""
        return self._prompts_dir

    def _load(self, filename: str) -> str:
        """
        Load a prompt file from the prompts directory.

        Args:
            filename: Name of the prompt file (e.g., "initial.md")

        Returns:
            Contents of the prompt file.

        Raises:
            FileNotFoundError: If prompt file doesn't exist.
        """
        path = self._prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    def _try_load(self, path: Path) -> Optional[str]:
        """Try to load a prompt file, returning None if it doesn't exist."""
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def load_subject_prompts(
        self, subject: str, prompts_dir: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Load initial and combine prompts for a subject.

        For custom subjects, prompts are loaded from a subdirectory:
        - {prompts_dir}/initial.md (or {subject}/initial.md)
        - {prompts_dir}/combine.md (or {subject}/combine.md)

        Args:
            subject: Subject name (e.g., "biology")
            prompts_dir: Optional custom prompts directory path

        Returns:
            Tuple of (initial_prompt, combine_prompt), either can be None
        """
        if prompts_dir:
            subject_dir = Path(prompts_dir)
        else:
            subject_dir = self._prompts_dir / subject

        initial = self._try_load(subject_dir / "initial.md")
        combine = self._try_load(subject_dir / "combine.md")
        return initial, combine

    def load_subject_mcq_prompts(
        self, subject: str, prompts_dir: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Load MCQ prompts for a subject.

        Args:
            subject: Subject name
            prompts_dir: Optional custom prompts directory path

        Returns:
            Tuple of (initial_mcq_prompt, combine_mcq_prompt), either can be None
        """
        if prompts_dir:
            subject_dir = Path(prompts_dir)
        else:
            subject_dir = self._prompts_dir / subject

        initial = self._try_load(subject_dir / "mcq.md")
        combine = self._try_load(subject_dir / "mcq_combine.md")
        return initial, combine

    @cached_property
    def initial(self) -> str:
        """Initial prompt template."""
        return self._load("initial.md")

    @cached_property
    def initial_leetcode(self) -> str:
        """Initial LeetCode-specific prompt template."""
        return self._load("initial_leetcode.md")

    @cached_property
    def initial_cs(self) -> str:
        """Initial CS-specific prompt template."""
        return self._load("initial_cs.md")

    @cached_property
    def combine(self) -> str:
        """Combine prompt template."""
        return self._load("combine.md")

    @cached_property
    def combine_leetcode(self) -> str:
        """Combine LeetCode-specific prompt template."""
        return self._load("combine_leetcode.md")

    @cached_property
    def combine_cs(self) -> str:
        """Combine CS-specific prompt template."""
        return self._load("combine_cs.md")

    @cached_property
    def mcq_combine(self) -> str:
        """MCQ combine prompt template."""
        return self._load("mcq_combine.md")

    @cached_property
    def physics(self) -> str:
        """Physics prompt template."""
        return self._load("physics.md")

    @cached_property
    def mcq(self) -> str:
        """MCQ prompt template."""
        return self._load("mcq.md")

    @cached_property
    def physics_mcq(self) -> str:
        """Physics MCQ prompt template."""
        return self._load("physics_mcq.md")


# Singleton instance for module-level access
prompts = PromptLoader()


# Deprecated module-level constants - use prompts singleton instead
def __getattr__(name: str):
    """Lazy access to deprecated module-level constants with deprecation warnings."""
    _deprecated_constants = {
        "PROMPTS_DIR": ("prompts_dir", prompts.prompts_dir),
        "INITIAL_PROMPT_TEMPLATE": ("initial", prompts.initial),
        "INITIAL_LEETCODE_PROMPT_TEMPLATE": ("initial_leetcode", prompts.initial_leetcode),
        "INITIAL_CS_PROMPT_TEMPLATE": ("initial_cs", prompts.initial_cs),
        "COMBINE_PROMPT_TEMPLATE": ("combine", prompts.combine),
        "COMBINE_LEETCODE_PROMPT_TEMPLATE": ("combine_leetcode", prompts.combine_leetcode),
        "COMBINE_CS_PROMPT_TEMPLATE": ("combine_cs", prompts.combine_cs),
        "MCQ_COMBINE_PROMPT_TEMPLATE": ("mcq_combine", prompts.mcq_combine),
        "PHYSICS_PROMPT_TEMPLATE": ("physics", prompts.physics),
        "MCQ_PROMPT_TEMPLATE": ("mcq", prompts.mcq),
        "PHYSICS_MCQ_PROMPT_TEMPLATE": ("physics_mcq", prompts.physics_mcq),
    }

    if name in _deprecated_constants:
        attr_name, value = _deprecated_constants[name]
        warnings.warn(
            f"{name} is deprecated. Use prompts.{attr_name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def load_prompt(prompt_filename: str) -> str:
    """
    Load prompt template from prompts directory.

    .. deprecated::
        Use prompts._load() or PromptLoader directly instead.

    Args:
        prompt_filename: Name of the prompt file (e.g., "initial.md")

    Returns:
        Contents of the prompt file.

    Raises:
        FileNotFoundError: If prompt file doesn't exist.
    """
    warnings.warn(
        "load_prompt() is deprecated. Use prompts._load() or PromptLoader directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    return prompts._load(prompt_filename)
