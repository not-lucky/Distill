import asyncio
import json
import time
from typing import List, Dict, Optional
from pydantic import BaseModel
from src.models import LeetCodeProblem
from src.providers.base import LLMProvider
from src.prompts import (
    MCQ_COMBINE_PROMPT_TEMPLATE,
    COMBINE_LEETCODE_PROMPT_TEMPLATE,
    COMBINE_CS_PROMPT_TEMPLATE,
)
from src.database import (
    get_session,
    create_problem,
    update_problem,
    create_provider_result,
    create_cards,
)
import logging

from src.logging_utils import log_section, log_status, console

logger = logging.getLogger(__name__)


class CardGenerator:
    def __init__(
        self,
        providers: List[LLMProvider],
        combiner: LLMProvider,
        mode: str = "default",
        run_id: str = None,
    ):
        self.llm_providers = providers
        self.card_combiner = combiner
        self.generation_mode = mode
        self.run_id = run_id

    async def process_question(
        self,
        question: str,
        prompt_template: Optional[str] = None,
        model_class: BaseModel = LeetCodeProblem,
        category_index: Optional[int] = None,
        category_name: Optional[str] = None,
        problem_index: Optional[int] = None,
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
        start_time = time.time()

        with log_section(f"Processing: {question}"):
            # Create problem entry in database
            session = get_session()
            problem = create_problem(
                session=session,
                run_id=self.run_id,
                question_name=question,
                category_name=category_name,
                category_index=category_index,
                problem_index=problem_index,
                status="running",
            )
            problem_id = problem.id
            session.close()

            # 1. Generate Initial Cards (Parallel)
            with log_status(f"Generating initial ideas for '{question}'..."):
                generation_tasks = []
                json_schema = model_class.model_json_schema()

                for provider in self.llm_providers:
                    generation_tasks.append(
                        provider.generate_initial_cards(
                            question, json_schema, prompt_template
                        )
                    )

                provider_results = await asyncio.gather(*generation_tasks)

        valid_provider_results = []

        # Save each provider result to database
        for provider, result in zip(self.llm_providers, provider_results):
            if result:  # Only save valid results
                session = get_session()

                # Count cards in result
                try:
                    result_json = json.loads(result)
                    card_count = len(result_json.get("cards", []))
                except (json.JSONDecodeError, KeyError, TypeError):
                    card_count = None

                create_provider_result(
                    session=session,
                    problem_id=problem_id,
                    run_id=self.run_id,
                    provider_name=provider.name,
                    provider_model=provider.model,
                    success=True,
                    raw_output=result,
                    card_count=card_count,
                )
                session.close()
                valid_provider_results.append(result)

        if not valid_provider_results:
            logger.error(f"All providers failed for '{question}'. Skipping.")
            # Update problem status to failed
            session = get_session()
            update_problem(
                session,
                problem_id,
                status="failed",
                processing_time_seconds=time.time() - start_time,
            )
            session.close()
            return None

        # 2. Combine Cards
        combined_inputs = ""
        for set_index, provider_result in enumerate(valid_provider_results):
            combined_inputs += f"Set {set_index + 1}:\n{provider_result}\n\n"

        # Select appropriate combining prompt based on mode
        if "mcq" in self.generation_mode:
            combine_prompt = MCQ_COMBINE_PROMPT_TEMPLATE
        elif "leetcode" in self.generation_mode:
            combine_prompt = COMBINE_LEETCODE_PROMPT_TEMPLATE
        elif "cs" in self.generation_mode:
            combine_prompt = COMBINE_CS_PROMPT_TEMPLATE
        else:
            combine_prompt = None
        final_card_data = await self.card_combiner.combine_cards(
            question, combined_inputs, json_schema, combine_prompt
        )

        if final_card_data:
            # Post-process tags/types
            for card in final_card_data.get("cards", []):
                if "tags" in card:
                    card["tags"] = [tag.replace(" ", "") for tag in card["tags"]]
                if "card_type" in card:
                    card["card_type"] = card["card_type"].replace(" ", "")

            # Add category metadata if provided (for ordered deck generation)
            if category_index is not None:
                final_card_data["category_index"] = category_index
            if category_name is not None:
                final_card_data["category_name"] = category_name
            if problem_index is not None:
                final_card_data["problem_index"] = problem_index

            # Save to database
            session = get_session()

            # Update problem with final result
            processing_time = time.time() - start_time
            update_problem(
                session=session,
                problem_id=problem_id,
                status="success",
                final_result=json.dumps(final_card_data),
                final_card_count=len(final_card_data.get("cards", [])),
                processing_time_seconds=processing_time,
            )

            # Save individual cards
            create_cards(
                session=session,
                problem_id=problem_id,
                run_id=self.run_id,
                cards_data=final_card_data.get("cards", []),
            )

            session.close()

            logger.info(
                f"Saved {len(final_card_data.get('cards', []))} cards to database for '{question}'"
            )

            return final_card_data
        else:
            logger.error(f"Failed to generate final JSON for '{question}'.")
            session = get_session()
            update_problem(
                session,
                problem_id,
                status="failed",
                processing_time_seconds=time.time() - start_time,
            )
            session.close()
            return None
