from dataclasses import dataclass
from typing import List, Type, Optional, Any, Dict, Union
from pydantic import BaseModel

from src.models import (
    CSProblem, 
    LeetCodeProblem, 
    PhysicsProblem, 
    MCQProblem
)
from src.prompts import (
    GENIUS_PERSONA_PROMPT_TEMPLATE,
    PHYSICS_PROMPT_TEMPLATE, 
    MCQ_PROMPT_TEMPLATE,
    PHYSICS_MCQ_PROMPT_TEMPLATE,
    INITIAL_PROMPT_TEMPLATE,
    INITIAL_LEETCODE_PROMPT_TEMPLATE,
    COMBINE_LEETCODE_PROMPT_TEMPLATE
)
from src.questions import (
    QUESTIONS, 
    CS_QUESTIONS, 
    PHYSICS_QUESTIONS
)

# Type aliases
CategorizedQuestions = Dict[str, List[str]]
FlatQuestions = List[str]

@dataclass
class SubjectConfig:
    """Configuration for a specific subject/mode."""
    target_questions: Union[CategorizedQuestions, FlatQuestions]
    prompt_template: Optional[str]
    target_model: Type[BaseModel]
    is_categorized: bool = False  # True if questions are in category dict format
    
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

        # 1. Select Questions
        is_categorized_format = False
        if subject_name == "cs":
            question_list = CS_QUESTIONS
        elif subject_name == "physics":
            question_list = PHYSICS_QUESTIONS
        else:
            question_list = QUESTIONS
            is_categorized_format = isinstance(question_list, dict)  # leetcode uses categorized format

        # 2. Select Model & Prompt
        if is_multiple_choice:
            target_model_class = MCQProblem
            if subject_name == "physics":
                prompt_template = PHYSICS_MCQ_PROMPT_TEMPLATE
            else:
                prompt_template = MCQ_PROMPT_TEMPLATE
        else:
            if subject_name == "cs":
                target_model_class = CSProblem
                prompt_template = GENIUS_PERSONA_PROMPT_TEMPLATE
            elif subject_name == "physics":
                target_model_class = PhysicsProblem
                prompt_template = PHYSICS_PROMPT_TEMPLATE
            else: # leetcode
                target_model_class = LeetCodeProblem
                prompt_template = None # Usage of generic/initial prompt implied or handled by Logic

        return SubjectConfig(
            target_questions=question_list,
            prompt_template=prompt_template,
            target_model=target_model_class,
            is_categorized=is_categorized_format
        )
