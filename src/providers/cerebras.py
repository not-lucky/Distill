import json
import asyncio
from typing import Dict, Any, Optional
from cerebras.cloud.sdk import Cerebras
from src.providers.base import LLMProvider
from src.config import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE

class CerebrasProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, reasoning_effort: str = "high"):
        self.client = Cerebras(api_key=api_key)
        self.model = model
        self.reasoning_effort = reasoning_effort

    async def generate_initial_cards(self, question: str, schema: Dict[str, Any]) -> str:
        print(f"  [Cerebras:{self.model}] Generating initial cards for '{question}'...")
        try:
            optional_args = {}
            if self.model == "gpt-oss-120b": # Or check if model supports it
                 optional_args["reasoning_effort"] = self.reasoning_effort

            messages = [
                {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
                {"role": "user", "content": INITIAL_PROMPT_TEMPLATE.format(
                    question=question,
                    schema=json.dumps(schema, indent=2)
                )},
            ]

            # Cerebras SDK is synchronous, so we run it in a thread
            completion = await asyncio.to_thread(
                self.client.chat.completions.create,
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
            return completion.choices[0].message.content
        except Exception as e:
            print(f"  [Cerebras:{self.model}] Error: {e}")
            return ""

    async def combine_cards(self, question: str, inputs: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print(f"  [Cerebras:{self.model}] Combining cards for '{question}'...")
        try:
            optional_args = {}
            if self.model == "gpt-oss-120b":
                 optional_args["reasoning_effort"] = self.reasoning_effort

            messages = [
                {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
                {"role": "user", "content": COMBINE_PROMPT_TEMPLATE.format(
                    question=question,
                    inputs=inputs
                )},
            ]

            completion = await asyncio.to_thread(
                self.client.chat.completions.create,
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
                temperature=0.2,
                **optional_args
            )
            content = completion.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"  [Cerebras:{self.model}] Combination Error: {e}")
            return None
