"""Prompt loading utilities for LLM2Deck."""

import os
from functools import cached_property
from pathlib import Path
from typing import Optional


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

# Backwards-compatible module-level constants
# These are evaluated lazily via the cached_property mechanism
PROMPTS_DIR = prompts.prompts_dir
INITIAL_PROMPT_TEMPLATE = prompts.initial
INITIAL_LEETCODE_PROMPT_TEMPLATE = prompts.initial_leetcode
INITIAL_CS_PROMPT_TEMPLATE = prompts.initial_cs
COMBINE_PROMPT_TEMPLATE = prompts.combine
COMBINE_LEETCODE_PROMPT_TEMPLATE = prompts.combine_leetcode
COMBINE_CS_PROMPT_TEMPLATE = prompts.combine_cs
MCQ_COMBINE_PROMPT_TEMPLATE = prompts.mcq_combine
PHYSICS_PROMPT_TEMPLATE = prompts.physics
MCQ_PROMPT_TEMPLATE = prompts.mcq
PHYSICS_MCQ_PROMPT_TEMPLATE = prompts.physics_mcq


def load_prompt(prompt_filename: str) -> str:
    """
    Load prompt template from prompts directory.

    This function is kept for backwards compatibility.
    Prefer using the PromptLoader class or module-level constants.

    Args:
        prompt_filename: Name of the prompt file (e.g., "initial.md")

    Returns:
        Contents of the prompt file.

    Raises:
        FileNotFoundError: If prompt file doesn't exist.
    """
    return prompts._load(prompt_filename)
