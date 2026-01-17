from dataclasses import dataclass
from typing import List, Type, Optional, Dict
from pydantic import BaseModel

from src.models import (
    CSProblem, 
    LeetCodeProblem, 
    PhysicsProblem, 
    MCQProblem
)
from src.prompts import (
    INITIAL_CS_PROMPT_TEMPLATE,
    PHYSICS_PROMPT_TEMPLATE,
    MCQ_PROMPT_TEMPLATE,
    PHYSICS_MCQ_PROMPT_TEMPLATE,
    COMBINE_LEETCODE_PROMPT_TEMPLATE,
    COMBINE_CS_PROMPT_TEMPLATE,
    MCQ_COMBINE_PROMPT_TEMPLATE,
)
from src.questions import (
    QUESTIONS, 
    CS_QUESTIONS, 
    PHYSICS_QUESTIONS
)

# Type alias
CategorizedQuestions = Dict[str, List[str]]

@dataclass
class SubjectConfig:
    """Configuration for a specific subject/mode."""
    name: str  # "leetcode", "cs", "physics"
    target_questions: CategorizedQuestions
    initial_prompt: Optional[str]  # Prompt template for initial generation
    combine_prompt: Optional[str]  # Prompt template for combining cards
    target_model: Type[BaseModel]
    deck_prefix: str  # Anki deck prefix, e.g., "LeetCode", "CS"
    deck_prefix_mcq: str  # MCQ variant prefix, e.g., "LeetCode_MCQ"
    
class SubjectRegistry:
    @staticmethod
    def get_config(subject_name: str, is_multiple_choice: bool = False) -> SubjectConfig:
        """
        Get configuration for a given subject and card type.

        Args:
            subject_name: 'leetcode', 'cs', or 'physics'
            is_multiple_choice: Whether to generate MCQ cards
        """
        # Default fallback
        if subject_name not in ["cs", "physics", "leetcode"]:
            subject_name = "leetcode"

        # Question lists (all subjects use categorized format)
        questions_map = {
            "cs": CS_QUESTIONS,
            "physics": PHYSICS_QUESTIONS,
            "leetcode": QUESTIONS,
        }
        question_list = questions_map[subject_name]

        # Deck prefixes
        deck_prefixes = {
            "cs": ("CS", "CS_MCQ"),
            "physics": ("Physics", "Physics_MCQ"),
            "leetcode": ("LeetCode", "LeetCode_MCQ"),
        }
        prefix, prefix_mcq = deck_prefixes[subject_name]

        # Select Model & Prompts based on mode
        if is_multiple_choice:
            target_model_class = MCQProblem
            if subject_name == "physics":
                initial_prompt = PHYSICS_MCQ_PROMPT_TEMPLATE
            else:
                initial_prompt = MCQ_PROMPT_TEMPLATE
            combine_prompt = MCQ_COMBINE_PROMPT_TEMPLATE
        else:
            # Standard mode - subject-specific configuration
            config_map = {
                "cs": (CSProblem, INITIAL_CS_PROMPT_TEMPLATE, COMBINE_CS_PROMPT_TEMPLATE),
                "physics": (PhysicsProblem, PHYSICS_PROMPT_TEMPLATE, None),
                "leetcode": (LeetCodeProblem, None, COMBINE_LEETCODE_PROMPT_TEMPLATE),
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
