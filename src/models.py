from typing import List
from pydantic import BaseModel, Field

class AnkiCard(BaseModel):
    model_config = {'extra': 'forbid'}
    card_type: str = Field(..., description="Type of the card (e.g., 'Concept', 'Code', 'Intuition'). Use PascalCase.")
    tags: List[str] = Field(..., description="Tags for the card. Use PascalCase.")
    front: str = Field(..., description="Front side of the card (Markdown supported)")
    back: str = Field(..., description="Back side of the card (Markdown supported)")

class LeetCodeProblem(BaseModel):
    model_config = {'extra': 'forbid'}
    title: str = Field(..., description="Title of the LeetCode problem")
    topic: str = Field(..., description="Main topic (e.g., 'Arrays', 'Linked Lists')")
    difficulty: str = Field(..., description="Difficulty level (Easy, Medium, Hard)")
    cards: List[AnkiCard]

class CSProblem(BaseModel):
    model_config = {'extra': 'forbid'}
    title: str = Field(..., description="Title of the CS Concept")
    topic: str = Field(..., description="Main topic (e.g., 'Operating Systems', 'Networking')")
    difficulty: str = Field(..., description="Difficulty level (Basic, Intermediate, Advanced)")
    cards: List[AnkiCard]
