import json
import asyncio
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI, RateLimitError, APITimeoutError
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE
import logging

logger = logging.getLogger(__name__)


class GoogleAntigravityProvider(LLMProvider):
    """LLM Provider for Google's OpenAI-compatible API (Gemini models)."""

    def __init__(self, model: str):
        self.model_name = model
        self.api_base_url = "http://127.0.0.1:8317/v1"

    @property
    def name(self) -> str:
        return "llm2deck_google_antigravity"

    @property
    def model(self) -> str:
        return self.model_name

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI( 
            api_key="", base_url=self.api_base_url, timeout=900.0
        )

    async def _make_request(
        self,
        chat_messages: List[Dict[str, Any]],
        json_schema: Dict[str, Any],
        max_retries: int = 5,
    ) -> Optional[str]:
        for attempt_number in range(max_retries):
            try:
                api_client = self._get_client()

                api_completion = await api_client.chat.completions.create(
                    model=self.model_name,
                    messages=chat_messages,
                    temperature=0.4,
                    max_tokens=16384,
                )

                response_content = api_completion.choices[0].message.content
                if response_content:
                    if json_schema:
                        response_content = (
                            response_content.lstrip("```json").rstrip("```").strip()
                        )
                    return response_content

                logger.warning(
                    f"[{self.model_name}] Attempt {attempt_number + 1}/{max_retries}: Received None content. Retrying..."
                )

            except Exception as error:
                logger.error(
                    f"[{self.model_name}] Attempt {attempt_number + 1}/{max_retries} Error: {error}"
                )
                if isinstance(error, RateLimitError):
                    logger.warning(
                        f"[{self.model_name}] Rate limit hit. Backing off..."
                    )
                    await asyncio.sleep(2 * (attempt_number + 1))
                    continue
                if isinstance(error, APITimeoutError):
                    logger.warning(f"[{self.model_name}] Request timed out.")

            await asyncio.sleep(1)

        return None

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        active_template = (
            prompt_template if prompt_template else INITIAL_PROMPT_TEMPLATE
        )

        chat_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates Anki cards in JSON format.",
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
        active_template = (
            combine_prompt_template
            if combine_prompt_template
            else COMBINE_PROMPT_TEMPLATE
        )
        chat_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates Anki cards in JSON format.",
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
                        f"[{self.model_name}] Attempt {attempt_number + 1}/3: JSON Decode Error: {decode_error}. Retrying..."
                    )
                    continue

        logger.error(f"[{self.model_name}] Failed to decode JSON after 3 attempts.")
        return None
