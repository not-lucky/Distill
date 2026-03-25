"""Subject configuration and registry for LLM2Deck."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Type

from pydantic import BaseModel

from src.config.loader import SubjectSettings, load_config
from src.models import (
    CSProblem,
    GenericProblem,
    LeetCodeProblem,
    MCQProblem,
    PhysicsProblem,
)
from src.prompts import prompts
from src.questions import CS_QUESTIONS, PHYSICS_QUESTIONS, QUESTIONS

# Type alias
CategorizedQuestions = Dict[str, List[str]]

# Built-in subject names
BUILTIN_SUBJECTS = {"leetcode", "cs", "physics"}


@dataclass
class SubjectConfig:
    """Configuration for a specific subject/mode."""

    name: str  # "leetcode", "cs", "physics", or custom subject name
    target_questions: CategorizedQuestions
    initial_prompt: Optional[str]  # Prompt template for initial generation
    combine_prompt: Optional[str]  # Prompt template for combining cards
    target_model: Type[BaseModel]
    deck_prefix: str  # Anki deck prefix, e.g., "LeetCode", "CS"
    deck_prefix_mcq: str  # MCQ variant prefix, e.g., "LeetCode_MCQ"


class SubjectRegistry:
    """Registry for subject configurations, supporting both built-in and custom subjects."""

    def __init__(self):
        """Initialize the registry."""
        self._config = load_config()

    def get_available_subjects(self) -> List[str]:
        """Get list of all available (enabled) subject names."""
        return [
            name
            for name, cfg in self._config.subjects.items()
            if cfg.enabled
        ]

    def is_valid_subject(self, subject_name: str) -> bool:
        """Check if a subject name is valid and enabled."""
        if subject_name in self._config.subjects:
            return self._config.subjects[subject_name].enabled
        # Allow built-in subjects even if not in config
        return subject_name in BUILTIN_SUBJECTS

    def get_config(
        self, subject_name: str, is_multiple_choice: bool = False
    ) -> SubjectConfig:
        """
        Get configuration for a given subject and card type.

        Args:
            subject_name: Subject name (built-in or custom)
            is_multiple_choice: Whether to generate MCQ cards

        Returns:
            SubjectConfig for the requested subject/mode

        Raises:
            ValueError: If subject is not found or not enabled
        """
        # Get settings from config (or use defaults for built-in)
        settings = self._config.subjects.get(subject_name)

        if subject_name in BUILTIN_SUBJECTS:
            return self._get_builtin_config(subject_name, is_multiple_choice, settings)
        elif settings and settings.is_custom():
            return self._get_custom_config(subject_name, is_multiple_choice, settings)
        else:
            raise ValueError(
                f"Unknown subject '{subject_name}'. "
                f"Available subjects: {', '.join(self.get_available_subjects())}"
            )

    def _get_builtin_config(
        self,
        subject_name: str,
        is_multiple_choice: bool,
        settings: Optional[SubjectSettings],
    ) -> SubjectConfig:
        """Get configuration for a built-in subject."""
        # Question lists
        questions_map = {
            "cs": CS_QUESTIONS,
            "physics": PHYSICS_QUESTIONS,
            "leetcode": QUESTIONS,
        }
        question_list = questions_map[subject_name]

        # Deck prefixes (from settings or defaults)
        default_prefixes = {
            "cs": ("CS", "CS_MCQ"),
            "physics": ("Physics", "Physics_MCQ"),
            "leetcode": ("LeetCode", "LeetCode_MCQ"),
        }
        default_prefix, default_prefix_mcq = default_prefixes[subject_name]

        if settings:
            prefix = settings.deck_prefix or default_prefix
            prefix_mcq = settings.deck_prefix_mcq or default_prefix_mcq
        else:
            prefix, prefix_mcq = default_prefix, default_prefix_mcq

        # Select Model & Prompts based on mode
        if is_multiple_choice:
            target_model_class = MCQProblem
            if subject_name == "physics":
                initial_prompt = prompts.physics_mcq
            else:
                initial_prompt = prompts.mcq
            combine_prompt = prompts.mcq_combine
        else:
            # Standard mode - subject-specific configuration
            config_map = {
                "cs": (CSProblem, prompts.initial_cs, prompts.combine_cs),
                "physics": (PhysicsProblem, prompts.physics, None),
                "leetcode": (LeetCodeProblem, None, prompts.combine_leetcode),
            }
            target_model_class, initial_prompt, combine_prompt = config_map[subject_name]

        return SubjectConfig(
            name=subject_name,
            target_questions=question_list,
            initial_prompt=initial_prompt,
            combine_prompt=combine_prompt,
            target_model=target_model_class,
            deck_prefix=prefix,
            deck_prefix_mcq=prefix_mcq,
        )

    def _get_custom_config(
        self,
        subject_name: str,
        is_multiple_choice: bool,
        settings: SubjectSettings,
    ) -> SubjectConfig:
        """Get configuration for a custom subject."""
        # Load questions from file
        questions: CategorizedQuestions = {}
        if settings.questions_file:
            questions = self._load_questions_file(settings.questions_file)

        # Deck prefixes
        prefix = settings.deck_prefix or subject_name.title()
        prefix_mcq = settings.deck_prefix_mcq or f"{prefix}_MCQ"

        # Load prompts
        if is_multiple_choice:
            target_model_class = MCQProblem
            initial_prompt, combine_prompt = prompts.load_subject_mcq_prompts(
                subject_name, settings.prompts_dir
            )
        else:
            target_model_class = GenericProblem
            initial_prompt, combine_prompt = prompts.load_subject_prompts(
                subject_name, settings.prompts_dir
            )

        return SubjectConfig(
            name=subject_name,
            target_questions=questions,
            initial_prompt=initial_prompt,
            combine_prompt=combine_prompt,
            target_model=target_model_class,
            deck_prefix=prefix,
            deck_prefix_mcq=prefix_mcq,
        )

    def _load_questions_file(self, filepath: str) -> CategorizedQuestions:
        """Load questions from a JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Questions file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Support both flat list and categorized format
        if isinstance(data, list):
            return {"General": data}
        elif isinstance(data, dict):
            return data
        else:
            raise ValueError(f"Invalid questions format in {path}")


# Backwards-compatible static method interface
def get_subject_config(
    subject_name: str, is_multiple_choice: bool = False
) -> SubjectConfig:
    """
    Get configuration for a given subject and card type.

    This is a convenience function that creates a registry and gets the config.
    For repeated access, prefer creating a SubjectRegistry instance.
    """
    registry = SubjectRegistry()
    return registry.get_config(subject_name, is_multiple_choice)
