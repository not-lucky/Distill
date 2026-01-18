"""Type definitions for LLM2Deck."""

from typing import List, Optional
from typing_extensions import TypedDict, NotRequired


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
