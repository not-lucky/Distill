from typing import List
from pydantic import BaseModel, Field


class AnkiCard(BaseModel):
    model_config = {'extra': 'forbid'}
    card_type: str = Field(..., description="Type of the card (e.g., 'Concept', 'Code', 'Intuition'). Use PascalCase.")
    tags: List[str] = Field(..., description="Tags for the card. Use PascalCase.")
    front: str = Field(..., description="Front side of the card (Markdown supported)")
    back: str = Field(..., description="Back side of the card (Markdown supported)")


class BaseProblem(BaseModel):
    """Base class for all problem types with common fields."""
    model_config = {'extra': 'forbid'}
    title: str = Field(..., description="Title of the topic/concept")
    topic: str = Field(..., description="Main topic or category")
    difficulty: str = Field(..., description="Difficulty level")
    cards: List[AnkiCard]


class LeetCodeProblem(BaseProblem):
    """Problem model for LeetCode algorithm questions."""
    title: str = Field(..., description="Title of the LeetCode problem")
    topic: str = Field(..., description="Main topic (e.g., 'Arrays', 'Linked Lists')")
    difficulty: str = Field(..., description="Difficulty level (Easy, Medium, Hard)")


class CSProblem(BaseProblem):
    """Problem model for Computer Science concepts."""
    title: str = Field(..., description="Title of the CS Concept")
    topic: str = Field(..., description="Main topic (e.g., 'Operating Systems', 'Networking')")
    difficulty: str = Field(..., description="Difficulty level (Basic, Intermediate, Advanced)")


class PhysicsProblem(BaseProblem):
    """Problem model for Physics concepts."""
    title: str = Field(..., description="Title of the Physics Concept")
    topic: str = Field(..., description="Main topic (e.g., 'Mechanics', 'Thermodynamics')")
    difficulty: str = Field(..., description="Difficulty level (Basic, Intermediate, Advanced)")

class MCQCard(BaseModel):
    model_config = {'extra': 'forbid'}
    card_type: str = Field(..., description="Type of the card (e.g., 'Concept', 'Application', 'Tricky'). Use PascalCase.")
    tags: List[str] = Field(..., description="Tags for the card. Use PascalCase.")
    question: str = Field(..., description="The question stem (Markdown supported)")
    options: List[str] = Field(..., description="Exactly 4 answer options labeled A, B, C, D")
    correct_answer: str = Field(..., description="The correct answer (A, B, C, or D)")
    explanation: str = Field(..., description="Explanation of why the correct answer is right (Markdown supported)")

class MCQProblem(BaseModel):
    model_config = {'extra': 'forbid'}
    title: str = Field(..., description="Title of the topic/concept")
    topic: str = Field(..., description="Main topic (e.g., 'Data Structures', 'Algorithms')")
    difficulty: str = Field(..., description="Difficulty level (Easy, Medium, Hard)")
    cards: List[MCQCard]


class GenericProblem(BaseProblem):
    """Generic problem model for user-defined custom subjects."""
    pass
