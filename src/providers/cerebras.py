"""Cerebras LLM Provider using native Cerebras SDK."""

import json
import asyncio
from typing import Any, Dict, Iterator, List, Optional

from cerebras.cloud.sdk import Cerebras
from tenacity import RetryError

from src.providers.base import (
    LLMProvider,
    create_retry_decorator,
    RetryableError,
    EmptyResponseError,
)
from src.prompts import prompts
from src.config.models import supports_reasoning_effort
import logging

logger = logging.getLogger(__name__)


class CerebrasProvider(LLMProvider):
    """
    LLM Provider for Cerebras API.

    Uses the native Cerebras SDK (not OpenAI-compatible) which supports
    structured JSON output via json_schema response format.
    """

    def __init__(
        self,
        api_keys: Iterator[str],
        model: str,
        reasoning_effort: str = "high",
        max_retries: int = 5,
        json_parse_retries: int = 3,
    ):
        self.api_key_iterator = api_keys
        self.model_name = model
        self.reasoning_effort = reasoning_effort
        self.max_retries = max_retries
        self.json_parse_retries = json_parse_retries

    @property
    def name(self) -> str:
        return "llm2deck_cerebras"

    @property
    def model(self) -> str:
        return self.model_name

    def _get_client(self) -> Cerebras:
        return Cerebras(api_key=next(self.api_key_iterator))

    async def _make_request(
        self,
        messages: List[Dict[str, Any]],
        json_schema: Dict[str, Any],
    ) -> Optional[str]:
        """Make a request with retry logic."""
        retry_decorator = create_retry_decorator(
            max_retries=self.max_retries,
            retry_logger=logger,
        )

        @retry_decorator
        async def _do_request() -> str:
            client = self._get_client()

            # Build request parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "card_schema",
                        "strict": True,
                        "schema": json_schema,
                    },
                },
                "temperature": 0.4,
            }

            # Add reasoning effort for compatible models
            if supports_reasoning_effort(self.model_name):
                params["reasoning_effort"] = self.reasoning_effort

            # Cerebras SDK is sync, so run in thread
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                **params,
            )

            content = completion.choices[0].message.content
            if not content:
                raise EmptyResponseError(
                    f"[{self.model_name}] Received empty response"
                )

            return content

        try:
            return await _do_request()
        except RetryError:
            logger.error(f"[{self.model_name}] All retry attempts failed")
            return None
        except Exception as e:
            logger.error(f"[{self.model_name}] Unexpected error: {e}")
            return None

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        """Generate initial cards for a given question."""
        template = prompt_template or prompts.initial

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates Anki cards in JSON format.",
            },
            {
                "role": "user",
                "content": template.format(
                    question=question,
                    schema=json.dumps(json_schema, indent=2, ensure_ascii=False),
                ),
            },
        ]

        content = await self._make_request(messages, json_schema)
        return content if content else ""

    async def combine_cards(
        self,
        question: str,
        combined_inputs: str,
        json_schema: Dict[str, Any],
        combine_prompt_template: Optional[str] = None,
    ) -> Optional[str]:
        """Combine multiple sets of cards into a single deck.

        Returns raw response string (may not be valid JSON).
        """
        template = combine_prompt_template or prompts.combine

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates Anki cards in JSON format.",
            },
            {
                "role": "user",
                "content": template.format(
                    question=question,
                    inputs=combined_inputs,
                ),
            },
        ]

        return await self._make_request(messages, json_schema)

    async def format_json(
        self,
        raw_content: str,
        json_schema: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Format raw content into valid JSON matching the schema.

        Cerebras supports structured JSON output natively, making it ideal for formatting.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a JSON formatting assistant. Your task is to extract and format "
                    "the content into valid JSON matching the provided schema. "
                    "Output ONLY valid JSON, nothing else."
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
            content = await self._make_request(messages, json_schema)
            if content:
                try:
                    return json.loads(content)
                except json.JSONDecodeError as error:
                    logger.warning(
                        f"[{self.model_name}] format_json attempt {attempt + 1}/{self.json_parse_retries}: "
                        f"JSON Decode Error: {error}. Retrying..."
                    )
                    continue

        logger.error(f"[{self.model_name}] format_json failed after {self.json_parse_retries} attempts.")
        return None
