import json
import logging
import asyncio
from typing import Dict, Any, Optional, Iterator
from google import genai
from google.genai import types

from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, MCQ_COMBINE_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class GoogleGenAIProvider(LLMProvider):
    def __init__(self, api_keys: Iterator[str], model: str = "gemini-3-pro-preview"):
        """
        Initialize the Google GenAI provider.
        
        Args:
            api_keys: An iterator that yields API keys (e.g. itertools.cycle).
            model: The model identifier to use (default: gemini-3-pro-preview).
        """
        self.api_keys = api_keys
        self.model = model

    def _get_client(self) -> genai.Client:
        """Get a client instance with the next API key."""
        try:
            api_key = next(self.api_keys)
            return genai.Client(api_key=api_key)
        except StopIteration:
            logger.error("No Google GenAI API keys available.")
            raise ValueError("No Google GenAI API keys available.")

    async def generate_initial_cards(self, question: str, json_schema: Dict[str, Any], prompt_template: Optional[str] = None) -> str:
        """Generates initial cards using Google GenAI."""
        # logger.info(f"[GoogleGenAI] Generating initial cards for '{question}' with model {self.model}...")
        client = self._get_client()
        active_template = prompt_template if prompt_template else INITIAL_PROMPT_TEMPLATE
        
        # We include the schema in the prompt text as well, as the template expects it.
        # This double-reinforces the structure.
        formatted_prompt = active_template.format(
            question=question,
            schema=json.dumps(json_schema, indent=2, ensure_ascii=False)
        )

        def _call_api():
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=formatted_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=json_schema,
                        thinking_config=types.ThinkingConfig(thinking_level="high") if "flash" not in self.model else types.ThinkingConfig(thinking_level="medium")
                    )
                )
                return response.text
            except Exception as e:
                logger.error(f"[GoogleGenAI] API call failed: {e}")
                raise

        try:
            loop = asyncio.get_running_loop()
            response_text = await loop.run_in_executor(None, _call_api)
            return response_text if response_text else ""
        except Exception as error:
            logger.error(f"[GoogleGenAI] Error generating cards: {error}")
            return ""

    async def combine_cards(self, question: str, combined_inputs: str, json_schema: Dict[str, Any], combine_prompt_template: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Combines multiple sets of cards into a single deck."""
        # logger.info(f"[GoogleGenAI] Combining cards for '{question}'...")
        client = self._get_client()
        
        prompt_template = combine_prompt_template if combine_prompt_template else MCQ_COMBINE_PROMPT_TEMPLATE
        if prompt_template:
             formatted_prompt = prompt_template.format(
                question=question,
                combined_inputs=combined_inputs,
                schema=json.dumps(json_schema, indent=2, ensure_ascii=False)
            )
        else:
             # Fallback if no template provided, though unlikely given logic in generator.py
             formatted_prompt = f"Combine these inputs for {question}:\n{combined_inputs}"

        def _call_api():
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=formatted_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=json_schema
                    )
                )
                return response.text
            except Exception as e:
                logger.error(f"[GoogleGenAI] API call failed during combination: {e}")
                raise

        try:
            loop = asyncio.get_running_loop()
            response_text = await loop.run_in_executor(None, _call_api)
            
            if not response_text:
                return None
                
            return json.loads(response_text)
        except Exception as error:
            logger.error(f"[GoogleGenAI] Error combining cards: {error}")
            return None
