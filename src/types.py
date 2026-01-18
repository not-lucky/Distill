"""Type definitions for LLM2Deck."""

from typing import Any, Dict, List, Optional, Union
from typing_extensions import TypedDict, NotRequired

from pydantic import BaseModel, field_validator


class CardData(TypedDict):
    """Structure for a single Anki card."""

    front: str
    back: str
    card_type: NotRequired[str]
    tags: NotRequired[List[str]]


class MCQCardData(TypedDict):
    """Structure for a multiple choice card."""

    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    card_type: NotRequired[str]
    tags: NotRequired[List[str]]


class CardResult(TypedDict):
    """Result from processing a question."""

    cards: List[CardData]
    category_index: NotRequired[int]
    category_name: NotRequired[str]
    problem_index: NotRequired[int]


class ProviderResultData(TypedDict):
    """Data for a provider's generation result."""

    provider_name: str
    provider_model: str
    raw_output: str
    card_count: NotRequired[int]
    success: bool


# Pydantic models for validation


class CardModel(BaseModel):
    """Pydantic model for validating a single card."""

    front: Optional[str] = None
    back: Optional[str] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    card_type: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("tags", mode="before")
    @classmethod
    def ensure_tags_list(cls, v: Any) -> Optional[List[str]]:
        """Ensure tags is a list of strings."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        return v


class ProviderResponse(BaseModel):
    """
    Pydantic model for validating raw LLM provider responses.

    Use this to validate JSON responses before saving to database.
    """

    cards: List[Dict[str, Any]]

    @field_validator("cards")
    @classmethod
    def validate_cards_not_empty(cls, v: List) -> List:
        """Ensure cards list is not empty."""
        if not v:
            raise ValueError("Cards list cannot be empty")
        return v

    @field_validator("cards")
    @classmethod
    def validate_cards_have_content(cls, v: List) -> List:
        """Ensure each card has either front/back or question/explanation."""
        for i, card in enumerate(v):
            has_standard = "front" in card and "back" in card
            has_mcq = "question" in card and "explanation" in card
            if not (has_standard or has_mcq):
                raise ValueError(
                    f"Card {i} must have either front/back or question/explanation"
                )
        return v
