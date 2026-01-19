import json
import re
import asyncio
from typing import Dict, Any, Optional, List
from g4f.client import AsyncClient
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE
import logging

logger = logging.getLogger(__name__)


class G4FProvider(LLMProvider):
    def __init__(
        self,
        model: str = "",
        provider: Optional[str] = "LMArena",
    ):
        self.model_name = model
        self.provider_name = provider
        self.async_client = AsyncClient(provider=self.provider_name)

    @property
    def name(self) -> str:
        return "llm2deck_g4f"

    @property
    def model(self) -> str:
        return self.model_name

    async def _make_request(
        self,
        chat_messages: List[Dict[str, Any]],
        json_schema: Dict[str, Any],
        max_retries: int = 3,
    ) -> Optional[str]:
        for attempt_number in range(max_retries):
            try:
                api_response = await self.async_client.chat.completions.create(
                    model=self.model_name,
                    messages=chat_messages,
                )

                response_content = api_response.choices[0].message.content
                if not response_content:
                    logger.warning(
                        f"[G4F:{self.model_name}] Attempt {attempt_number + 1}/{max_retries}: Received None content. Retrying..."
                    )
                    continue

                # Try to extract JSON if it's wrapped in markdown
                json_code_block_match = re.search(
                    r"```json\s*(.*?)\s*```", response_content, re.DOTALL
                )
                if json_code_block_match:
                    response_content = json_code_block_match.group(1)
                elif "```" in response_content:
                    # Fallback for code block without language specifier
                    generic_code_block_match = re.search(
                        r"```\s*(.*?)\s*```", response_content, re.DOTALL
                    )
                    if generic_code_block_match:
                        response_content = generic_code_block_match.group(1)

                return response_content

            except Exception as error:
                logger.error(
                    f"[G4F:{self.model_name}] Attempt {attempt_number + 1}/{max_retries} Error: {error}"
                )

            await asyncio.sleep(1)

        return None

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        # logger.info(f"[G4F:{self.model_name}] Generating initial cards for '{question}'...")

        active_template = (
            prompt_template if prompt_template else INITIAL_PROMPT_TEMPLATE
        )

        chat_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates Anki cards in JSON format. Return ONLY the JSON object, no other text.",
            },
            {
                "role": "user",
                "content": active_template.format(
                    question=question,
                    schema=json.dumps(json_schema, indent=2, ensure_ascii=False),
                ),
            },
        ]

        response_content = await self._make_request(chat_messages, json_schema)
        return response_content if response_content else ""

    async def combine_cards(
        self,
        question: str,
        combined_inputs: str,
        json_schema: Dict[str, Any],
        combine_prompt_template: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        # logger.info(f"[G4F:{self.model_name}] Combining cards for '{question}'...")
        active_template = (
            combine_prompt_template
            if combine_prompt_template
            else COMBINE_PROMPT_TEMPLATE
        )
        chat_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates Anki cards in JSON format. Return ONLY the JSON object, no other text.",
            },
            {
                "role": "user",
                "content": active_template.format(
                    question=question, inputs=combined_inputs
                ),
            },
        ]

        for attempt_number in range(3):
            response_content = await self._make_request(chat_messages, json_schema)
            if response_content:
                try:
                    return json.loads(response_content)
                except json.JSONDecodeError as decode_error:
                    logger.warning(
                        f"[G4F:{self.model_name}] Attempt {attempt_number + 1}/3: JSON Decode Error: {decode_error}. Content preview: {response_content[:100]}... Retrying..."
                    )
                    continue

        logger.error(f"[G4F:{self.model_name}] Failed to decode JSON after 3 attempts.")
        return None
