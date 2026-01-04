from dataclasses import dataclass
from typing import List, Type, Optional, Any
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
    INITIAL_PROMPT_TEMPLATE
)
from src.questions import (
    QUESTIONS, 
    CS_QUESTIONS, 
    PHYSICS_QUESTIONS
)

@dataclass
class SubjectConfig:
    """Configuration for a specific subject/mode."""
    target_questions: List[str]
    prompt_template: Optional[str]
    target_model: Type[BaseModel]
    
class SubjectRegistry:
    @staticmethod
    def get_config(subject: str, is_mcq: bool = False) -> SubjectConfig:
        """
        Get configuration for a given subject and card type.
        
        Args:
            subject: 'leetcode', 'cs', or 'physics'
            is_mcq: Whether to generate MCQ cards
        """
        # Default fallback
        if subject not in ["cs", "physics", "leetcode"]:
            subject = "leetcode"

        # 1. Select Questions
        if subject == "cs":
            questions = CS_QUESTIONS
        elif subject == "physics":
            questions = PHYSICS_QUESTIONS
        else:
            questions = QUESTIONS

        # 2. Select Model & Prompt
        if is_mcq:
            model = MCQProblem
            if subject == "physics":
                prompt = PHYSICS_MCQ_PROMPT_TEMPLATE
            else:
                prompt = MCQ_PROMPT_TEMPLATE
        else:
            if subject == "cs":
                model = CSProblem
                prompt = GENIUS_PERSONA_PROMPT_TEMPLATE
            elif subject == "physics":
                model = PhysicsProblem
                prompt = PHYSICS_PROMPT_TEMPLATE
            else: # leetcode
                model = LeetCodeProblem
                prompt = None # Usage of generic/initial prompt implied or handled by Logic

        return SubjectConfig(
            target_questions=questions,
            prompt_template=prompt,
            target_model=model
        )
