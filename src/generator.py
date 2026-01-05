import asyncio
import json
from typing import List, Dict, Optional
from pydantic import BaseModel
from src.models import LeetCodeProblem
from src.providers.base import LLMProvider
from src.prompts import MCQ_COMBINE_PROMPT_TEMPLATE
from src.utils import save_archival
import logging

from src.logging_utils import log_section, log_status, console

logger = logging.getLogger(__name__)

class CardGenerator:
    def __init__(self, providers: List[LLMProvider], combiner: LLMProvider, mode: str = "default"):
        self.providers = providers
        self.combiner = combiner
        self.mode = mode

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
                tasks = []
                schema = model_class.model_json_schema()
                
                for provider in self.providers:
                    tasks.append(provider.generate_initial_cards(question, schema, prompt_template))
                
                results = await asyncio.gather(*tasks)
        
        valid_results = [r for r in results if r]
        
        if not valid_results:
            logger.error(f"All providers failed for '{question}'. Skipping.")
            return None

        # 2. Combine Cards
        inputs = ""
        for i, res in enumerate(valid_results):
            inputs += f"Set {i+1}:\n{res}\n\n"
        
        # Use MCQ combine prompt if mode contains 'mcq'
        combine_prompt = MCQ_COMBINE_PROMPT_TEMPLATE if 'mcq' in self.mode else None
        final_data = await self.combiner.combine_cards(question, inputs, schema, combine_prompt)
        
        if final_data:
            # Post-process tags/types
            for card in final_data.get('cards', []):
                if 'tags' in card:
                    card['tags'] = [tag.replace(' ', '') for tag in card['tags']]
                if 'card_type' in card:
                    card['card_type'] = card['card_type'].replace(' ', '')
            
            # Add category metadata if provided (for ordered deck generation)
            if category_index is not None:
                final_data['category_index'] = category_index
            if category_name is not None:
                final_data['category_name'] = category_name
            if problem_index is not None:
                final_data['problem_index'] = problem_index

            save_archival(question, final_data, subdir=self.mode)
            return final_data
        else:
            logger.error(f"Failed to generate final JSON for '{question}'.")
            return None
