import json
import re
import asyncio
import itertools
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE

class OpenRouterProvider(LLMProvider):
    def __init__(self, api_keys: List[str], model: str):
        self.api_keys = itertools.cycle(api_keys)
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=next(self.api_keys),
            base_url=self.base_url,
            # default_headers={
            #     "HTTP-Referer": "https://github.com/not-lucky/LLM2Deck", # Optional, for OpenRouter rankings
            #     "X-Title": "LLM2Deck", # Optional
            # }
        )

    async def _make_request(self, messages: List[Dict[str, Any]], schema: Dict[str, Any], retries: int = 3) -> Optional[str]:
        for attempt in range(retries):
            try:
                client = self._get_client()
                completion = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.4,
                )
                
                content = completion.choices[0].message.content
                
                print(f"  [OpenRouter:{self.model}] Attempt {attempt+1}/{retries}: Received None content. Retrying...")
                
            except Exception as e:
                print(f"  [OpenRouter:{self.model}] Attempt {attempt+1}/{retries} Error: {e}")
                
            await asyncio.sleep(1)
            
        return None

    async def generate_initial_cards(self, question: str, schema: Dict[str, Any], prompt_template: Optional[str] = None) -> str:
        print(f"  [OpenRouter:{self.model}] Generating initial cards for '{question}'...")
        
        template = prompt_template if prompt_template else INITIAL_PROMPT_TEMPLATE
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
            {"role": "user", "content": template.format(
                question=question,
                schema=json.dumps(schema, indent=2)
            )},
        ]
        
        content = await self._make_request(messages, schema)
        return content if content else ""

    async def combine_cards(self, question: str, inputs: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print(f"  [OpenRouter:{self.model}] Combining cards for '{question}'...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
            {"role": "user", "content": COMBINE_PROMPT_TEMPLATE.format(
                question=question,
                inputs=inputs
            )},
        ]
        
        content = await self._make_request(messages, schema)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"  [OpenRouter:{self.model}] JSON Decode Error: {e}")
                return None
        return None
