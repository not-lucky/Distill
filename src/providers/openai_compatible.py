"""Base class for LLM providers using OpenAI-compatible APIs."""

import json
import asyncio
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Iterator

from openai import AsyncOpenAI, RateLimitError, APITimeoutError

from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE
import logging

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """
    Base class for providers using OpenAI-compatible APIs.

    Subclasses only need to define:
    - name property
    - __init__ that calls super().__init__() with appropriate config
    - Optionally override _get_extra_request_params() for provider-specific params
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        api_keys: Optional[Iterator[str]] = None,
        timeout: float = 120.0,
        max_retries: int = 5,
        temperature: float = 0.4,
        max_tokens: Optional[int] = None,
        strip_json_markers: bool = True,
    ):
        """
        Initialize an OpenAI-compatible provider.

        Args:
            model: Model identifier
            base_url: API base URL
            api_keys: Optional iterator of API keys (for rotation)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for requests
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response (None for API default)
            strip_json_markers: Whether to strip ```json markers from responses
        """
        self.model_name = model
        self.base_url = base_url
        self.api_key_iterator = api_keys
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.strip_json_markers = strip_json_markers

    @property
    def model(self) -> str:
        return self.model_name

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    def _get_api_key(self) -> str:
        """Get the next API key from the iterator, or empty string if none."""
        if self.api_key_iterator is None:
            return ""
        return next(self.api_key_iterator)

    def _get_client(self) -> AsyncOpenAI:
        """Create an AsyncOpenAI client instance."""
        return AsyncOpenAI(
            api_key=self._get_api_key(),
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def _get_extra_request_params(self) -> Dict[str, Any]:
        """
        Override this method to add provider-specific request parameters.

        Returns:
            Dict of extra parameters to pass to chat.completions.create()
        """
        return {}

    def _strip_json_block(self, content: str) -> str:
        """Strip markdown JSON code block markers if present."""
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        elif content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    async def _make_request(
        self,
        chat_messages: List[Dict[str, Any]],
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Make a request to the API with retry logic.

        Args:
            chat_messages: List of chat messages
            json_schema: Optional JSON schema (used for response formatting)

        Returns:
            Response content string, or None if all retries failed
        """
        for attempt in range(self.max_retries):
            try:
                client = self._get_client()

                request_params = {
                    "model": self.model_name,
                    "messages": chat_messages,
                    "temperature": self.temperature,
                }

                if self.max_tokens is not None:
                    request_params["max_tokens"] = self.max_tokens

                # Add provider-specific parameters
                request_params.update(self._get_extra_request_params())

                completion = await client.chat.completions.create(**request_params)
                response_content = completion.choices[0].message.content

                if response_content:
                    if self.strip_json_markers and json_schema:
                        response_content = self._strip_json_block(response_content)
                    return response_content

                logger.warning(
                    f"[{self.model_name}] Attempt {attempt + 1}/{self.max_retries}: "
                    "Received None content. Retrying..."
                )

            except RateLimitError:
                wait_time = 2 * (attempt + 1)
                logger.warning(
                    f"[{self.model_name}] Rate limit hit. "
                    f"Backing off for {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
                continue

            except APITimeoutError:
                logger.warning(f"[{self.model_name}] Request timed out.")

            except Exception as error:
                logger.error(
                    f"[{self.model_name}] Attempt {attempt + 1}/{self.max_retries} "
                    f"Error: {error}"
                )

            await asyncio.sleep(1)

        return None

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        """Generate initial cards for a given question."""
        active_template = prompt_template or INITIAL_PROMPT_TEMPLATE

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
        """Combine multiple sets of cards into a single deck."""
        active_template = combine_prompt_template or COMBINE_PROMPT_TEMPLATE

        chat_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates Anki cards in JSON format.",
            },
            {
                "role": "user",
                "content": active_template.format(
                    question=question,
                    inputs=combined_inputs,
                ),
            },
        ]

        # Retry JSON parsing separately from API calls
        for attempt in range(3):
            response_content = await self._make_request(chat_messages, json_schema)
            if response_content:
                try:
                    return json.loads(response_content)
                except json.JSONDecodeError as error:
                    logger.warning(
                        f"[{self.model_name}] Attempt {attempt + 1}/3: "
                        f"JSON Decode Error: {error}. Retrying..."
                    )
                    continue

        logger.error(f"[{self.model_name}] Failed to decode JSON after 3 attempts.")
        return None
