"""Orchestrator for LLM2Deck card generation workflow."""

import asyncio
import logging
import uuid
from typing import List, Dict, Optional, Tuple

from src.config import CONCURRENT_REQUESTS, DATABASE_PATH

logger = logging.getLogger(__name__)
from src.config.subjects import SubjectConfig
from src.setup import initialize_providers
from src.generator import CardGenerator
from src.repositories import CardRepository
from src.utils import save_final_deck
from src.questions import get_indexed_questions
from src.database import init_database, create_run, update_run, get_session


class Orchestrator:
    """Coordinates the card generation workflow."""

    def __init__(
        self,
        subject_config: SubjectConfig,
        is_mcq: bool = False,
        run_label: Optional[str] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            subject_config: Configuration for the subject/mode
            is_mcq: Whether generating MCQ cards
            run_label: Optional user-provided label for the run
        """
        self.subject_config = subject_config
        self.is_mcq = is_mcq
        self.run_label = run_label
        self.run_id: Optional[str] = None
        self.card_generator: Optional[CardGenerator] = None

    @property
    def generation_mode(self) -> str:
        """Get the generation mode string."""
        if self.is_mcq:
            return f"{self.subject_config.name}_mcq"
        return self.subject_config.name

    @property
    def deck_prefix(self) -> str:
        """Get the appropriate deck prefix."""
        if self.is_mcq:
            return self.subject_config.deck_prefix_mcq
        return self.subject_config.deck_prefix

    async def initialize(self) -> bool:
        """
        Initialize database and providers.

        Returns:
            True if initialization successful, False otherwise.
        """
        # Initialize database
        logger.info(f"Initializing database at {DATABASE_PATH}")
        init_database(DATABASE_PATH)

        # Create run entry
        self.run_id = str(uuid.uuid4())
        session = get_session()
        create_run(
            session=session,
            id=self.run_id,
            user_label=self.run_label,
            mode=self.generation_mode,
            subject=self.subject_config.name,
            card_type="mcq" if self.is_mcq else "standard",
            status="running",
        )
        session.close()

        logger.info(f"Run ID: {self.run_id}")

        # Initialize providers
        llm_providers = await initialize_providers()
        if not llm_providers:
            session = get_session()
            update_run(session, self.run_id, status="failed")
            session.close()
            return False

        # Combiner is first provider
        combiner = llm_providers[0]
        llm_providers.remove(combiner)

        # Create repository for database operations
        repository = CardRepository(run_id=self.run_id)

        # Initialize generator with repository and combine_prompt from subject config
        self.card_generator = CardGenerator(
            providers=llm_providers,
            combiner=combiner,
            repository=repository,
            combine_prompt=self.subject_config.combine_prompt,
        )

        return True

    async def run(self) -> List[Dict]:
        """
        Execute the card generation workflow.

        Returns:
            List of generated problem dictionaries.
        """
        if self.card_generator is None:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        # Build question list with metadata
        questions_with_metadata: List[Tuple] = get_indexed_questions(
            self.subject_config.target_questions
        )

        # Process questions with concurrency control
        concurrency_semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
        all_generated_problems: List[Dict] = []

        async def process_question_with_semaphore(
            category_index: int,
            category_name: str,
            problem_index: int,
            question_text: str,
        ):
            async with concurrency_semaphore:
                generation_result = await self.card_generator.process_question(
                    question_text,
                    self.subject_config.initial_prompt,
                    self.subject_config.target_model,
                    category_index=category_index,
                    category_name=category_name,
                    problem_index=problem_index,
                )
                if generation_result:
                    all_generated_problems.append(generation_result)

        logger.info(f"Starting generation for {len(questions_with_metadata)} questions...")

        generation_tasks = [
            process_question_with_semaphore(
                category_index, category_name, problem_index, question_text
            )
            for category_index, category_name, problem_index, question_text in questions_with_metadata
        ]
        await asyncio.gather(*generation_tasks)

        # Update run status
        session = get_session()
        update_run(
            session=session,
            run_id=self.run_id,
            status="completed",
            total_problems=len(questions_with_metadata),
            successful_problems=len(all_generated_problems),
            failed_problems=len(questions_with_metadata) - len(all_generated_problems),
        )
        session.close()

        return all_generated_problems

    def save_results(self, problems: List[Dict]) -> Optional[str]:
        """
        Save generated problems to JSON file.

        Args:
            problems: List of generated problem dictionaries

        Returns:
            Output filename if saved, None if no problems to save.
        """
        if not problems:
            logger.warning("No cards generated.")
            return None

        output_filename = f"{self.generation_mode}_anki_deck"
        save_final_deck(problems, output_filename)

        logger.info(
            f"Run completed successfully! Run ID: {self.run_id}, "
            f"Database: {DATABASE_PATH}, Generated {len(problems)} problems, "
            f"Final deck: {output_filename}_<timestamp>.json"
        )

        return output_filename
