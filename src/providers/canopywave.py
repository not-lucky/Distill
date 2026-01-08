import json
import asyncio
import itertools
from typing import Dict, Any, Optional, List
import httpx
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE
import logging

logger = logging.getLogger(__name__)

class CanopywaveProvider(LLMProvider):
    """
    LLM Provider for Canopywave API.
    
    Supports inference through https://inference.canopywave.io/v1/chat/completions
    
    API Reference:
    - Endpoint: https://inference.canopywave.io/v1/chat/completions
    - Auth: Bearer token in Authorization header
    - Models: deepseek/deepseek-chat-v3.2, and others
    """
    
    def __init__(self, api_keys: List[str], model: str = "deepseek/deepseek-chat-v3.2"):
        """
        Initialize Canopywave provider.
        
        Args:
            api_keys: List of API keys or iterator of keys
            model: Model name (default: deepseek/deepseek-chat-v3.2)
        """
        # Handle both list and iterator inputs
        if isinstance(api_keys, list):
            self.api_key_cycle = itertools.cycle(api_keys)
        else:
            self.api_key_cycle = api_keys
            
        self.model_name = model
        self.api_base_url = "https://inference.canopywave.io/v1"
        self.timeout = 300.0

    async def _make_request(self, chat_messages: List[Dict[str, Any]], json_schema: Dict[str, Any], max_retries: int = 5) -> Optional[str]:
        """
        Make an API request to Canopywave.
        
        Args:
            chat_messages: List of chat messages
            json_schema: JSON schema for structured output
            max_retries: Number of retries on failure
            
        Returns:
            Response content as string, or None on failure
        """
        for attempt_number in range(max_retries):
            try:
                current_api_key = next(self.api_key_cycle)
                
                headers = {
                    "Authorization": f"Bearer {current_api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model_name,
                    "messages": chat_messages,
                    "temperature": 0.4,
                    "max_tokens": 132000,
                }
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.api_base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        response_content = response_data.get("choices", [{}])[0].get("message", {}).get("content")
                        
                        if response_content:
                            return response_content
                        else:
                            logger.warning(f"[{self.model_name}] Attempt {attempt_number+1}/{max_retries}: Received empty content. Retrying...")
                    else:
                        logger.error(f"[{self.model_name}] Attempt {attempt_number+1}/{max_retries} HTTP {response.status_code}: {response.text[:200]}")
                
            except httpx.TimeoutException:
                logger.error(f"[{self.model_name}] Attempt {attempt_number+1}/{max_retries}: Timeout. Retrying...")
            except httpx.RequestError as request_error:
                logger.error(f"[{self.model_name}] Attempt {attempt_number+1}/{max_retries} Request Error: {request_error}")
            except Exception as error:
                logger.error(f"[{self.model_name}] Attempt {attempt_number+1}/{max_retries} Error: {error}")
            
            # Add delay between retries
            if attempt_number < max_retries - 1:
                await asyncio.sleep(2)
        
        return None

    async def generate_initial_cards(self, question: str, json_schema: Dict[str, Any], prompt_template: Optional[str] = None) -> str:
        """
        Generate initial cards for a question.
        
        Args:
            question: The problem/question text
            json_schema: Expected JSON schema for output
            prompt_template: Optional custom prompt template
            
        Returns:
            JSON string with generated cards
        """
        active_template = prompt_template if prompt_template else INITIAL_PROMPT_TEMPLATE
        
        chat_messages = [
            {
                "role": "system", 
                "content": "You are a helpful assistant that generates Anki cards in JSON format. Always output valid JSON."
            },
            {
                "role": "user", 
                "content": active_template.format(
                    question=question,
                    schema=json.dumps(json_schema, indent=2, ensure_ascii=False)
                )
            },
        ]
        
        response_content = await self._make_request(chat_messages, json_schema)
        return response_content if response_content else ""

    async def combine_cards(self, question: str, combined_inputs: str, json_schema: Dict[str, Any], combine_prompt_template: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Combine multiple sets of cards into a single cohesive deck.
        
        Args:
            question: The problem/question text
            combined_inputs: Pre-formatted input sets to combine
            json_schema: Expected JSON schema for output
            combine_prompt_template: Optional custom combining prompt
            
        Returns:
            Parsed JSON dict with combined cards, or None on failure
        """
        active_template = combine_prompt_template if combine_prompt_template else COMBINE_PROMPT_TEMPLATE
        
        chat_messages = [
            {
                "role": "system", 
                "content": "You are a helpful assistant that generates Anki cards in JSON format. Always output valid JSON."
            },
            {
                "role": "user", 
                "content": active_template.format(
                    question=question,
                    inputs=combined_inputs
                )
            },
        ]
        
        for attempt_number in range(7):
            response_content = await self._make_request(chat_messages, json_schema, max_retries=3)
            if response_content:
                try:
                    return json.loads(response_content)
                except json.JSONDecodeError as decode_error:
                    logger.warning(f"[{self.model_name}] Attempt {attempt_number+1}/3: JSON Decode Error: {decode_error}. Retrying...")
                    continue
        
        logger.error(f"[{self.model_name}] Failed to decode JSON after 3 attempts.")
        return None
