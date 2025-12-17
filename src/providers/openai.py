import json
import asyncio
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from src.providers.base import LLMProvider
from src.config import INITIAL_PROMPT_TEMPLATE, COMBINE_PROMPT_TEMPLATE

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str, reasoning_effort: str = "medium"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.reasoning_effort = reasoning_effort

    async def generate_initial_cards(self, question: str, schema: Dict[str, Any]) -> str:
        print(f"  [{self.model}] Generating initial cards for '{question}'...")
        try:
            optional_args = {}
            # Check if model supports reasoning_effort (e.g. o1/o3 models) or if it's a generic parameter we want to pass
            # For now, let's only pass it if explicitly requested or known to be supported. 
            # However, the user asked for "openai api compatible", so we should be careful with proprietary params.
            # We'll stick to standard params for now, but keep reasoning_effort if the user wants to extend it.
            
            # Note: The original code used `reasoning_effort` for Cerebras (gpt-oss-120b). 
            # We will include it if the model name suggests it might be useful or if configured.
            # For broad compatibility, we might want to omit it unless we know the provider supports it.
            # But let's assume standard OpenAI chat completion.
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
                {"role": "user", "content": INITIAL_PROMPT_TEMPLATE.format(
                    question=question,
                    schema=json.dumps(schema, indent=2)
                )},
            ]

            completion = await self.client.chat.completions.create(
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
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"  [{self.model}] Error: {e}")
            return ""

    async def combine_cards(self, question: str, inputs: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print(f"  [{self.model}] Combining cards for '{question}'...")
        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
                {"role": "user", "content": COMBINE_PROMPT_TEMPLATE.format(
                    question=question,
                    inputs=inputs
                )},
            ]

            completion = await self.client.chat.completions.create(
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
            )
            content = completion.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"  [{self.model}] Combination Error: {e}")
            return None
