import json
import re
import asyncio
import itertools
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE
import logging

logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_keys: List[str], model: str):
        self.api_key_cycle = itertools.cycle(api_keys)
        self.model_name = model
        self.api_base_url = "https://openrouter.ai/api/v1"

    @property
    def name(self) -> str:
        return "llm2deck_openrouter"

    @property
    def model(self) -> str:
        return self.model_name

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=next(self.api_key_cycle),
            base_url=self.api_base_url,
            # default_headers={
            #     "HTTP-Referer": "https://github.com/not-lucky/LLM2Deck", # Optional, for OpenRouter rankings
            #     "X-Title": "LLM2Deck", # Optional
            # }
        )

    async def _make_request(
        self,
        chat_messages: List[Dict[str, Any]],
        json_schema: Dict[str, Any],
        max_retries: int = 3,
    ) -> Optional[str]:
        for attempt_number in range(max_retries):
            try:
                api_client = self._get_client()
                api_completion = await api_client.chat.completions.create(
                    model=self.model_name,
                    messages=chat_messages,
                    temperature=0.4,
                )

                response_content = api_completion.choices[0].message.content

                logger.warning(
                    f"[{self.model_name}] Attempt {attempt_number + 1}/{max_retries}: Received None content. Retrying..."
                )

            except Exception as error:
                logger.error(
                    f"[{self.model_name}] Attempt {attempt_number + 1}/{max_retries} Error: {error}"
                )

            await asyncio.sleep(1)

        return None

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        # logger.info(f"[{self.model_name}] Generating initial cards for '{question}'...")

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
        # logger.info(f"[{self.model_name}] Combining cards for '{question}'...")
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
