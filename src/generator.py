"""Card generation logic for LLM2Deck."""

import asyncio
import json
import logging
import time
from typing import List, Dict, Optional, Any

from pydantic import BaseModel

from src.models import LeetCodeProblem
from src.providers.base import LLMProvider
from src.repositories import CardRepository
from src.logging_utils import log_section, log_status
from src.types import CardResult

logger = logging.getLogger(__name__)


class CardGenerator:
    """Generates Anki cards using multiple LLM providers."""

    def __init__(
        self,
        providers: List[LLMProvider],
        combiner: LLMProvider,
        repository: CardRepository,
        combine_prompt: Optional[str] = None,
    ):
        """
        Initialize the card generator.

        Args:
            providers: List of LLM providers for initial generation.
            combiner: LLM provider used to combine results.
            repository: Repository for database operations.
            combine_prompt: Optional prompt template for combining.
        """
        self.llm_providers = providers
        self.card_combiner = combiner
        self.repository = repository
        self.combine_prompt = combine_prompt

    def _save_provider_results(
        self,
        problem_id: int,
        provider_results: List[str],
    ) -> List[str]:
        """
        Save valid provider results to database.

        Args:
            problem_id: ID of the problem.
            provider_results: List of raw results from providers.

        Returns:
            List of valid (non-empty) results.
        """
        valid_results = []

        for provider, result in zip(self.llm_providers, provider_results):
            if not result:
                continue

            # Count cards in result
            card_count = None
            try:
                result_json = json.loads(result)
                card_count = len(result_json.get("cards", []))
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

            self.repository.save_provider_result(
                problem_id=problem_id,
                provider_name=provider.name,
                provider_model=provider.model,
                raw_output=result,
                card_count=card_count,
            )
            valid_results.append(result)

        return valid_results

    def _post_process_cards(
        self,
        card_data: Dict[str, Any],
        category_index: Optional[int] = None,
        category_name: Optional[str] = None,
        problem_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Post-process card data: strip spaces from tags/types, add metadata.

        Args:
            card_data: Raw card data from combiner.
            category_index: Optional category index.
            category_name: Optional category name.
            problem_index: Optional problem index.

        Returns:
            Processed card data with metadata.
        """
        # Strip spaces from tags and card types
        for card in card_data.get("cards", []):
            if "tags" in card:
                card["tags"] = [tag.replace(" ", "") for tag in card["tags"]]
            if "card_type" in card:
                card["card_type"] = card["card_type"].replace(" ", "")

        # Add category metadata for ordered deck generation
        if category_index is not None:
            card_data["category_index"] = category_index
        if category_name is not None:
            card_data["category_name"] = category_name
        if problem_index is not None:
            card_data["problem_index"] = problem_index

        return card_data

    async def _generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str],
    ) -> List[str]:
        """
        Generate initial cards from all providers in parallel.

        Args:
            question: The question to generate cards for.
            json_schema: JSON schema for the card structure.
            prompt_template: Optional prompt template.

        Returns:
            List of raw results from each provider.
        """
        generation_tasks = [
            provider.generate_initial_cards(question, json_schema, prompt_template)
            for provider in self.llm_providers
        ]
        return await asyncio.gather(*generation_tasks)

    async def _combine_results(
        self,
        question: str,
        valid_results: List[str],
        json_schema: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Combine multiple provider results into final card data.

        Args:
            question: The question being processed.
            valid_results: List of valid provider results.
            json_schema: JSON schema for validation.

        Returns:
            Combined card data, or None if combining failed.
        """
        combined_inputs = ""
        for set_index, provider_result in enumerate(valid_results):
            combined_inputs += f"Set {set_index + 1}:\n{provider_result}\n\n"

        return await self.card_combiner.combine_cards(
            question, combined_inputs, json_schema, self.combine_prompt
        )

    async def process_question(
        self,
        question: str,
        prompt_template: Optional[str] = None,
        model_class: BaseModel = LeetCodeProblem,
        category_index: Optional[int] = None,
        category_name: Optional[str] = None,
        problem_index: Optional[int] = None,
    ) -> Optional[CardResult]:
        """
        Process a single question and generate cards.

        Args:
            question: The question/problem name.
            prompt_template: Optional prompt template.
            model_class: Pydantic model for the card structure.
            category_index: 1-based index of the category (for ordering).
            category_name: Name of the category.
            problem_index: 1-based index of the problem within its category.

        Returns:
            CardResult with card data including category metadata if provided.
        """
        start_time = time.time()
        json_schema = model_class.model_json_schema()

        with log_section(f"Processing: {question}"):
            # Create problem entry
            problem_id = self.repository.create_initial_problem(
                question_name=question,
                category_name=category_name,
                category_index=category_index,
                problem_index=problem_index,
            )

            # Generate initial cards in parallel
            with log_status(f"Generating initial ideas for '{question}'..."):
                provider_results = await self._generate_initial_cards(
                    question, json_schema, prompt_template
                )

        # Save and filter valid results
        valid_results = self._save_provider_results(problem_id, provider_results)

        if not valid_results:
            logger.error(f"All providers failed for '{question}'. Skipping.")
            self.repository.update_problem_failed(
                problem_id, time.time() - start_time
            )
            return None

        # Combine results
        final_card_data = await self._combine_results(
            question, valid_results, json_schema
        )

        if not final_card_data:
            logger.error(f"Failed to generate final JSON for '{question}'.")
            self.repository.update_problem_failed(
                problem_id, time.time() - start_time
            )
            return None

        # Post-process and save
        final_card_data = self._post_process_cards(
            final_card_data, category_index, category_name, problem_index
        )
        self.repository.save_final_result(
            problem_id, final_card_data, time.time() - start_time
        )

        return final_card_data
