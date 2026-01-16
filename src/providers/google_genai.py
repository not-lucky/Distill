import json
import asyncio
import itertools
from typing import Dict, Any, Optional, List, Iterator
from google import genai
from google.genai import types
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE
import logging

logger = logging.getLogger(__name__)


class GoogleGenAIProvider(LLMProvider):
    """
    Provider for Google's official Gemini API using the google-genai package.
    Supports Gemini 3 models with thinking_level and other advanced features.
    """

    def __init__(
        self,
        api_keys: Iterator[str],
        model: str = "gemini-3-flash-preview",
        thinking_level: str = "high",
    ):
        """
        Initialize the GoogleGenAIProvider.

        Args:
            api_keys: An iterator (e.g., itertools.cycle) of API keys for rotation.
            model: The model ID to use (e.g., "gemini-3-pro-preview", "gemini-3-flash-preview").
            thinking_level: The thinking level for Gemini 3 models ("low", "medium", "high", "minimal").
                           Note: "medium" and "minimal" are only supported by Gemini 3 Flash.
        """
        self.api_key_iterator = api_keys
        self.model_name = model
        self.thinking_level = thinking_level

    @property
    def name(self) -> str:
        return "llm2deck_google_genai"

    @property
    def model(self) -> str:
        return self.model_name

    def _get_client(self) -> genai.Client:
        """Get a new client with the next API key in rotation."""
        current_api_key = next(self.api_key_iterator)
        return genai.Client(api_key=current_api_key)

    async def _make_request(
        self,
        contents: str,
        json_schema: Optional[Dict[str, Any]] = None,
        max_retries: int = 5,
    ) -> Optional[str]:
        """
        Make a request to the Gemini API with retry logic.

        Args:
            contents: The prompt/contents to send to the model.
            json_schema: Optional JSON schema for structured output.
            max_retries: Maximum number of retry attempts.

        Returns:
            The response text or None if all retries failed.
        """
        for attempt_number in range(max_retries):
            try:
                client = self._get_client()

                # Build the config
                config_dict: Dict[str, Any] = {
                    "thinking_config": types.ThinkingConfig(
                        thinking_level=self.thinking_level
                    ),
                    "temperature": 1.0,  # Gemini 3 recommends keeping temperature at 1.0
                    # "tools": [
                    #     {"google_search": {}},
                    #     {"url_context": {}}
                    # ],
                }

                # Add JSON schema for structured output if provided
                if json_schema:
                    config_dict["response_mime_type"] = "application/json"
                    config_dict["response_json_schema"] = json_schema

                config = types.GenerateContentConfig(**config_dict)

                # Make the API call in a thread to avoid blocking
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )

                if response.text:
                    return response.text

                logger.warning(
                    f"[{self.model_name}] Attempt {attempt_number + 1}/{max_retries}: "
                    "Received empty response. Retrying..."
                )

            except Exception as error:
                logger.error(
                    f"[{self.model_name}] Attempt {attempt_number + 1}/{max_retries} "
                    f"Error: {error}"
                )

            # Small delay between retries
            await asyncio.sleep(1)

        return None

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        """
        Generates initial Anki cards for a given question.

        Args:
            question: The question/topic to generate cards for.
            json_schema: The JSON schema for the response format.
            prompt_template: Optional custom prompt template.

        Returns:
            The generated content as a string, or empty string on failure.
        """
        active_template = (
            prompt_template if prompt_template else INITIAL_PROMPT_TEMPLATE
        )

        formatted_prompt = active_template.format(
            question=question,
            schema=json.dumps(json_schema, indent=2, ensure_ascii=False),
        )

        response_content = await self._make_request(formatted_prompt, json_schema)
        return response_content if response_content else ""

    async def combine_cards(
        self,
        question: str,
        combined_inputs: str,
        json_schema: Dict[str, Any],
        combine_prompt_template: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Combines multiple sets of cards into a single deck.

        Args:
            question: The question/topic for the cards.
            combined_inputs: The combined input from multiple card generations.
            json_schema: The JSON schema for the response format.
            combine_prompt_template: Optional custom combine prompt template.

        Returns:
            The combined cards as a dictionary, or None on failure.
        """
        active_template = (
            combine_prompt_template
            if combine_prompt_template
            else COMBINE_PROMPT_TEMPLATE
        )

        formatted_prompt = active_template.format(
            question=question, inputs=combined_inputs
        )

        for attempt_number in range(5):
            response_content = await self._make_request(formatted_prompt, json_schema)
            if response_content:
                try:
                    return json.loads(response_content)
                except json.JSONDecodeError as decode_error:
                    logger.warning(
                        f"[{self.model_name}] Attempt {attempt_number + 1}/5: "
                        f"JSON Decode Error: {decode_error}. Retrying..."
                    )
                    continue

        logger.error(f"[{self.model_name}] Failed to decode JSON after 5 attempts.")
        return None
