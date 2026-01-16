from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'llm2deck_cerebras', 'llm2deck_gemini')"""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier (e.g., 'llama3.1-70b', 'gemini-1.5-pro')"""
        pass

    @abstractmethod
    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        """Generates initial cards for a given question."""
        pass

    @abstractmethod
    async def combine_cards(
        self,
        question: str,
        combined_inputs: str,
        json_schema: Dict[str, Any],
        combine_prompt_template: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Combines multiple sets of cards into a single deck."""
        pass
