from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMProvider(ABC):
    @abstractmethod
    async def generate_initial_cards(self, question: str, schema: Dict[str, Any]) -> str:
        """Generates initial cards for a given question."""
        pass

    @abstractmethod
    async def combine_cards(self, question: str, inputs: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Combines multiple sets of cards into a single deck."""
        pass
