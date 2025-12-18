import json
import asyncio
import itertools
from typing import Dict, Any, Optional, List
from cerebras.cloud.sdk import Cerebras
from src.providers.base import LLMProvider
from src.config import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE

class CerebrasProvider(LLMProvider):
    def __init__(self, api_keys: List[str], model: str, reasoning_effort: str = "high"):
        self.api_keys = itertools.cycle(api_keys)
        self.model = model
        self.reasoning_effort = reasoning_effort

    def _get_client(self) -> Cerebras:
        return Cerebras(api_key=next(self.api_keys))

    async def _make_request(self, messages: List[Dict[str, Any]], schema: Dict[str, Any], retries: int = 5) -> Optional[str]:
        for attempt in range(retries):
            try:
                client = self._get_client()
                optional_args = {}
                if self.model == "gpt-oss-120b":
                     optional_args["reasoning_effort"] = self.reasoning_effort

                completion = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "leetcode_problem_schema",
                            "strict": True,
                            "schema": schema
                        }
                    },
                    temperature=0.4,
                    **optional_args
                )
                
                content = completion.choices[0].message.content
                if content:
                    return content
                
                print(f"  [Cerebras:{self.model}] Attempt {attempt+1}/{retries}: Received None content. Retrying...")
                
            except Exception as e:
                print(f"  [Cerebras:{self.model}] Attempt {attempt+1}/{retries} Error: {e}")
                
            # Optional: Add a small delay between retries if needed
            await asyncio.sleep(1)
            
        return None

    async def generate_initial_cards(self, question: str, schema: Dict[str, Any]) -> str:
        print(f"  [Cerebras:{self.model}] Generating initial cards for '{question}'...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
            {"role": "user", "content": INITIAL_PROMPT_TEMPLATE.format(
                question=question,
                schema=json.dumps(schema, indent=2)
            )},
        ]
        
        content = await self._make_request(messages, schema)
        return content if content else ""

    async def combine_cards(self, question: str, inputs: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print(f"  [Cerebras:{self.model}] Combining cards for '{question}'...")
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
                print(f"  [Cerebras:{self.model}] JSON Decode Error: {e}")
                return None
        return None
