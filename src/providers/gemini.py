import json
from typing import Dict, Any, Optional
from gemini_webapi import GeminiClient
from gemini_webapi.constants import Model
from src.providers.base import LLMProvider
from src.prompts import prompts
import logging

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    @property
    def name(self) -> str:
        return "llm2deck_gemini"

    @property
    def model(self) -> str:
        return "gemini-3.0-pro"

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        # logger.info(f"[Gemini] Generating initial cards for '{question}'...")
        try:
            active_template = (
                prompt_template if prompt_template else prompts.initial
            )
            formatted_prompt = active_template.format(
                question=question,
                schema=json.dumps(json_schema, indent=2, ensure_ascii=False),
            )
            api_response = await self.gemini_client.generate_content(
                formatted_prompt, model=Model.G_3_0_PRO
            )
            return api_response.text
        except Exception as error:
            logger.error(f"[Gemini] Error: {error}")
            return ""

    async def combine_cards(
        self,
        question: str,
        combined_inputs: str,
        json_schema: Dict[str, Any],
        combine_prompt_template: Optional[str] = None,
    ) -> Optional[str]:
        # Gemini webapi might not be best for strict JSON schema enforcement in the same way as OpenAI
        # But we can try prompting it.
        # The original code didn't use Gemini for combination.
        logger.warning(
            "[Gemini] Combination not implemented/recommended for this provider."
        )
        return None
