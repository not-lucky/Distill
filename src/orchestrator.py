"""Orchestrator for LLM2Deck card generation workflow."""

import logging
from typing import Any, List, Dict, Optional, Tuple

from src.config import DATABASE_PATH
from src.config.loader import load_config

logger = logging.getLogger(__name__)
from src.config.subjects import SubjectConfig
from src.setup import initialize_providers
from src.generator import CardGenerator
from src.repositories import RunRepository, RunStats
from src.task_runner import ConcurrentTaskRunner, Success
from src.utils import save_final_deck
from src.questions import get_indexed_questions


class Orchestrator:
    """Coordinates the card generation workflow."""

    def __init__(
        self,
        subject_config: SubjectConfig,
        is_mcq: bool = False,
        run_label: Optional[str] = None,
        dry_run: bool = False,
        bypass_cache_lookup: bool = False,
    ):
        """
        Initialize the orchestrator.

        Args:
            subject_config: Configuration for the subject/mode
            is_mcq: Whether generating MCQ cards
            run_label: Optional user-provided label for the run
            dry_run: If True, show what would be done without making changes
            bypass_cache_lookup: If True, skip cache lookup but still store results
        """
        self.subject_config = subject_config
        self.is_mcq = is_mcq
        self.run_label = run_label
        self.dry_run = dry_run
        self.bypass_cache_lookup = bypass_cache_lookup
        self.run_repo = RunRepository(DATABASE_PATH)
        self.card_generator: Optional[CardGenerator] = None

        # Load generation config
        config = load_config()
        self.concurrent_requests = config.generation.concurrent_requests
        self.request_delay = config.generation.request_delay

    @property
    def run_id(self) -> Optional[str]:
        """Get the current run ID."""
        return self.run_repo.run_id

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
        if self.dry_run:
            logger.info("[DRY RUN] Would initialize database and create run")
        else:
            # Initialize database and create run
            self.run_repo.initialize_database()
            self.run_repo.create_new_run(
                mode=self.generation_mode,
                subject=self.subject_config.name,
                card_type="mcq" if self.is_mcq else "standard",
                user_label=self.run_label,
            )
            logger.info(f"Run ID: {self.run_id}")

        # Initialize providers - returns (generators, combiner, formatter)
        llm_providers, combiner, formatter = await initialize_providers()

        # Apply bypass_cache_lookup setting to all providers
        if self.bypass_cache_lookup:
            for provider in llm_providers:
                if hasattr(provider, 'bypass_cache_lookup'):
                    setattr(provider, 'bypass_cache_lookup', True)
            if combiner and hasattr(combiner, 'bypass_cache_lookup'):
                setattr(combiner, 'bypass_cache_lookup', True)
            if formatter and hasattr(formatter, 'bypass_cache_lookup'):
                setattr(formatter, 'bypass_cache_lookup', True)

        # If no explicit combiner configured, use first provider as combiner
        if combiner is None:
            if not llm_providers:
                if not self.dry_run:
                    self.run_repo.mark_run_failed()
                return False
            combiner = llm_providers[0]
            llm_providers = llm_providers[1:]

        # Need at least the combiner to function
        if combiner is None:
            if not self.dry_run:
                self.run_repo.mark_run_failed()
            return False

        if self.dry_run:
            logger.info(f"[DRY RUN] Combiner: {combiner.name} ({combiner.model})")
            if formatter:
                logger.info(f"[DRY RUN] Formatter: {formatter.name} ({formatter.model})")
            logger.info(f"[DRY RUN] Generators: {[(p.name, p.model) for p in llm_providers]}")

        # Get repository for card operations (None in dry run mode)
        repository = None if self.dry_run else self.run_repo.get_card_repository()

        # Initialize generator with repository and combine_prompt from subject config
        self.card_generator = CardGenerator(
            providers=llm_providers,
            combiner=combiner,
            formatter=formatter,
            repository=repository,
            combine_prompt=self.subject_config.combine_prompt,
            dry_run=self.dry_run,
        )

        return True

    async def run(self) -> List[Dict[str, Any]]:
        """
        Execute the card generation workflow.

        Returns:
            List of generated problem dictionaries.
        """
        if self.card_generator is None:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        # Capture card_generator locally to help type checker
        card_generator = self.card_generator

        # Build question list with metadata
        questions_with_metadata: List[Tuple] = get_indexed_questions(
            self.subject_config.target_questions
        )

        if self.dry_run:
            logger.info(f"[DRY RUN] Would process {len(questions_with_metadata)} questions")
            # Show first few questions as preview
            preview_count = min(5, len(questions_with_metadata))
            for cat_idx, cat_name, prob_idx, question in questions_with_metadata[:preview_count]:
                logger.info(f"[DRY RUN]   - {cat_name}/{question}")
            if len(questions_with_metadata) > preview_count:
                logger.info(f"[DRY RUN]   ... and {len(questions_with_metadata) - preview_count} more")
            return []

        logger.info(f"Starting generation for {len(questions_with_metadata)} questions...")

        # Create task functions for each question
        def make_task(cat_idx: int, cat_name: str, prob_idx: int, question: str):
            async def task():
                return await card_generator.process_question(
                    question,
                    self.subject_config.initial_prompt,
                    self.subject_config.target_model,
                    category_index=cat_idx,
                    category_name=cat_name,
                    problem_index=prob_idx,
                )
            return task

        tasks = [
            make_task(cat_idx, cat_name, prob_idx, question)
            for cat_idx, cat_name, prob_idx, question in questions_with_metadata
        ]

        # Run with concurrency control and staggered request starts
        task_runner = ConcurrentTaskRunner(
            max_concurrent=self.concurrent_requests,
            request_delay=self.request_delay,
        )
        results = await task_runner.run_all(tasks)

        # Extract successful results
        all_generated_problems: List[Dict[str, Any]] = []
        for result in results:
            if isinstance(result, Success) and result.value is not None:
                all_generated_problems.append(result.value)  # type: ignore[arg-type]

        # Update run status
        self.run_repo.mark_run_completed(
            RunStats(
                total_problems=len(questions_with_metadata),
                successful_problems=len(all_generated_problems),
                failed_problems=len(questions_with_metadata) - len(all_generated_problems),
            )
        )

        return all_generated_problems

    def save_results(self, problems: List[Dict[str, Any]]) -> Optional[str]:
        """
        Save generated problems to JSON file.

        Args:
            problems: List of generated problem dictionaries

        Returns:
            Output filename if saved, None if no problems to save.
        """
        output_filename = f"{self.generation_mode}_anki_deck"

        if self.dry_run:
            if problems:
                logger.info(f"[DRY RUN] Would save {len(problems)} problems to {output_filename}_<timestamp>.json")
            else:
                logger.info(f"[DRY RUN] Would save results to {output_filename}_<timestamp>.json")
            return output_filename

        if not problems:
            logger.warning("No cards generated.")
            return None

        save_final_deck(problems, output_filename)

        logger.info(
            f"Run completed successfully! Run ID: {self.run_id}, "
            f"Database: {DATABASE_PATH}, Generated {len(problems)} problems, "
            f"Final deck: {output_filename}_<timestamp>.json"
        )

        return output_filename
