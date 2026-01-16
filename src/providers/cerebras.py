import json
import asyncio
import itertools
from typing import Dict, Any, Optional, List
from cerebras.cloud.sdk import Cerebras
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE
import logging

logger = logging.getLogger(__name__)


class CerebrasProvider(LLMProvider):
    def __init__(self, api_keys: Any, model: str, reasoning_effort: str = "high"):
        self.api_key_iterator = api_keys
        self.model_name = model
        self.reasoning_effort_level = reasoning_effort

    @property
    def name(self) -> str:
        return "llm2deck_cerebras"

    @property
    def model(self) -> str:
        return self.model_name

    def _get_client(self) -> Cerebras:
        current_api_key = next(self.api_key_iterator)
        # logger.debug(f"Using key: ...{current_api_key[-4:]}")
        return Cerebras(api_key=current_api_key)

    async def _make_request(
        self,
        chat_messages: List[Dict[str, Any]],
        json_schema: Dict[str, Any],
        max_retries: int = 7,
    ) -> Optional[str]:
        for attempt_number in range(max_retries):
            try:
                api_client = self._get_client()
                optional_parameters = {}
                if self.model_name == "gpt-oss-120b":
                    optional_parameters["reasoning_effort"] = (
                        self.reasoning_effort_level
                    )

                api_completion = await asyncio.to_thread(
                    api_client.chat.completions.create,
                    model=self.model_name,
                    messages=chat_messages,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "leetcode_problem_schema",
                            "strict": True,
                            "schema": json_schema,
                        },
                    },
                    temperature=0.4,
                    **optional_parameters,
                )

                response_content = api_completion.choices[0].message.content
                if response_content:
                    return response_content

                logger.warning(
                    f"[{self.model_name}] Attempt {attempt_number + 1}/{max_retries}: Received None content. Retrying..."
                )

            except Exception as error:
                logger.error(
                    f"[{self.model_name}] Attempt {attempt_number + 1}/{max_retries} Error: {error}"
                )

            # Optional: Add a small delay between retries if needed
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

        for attempt_number in range(7):
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
