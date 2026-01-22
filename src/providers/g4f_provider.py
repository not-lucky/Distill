import json
import re
import asyncio
from typing import Dict, Any, Optional, List
from g4f.client import AsyncClient
from src.providers.base import LLMProvider
from src.prompts import prompts
import logging

logger = logging.getLogger(__name__)


class G4FProvider(LLMProvider):
    def __init__(
        self,
        model: str = "",
        provider_name: Optional[str] = "LMArena",
        max_retries: int = 3,
        json_parse_retries: int = 3,
    ):
        self.model_name = model
        self.provider_name = provider_name
        self.max_retries = max_retries
        self.json_parse_retries = json_parse_retries
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
    ) -> Optional[str]:
        for attempt_number in range(self.max_retries):
            try:
                api_response = await self.async_client.chat.completions.create(
                    model=self.model_name,
                    messages=chat_messages,
                )

                response_content = api_response.choices[0].message.content
                if not response_content:
                    logger.warning(
                        f"[G4F:{self.model_name}] Attempt {attempt_number + 1}/{self.max_retries}: Received None content. Retrying..."
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
                    f"[G4F:{self.model_name}] Attempt {attempt_number + 1}/{self.max_retries} Error: {error}"
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
            prompt_template if prompt_template else prompts.initial
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
    ) -> Optional[str]:
        """Combine cards and return raw response string."""
        active_template = (
            combine_prompt_template
            if combine_prompt_template
            else prompts.combine
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

        return await self._make_request(chat_messages, json_schema)

    async def format_json(
        self,
        raw_content: str,
        json_schema: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Format raw content into valid JSON matching the schema."""
        chat_messages = [
            {
                "role": "system",
                "content": (
                    "You are a JSON formatting assistant. Your task is to extract and format "
                    "the content into valid JSON matching the provided schema. "
                    "Output ONLY valid JSON, nothing else. No markdown, no explanations."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Format the following content into valid JSON matching this schema:\n\n"
                    f"Schema:\n{json.dumps(json_schema, indent=2, ensure_ascii=False)}\n\n"
                    f"Content to format:\n{raw_content}"
                ),
            },
        ]

        for attempt in range(self.json_parse_retries):
            response_content = await self._make_request(chat_messages, json_schema)
            if response_content:
                try:
                    return json.loads(response_content)
                except json.JSONDecodeError as error:
                    logger.warning(
                        f"[G4F:{self.model_name}] format_json attempt {attempt + 1}/{self.json_parse_retries}: "
                        f"JSON Decode Error: {error}. Retrying..."
                    )
                    continue

        logger.error(f"[G4F:{self.model_name}] format_json failed after {self.json_parse_retries} attempts.")
        return None
