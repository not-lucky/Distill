import json
from typing import Dict, Any, Optional
from gemini_webapi import GeminiClient
from gemini_webapi.constants import Model
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE

class GeminiProvider(LLMProvider):
    def __init__(self, client: GeminiClient):
        self.client = client

    async def generate_initial_cards(self, question: str, schema: Dict[str, Any], prompt_template: Optional[str] = None) -> str:
        print(f"  [Gemini] Generating initial cards for '{question}'...")
        try:
            template = prompt_template if prompt_template else INITIAL_PROMPT_TEMPLATE
            prompt = template.format(
                question=question,
                schema=json.dumps(schema, indent=2)
            )
            response = await self.client.generate_content(prompt, model=Model.G_3_0_PRO)
            return response.text
        except Exception as e:
            print(f"  [Gemini] Error: {e}")
            return ""

    async def combine_cards(self, question: str, inputs: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Gemini webapi might not be best for strict JSON schema enforcement in the same way as OpenAI
        # But we can try prompting it.
        # For now, let's assume we rely on OpenAI/Cerebras for the combination step as per original logic,
        # or implement a best-effort approach here.
        # The original code didn't use Gemini for combination.
        print("  [Gemini] Combination not implemented/recommended for this provider.")
        return None
