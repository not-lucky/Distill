import asyncio
import json
from typing import List, Dict, Optional
from pydantic import BaseModel
from src.models import LeetCodeProblem
from src.providers.base import LLMProvider
from src.prompts import MCQ_COMBINE_PROMPT_TEMPLATE, COMBINE_LEETCODE_PROMPT_TEMPLATE, COMBINE_CS_PROMPT_TEMPLATE
from src.utils import save_archival
import logging

from src.logging_utils import log_section, log_status, console

logger = logging.getLogger(__name__)

class CardGenerator:
    def __init__(self, providers: List[LLMProvider], combiner: LLMProvider, mode: str = "default"):
        self.llm_providers = providers
        self.card_combiner = combiner
        self.generation_mode = mode

    async def process_question(
        self, 
        question: str, 
        prompt_template: Optional[str] = None, 
        model_class: BaseModel = LeetCodeProblem,
        category_index: Optional[int] = None,
        category_name: Optional[str] = None,
        problem_index: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Process a single question and generate cards.
        
        Args:
            question: The question/problem name
            prompt_template: Optional prompt template
            model_class: Pydantic model for the card structure
            category_index: 1-based index of the category (for ordering)
            category_name: Name of the category
            problem_index: 1-based index of the problem within its category
            
        Returns:
            Dict with card data including category metadata if provided
        """
        with log_section(f"Processing: {question}"):
            # 1. Generate Initial Cards (Parallel)
            with log_status(f"Generating initial ideas for '{question}'..."):
                generation_tasks = []
                json_schema = model_class.model_json_schema()
                
                for provider in self.llm_providers:
                    generation_tasks.append(provider.generate_initial_cards(question, json_schema, prompt_template))
                
                provider_results = await asyncio.gather(*generation_tasks)
        
        valid_provider_results = [result for result in provider_results if result]
        
        if not valid_provider_results:
            logger.error(f"All providers failed for '{question}'. Skipping.")
            return None

        # 2. Combine Cards
        combined_inputs = ""
        for set_index, provider_result in enumerate(valid_provider_results):
            combined_inputs += f"Set {set_index+1}:\n{provider_result}\n\n"
        
        # Select appropriate combining prompt based on mode
        if 'mcq' in self.generation_mode:
            combine_prompt = MCQ_COMBINE_PROMPT_TEMPLATE
        elif 'leetcode' in self.generation_mode:
            combine_prompt = COMBINE_LEETCODE_PROMPT_TEMPLATE
        elif 'cs' in self.generation_mode:
            combine_prompt = COMBINE_CS_PROMPT_TEMPLATE
        else:
            combine_prompt = None
        final_card_data = await self.card_combiner.combine_cards(question, combined_inputs, json_schema, combine_prompt)
        
        if final_card_data:
            # Post-process tags/types
            for card in final_card_data.get('cards', []):
                if 'tags' in card:
                    card['tags'] = [tag.replace(' ', '') for tag in card['tags']]
                if 'card_type' in card:
                    card['card_type'] = card['card_type'].replace(' ', '')
            
            # Add category metadata if provided (for ordered deck generation)
            if category_index is not None:
                final_card_data['category_index'] = category_index
            if category_name is not None:
                final_card_data['category_name'] = category_name
            if problem_index is not None:
                final_card_data['problem_index'] = problem_index

            save_archival(question, final_card_data, subdir=self.generation_mode)
            return final_card_data
        else:
            logger.error(f"Failed to generate final JSON for '{question}'.")
            return None
