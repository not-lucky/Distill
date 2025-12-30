import json
import re
import asyncio
from typing import Dict, Any, Optional, List
from g4f.client import AsyncClient
from src.providers.base import LLMProvider
from src.prompts import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE
import logging

logger = logging.getLogger(__name__)

class G4FProvider(LLMProvider):
    def __init__(self, model: str = "claude-opus-4-5-20251101-thinking-32k", provider: Optional[str] = "LMArena"):
        self.model = model
        self.provider = provider
        self.client = AsyncClient(
            provider=self.provider
        )

    async def _make_request(self, messages: List[Dict[str, Any]], schema: Dict[str, Any], retries: int = 3) -> Optional[str]:
        for attempt in range(retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                
                content = response.choices[0].message.content
                if not content:
                     logger.warning(f"[G4F:{self.model}] Attempt {attempt+1}/{retries}: Received None content. Retrying...")
                     continue
                
                # Try to extract JSON if it's wrapped in markdown
                json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                elif "```" in content: 
                     # Fallback for code block without language specifier
                     json_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
                     if json_match:
                        content = json_match.group(1)

                return content
                
            except Exception as e:
                logger.error(f"[G4F:{self.model}] Attempt {attempt+1}/{retries} Error: {e}")
                
            await asyncio.sleep(1)
            
        return None

    async def generate_initial_cards(self, question: str, schema: Dict[str, Any], prompt_template: Optional[str] = None) -> str:
        # logger.info(f"[G4F:{self.model}] Generating initial cards for '{question}'...")
        
        template = prompt_template if prompt_template else INITIAL_PROMPT_TEMPLATE
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format. Return ONLY the JSON object, no other text."},
            {"role": "user", "content": template.format(
                question=question,
                schema=json.dumps(schema, indent=2, ensure_ascii=False)
            )},
        ]
        
        content = await self._make_request(messages, schema)
        return content if content else ""

    async def combine_cards(self, question: str, inputs: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # logger.info(f"[G4F:{self.model}] Combining cards for '{question}'...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format. Return ONLY the JSON object, no other text."},
            {"role": "user", "content": COMBINE_PROMPT_TEMPLATE.format(
                question=question,
                inputs=inputs
            )},
        ]
        
        for attempt in range(3):
            content = await self._make_request(messages, schema)
            if content:
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"[G4F:{self.model}] Attempt {attempt+1}/3: JSON Decode Error: {e}. Content preview: {content[:100]}... Retrying...")
                    continue
        
        logger.error(f"[G4F:{self.model}] Failed to decode JSON after 3 attempts.")
        return None
