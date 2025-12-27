import json
import asyncio
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE
import logging

logger = logging.getLogger(__name__)

class NvidiaProvider(LLMProvider):
    def __init__(self, api_keys: Any, model: str):
        self.api_keys = api_keys
        self.model = model
        self.base_url = "https://integrate.api.nvidia.com/v1"

    def _get_client(self) -> AsyncOpenAI:
        key = next(self.api_keys)
        return AsyncOpenAI(api_key=key, base_url=self.base_url)

    async def _make_request(self, messages: List[Dict[str, Any]], schema: Dict[str, Any], retries: int = 3) -> Optional[str]:
        for attempt in range(retries):
            try:
                client = self._get_client()
                
                # Note: The user explicitly requested NOT to use/need reasoning content, 
                # so we do not pass "thinking": True in extra_body.
                
                completion = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.4,
                    top_p=0.95,
                    max_tokens=16384,
                    extra_body={
                        # "nvext": {"guided_json": schema},
                        "chat_template_kwargs": {"thinking":True}
                    }
                )
                
                content = completion.choices[0].message.content
                if content:
                    if schema:
                        content = content.lstrip('```json').rstrip('```').strip()
                    return content
                
                logger.warning(f"[{self.model}] Attempt {attempt+1}/{retries}: Received None content. Retrying...")
                
            except Exception as e:
                logger.error(f"[{self.model}] Attempt {attempt+1}/{retries} Error: {e}")
                
            await asyncio.sleep(1)
            
        return None

    async def generate_initial_cards(self, question: str, schema: Dict[str, Any], prompt_template: Optional[str] = None) -> str:
        # logger.info(f"[{self.model}] Generating initial cards for '{question}'...")
        
        template = prompt_template if prompt_template else INITIAL_PROMPT_TEMPLATE
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
            {"role": "user", "content": template.format(
                question=question,
                schema=json.dumps(schema, indent=2, ensure_ascii=False)
            )},
        ]
        
        content = await self._make_request(messages, schema)
        return content if content else ""

    async def combine_cards(self, question: str, inputs: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # logger.info(f"[{self.model}] Combining cards for '{question}'...")
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
                logger.error(f"[{self.model}] JSON Decode Error: {e}")
                return None
        return None
