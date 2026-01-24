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
from src.task_runner import ConcurrentTaskRunner, Success, TaskInfo
from src.utils import save_final_deck
from src.questions import get_indexed_questions, filter_indexed_questions, QuestionFilter
from src.progress import ProgressTracker, ProviderStatus
from src.providers.base import TokenUsage


class Orchestrator:
    """Coordinates the card generation workflow."""

    def __init__(
        self,
        subject_config: SubjectConfig,
        is_mcq: bool = False,
        run_label: Optional[str] = None,
        dry_run: bool = False,
        bypass_cache_lookup: bool = False,
        resume_run_id: Optional[str] = None,
        question_filter: Optional[QuestionFilter] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            subject_config: Configuration for the subject/mode
            is_mcq: Whether generating MCQ cards
            run_label: Optional user-provided label for the run
            dry_run: If True, show what would be done without making changes
            bypass_cache_lookup: If True, skip cache lookup but still store results
            resume_run_id: Optional run ID to resume (skips already-processed questions)
            question_filter: Optional filter to limit which questions are processed
        """
        self.subject_config = subject_config
        self.is_mcq = is_mcq
        self.run_label = run_label
        self.dry_run = dry_run
        self.bypass_cache_lookup = bypass_cache_lookup
        self.resume_run_id = resume_run_id
        self.question_filter = question_filter
        self.run_repo = RunRepository(DATABASE_PATH)
        self.card_generator: Optional[CardGenerator] = None
        self.progress_tracker: Optional[ProgressTracker] = None
        self._llm_providers: List = []  # Store for progress tracking
        self._processed_questions: set[str] = set()  # For resume mode
        self._existing_results: List[Dict[str, Any]] = []  # For resume mode

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

    def _initialize_for_resume(self) -> bool:
        """
        Initialize for resume mode by loading existing run data.

        Returns:
            True if resume initialization successful, False otherwise.
        """
        if not self.resume_run_id:
            return False

        # Initialize database if not already initialized
        if not self.run_repo.db_manager.is_initialized:
            self.run_repo.initialize_database()

        # Load existing run
        run_data = self.run_repo.load_existing_run(self.resume_run_id)
        if not run_data:
            logger.error(f"Run not found: {self.resume_run_id}")
            return False

        # Validate run can be resumed
        if run_data["status"] == "completed":
            logger.error(
                f"Cannot resume completed run {run_data['id']}. "
                "Only 'failed' or 'running' runs can be resumed."
            )
            return False

        # Validate subject/mode match
        expected_mode = self.generation_mode
        if run_data["mode"] != expected_mode:
            logger.error(
                f"Mode mismatch: run {run_data['id']} has mode '{run_data['mode']}', "
                f"but current mode is '{expected_mode}'"
            )
            return False

        # Set the run ID and update status to running
        full_run_id = run_data["id"]
        self.run_repo.set_run_id(full_run_id)
        self.run_repo.update_run_status("running")

        # Load already-processed questions
        self._processed_questions = self.run_repo.get_processed_questions(full_run_id)
        self._existing_results = self.run_repo.get_existing_results(full_run_id)

        logger.info(f"Resuming run {full_run_id}")
        logger.info(
            f"Found {len(self._processed_questions)} already-processed questions, "
            f"{len(self._existing_results)} existing results"
        )

        return True

    async def initialize(self) -> bool:
        """
        Initialize database and providers.

        Returns:
            True if initialization successful, False otherwise.
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would initialize database and create run")
        elif self.resume_run_id:
            # Resume mode: load existing run
            if not self._initialize_for_resume():
                return False
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

        # Store providers for progress tracking
        self._llm_providers = llm_providers
        self._combiner = combiner
        self._formatter = formatter

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
        all_questions_with_metadata: List[Tuple] = get_indexed_questions(
            self.subject_config.target_questions
        )

        # Apply question filter if provided (before resume filter)
        if self.question_filter:
            all_questions_with_metadata = filter_indexed_questions(
                all_questions_with_metadata, self.question_filter
            )
            if not all_questions_with_metadata:
                logger.warning("No questions match the specified filters")
                return []

        # Filter out already-processed questions in resume mode
        if self._processed_questions:
            original_count = len(all_questions_with_metadata)
            questions_with_metadata = [
                q for q in all_questions_with_metadata
                if q[3] not in self._processed_questions  # q[3] is question name
            ]
            skipped = original_count - len(questions_with_metadata)
            logger.info(f"Resume mode: skipping {skipped} already-processed questions")
        else:
            questions_with_metadata = all_questions_with_metadata

        if self.dry_run:
            logger.info(f"[DRY RUN] Would process {len(questions_with_metadata)} questions")
            # Show first few questions as preview
            preview_count = min(5, len(questions_with_metadata))
            for cat_idx, cat_name, prob_idx, question in questions_with_metadata[:preview_count]:
                logger.info(f"[DRY RUN]   - {cat_name}/{question}")
            if len(questions_with_metadata) > preview_count:
                logger.info(f"[DRY RUN]   ... and {len(questions_with_metadata) - preview_count} more")
            return []

        # Handle case where all questions already processed
        if not questions_with_metadata:
            logger.info("All questions already processed. Nothing to do.")
            # In resume mode, return existing results
            if self._existing_results:
                self.run_repo.mark_run_completed(
                    RunStats(
                        total_problems=len(all_questions_with_metadata),
                        successful_problems=len(self._existing_results),
                        failed_problems=len(all_questions_with_metadata) - len(self._existing_results),
                    )
                )
                return self._existing_results
            return []

        # Collect all providers for progress tracking
        all_providers: List[Tuple[str, str]] = []
        for p in self._llm_providers:
            all_providers.append((p.name, p.model))
        if self._combiner:
            all_providers.append((self._combiner.name, self._combiner.model))
        if self._formatter and self._formatter != self._combiner:
            all_providers.append((self._formatter.name, self._formatter.model))

        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(
            total_questions=len(questions_with_metadata),
            provider_names=all_providers,
        )

        # Set up token usage callback for all providers
        def on_token_usage(provider_name: str, model: str, usage: TokenUsage, success: bool):
            if self.progress_tracker:
                status = ProviderStatus.SUCCESS if success else ProviderStatus.FAILED
                self.progress_tracker.update_provider_status(
                    provider_name=provider_name,
                    model=model,
                    status=status,
                    success=success,
                    tokens_input=usage.input_tokens,
                    tokens_output=usage.output_tokens,
                )

        # Wire up the callback to all providers
        for provider in self._llm_providers:
            if hasattr(provider, 'on_token_usage'):
                provider.on_token_usage = on_token_usage
        if hasattr(self._combiner, 'on_token_usage'):
            self._combiner.on_token_usage = on_token_usage  # type: ignore[union-attr]
        if self._formatter and hasattr(self._formatter, 'on_token_usage'):
            self._formatter.on_token_usage = on_token_usage  # type: ignore[union-attr]

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

        # Task names for progress display
        task_names = [question for _, _, _, question in questions_with_metadata]

        # Set up progress callbacks
        def on_task_start(info: TaskInfo):
            if self.progress_tracker:
                self.progress_tracker.start_question(info.name)

        def on_task_complete(info: TaskInfo, success: bool):
            if self.progress_tracker:
                self.progress_tracker.complete_question(
                    info.name,
                    success=success,
                    duration=info.duration,
                )

        # Start progress display
        self.progress_tracker.start()

        try:
            # Run with concurrency control and staggered request starts
            task_runner = ConcurrentTaskRunner(
                max_concurrent=self.concurrent_requests,
                request_delay=self.request_delay,
                on_task_start=on_task_start,
                on_task_complete=on_task_complete,
            )
            results = await task_runner.run_all(tasks, task_names=task_names)
        finally:
            # Stop progress display
            self.progress_tracker.stop()
            self.progress_tracker.print_summary()

        # Extract successful results
        newly_generated_problems: List[Dict[str, Any]] = []
        for result in results:
            if isinstance(result, Success) and result.value is not None:
                newly_generated_problems.append(result.value)  # type: ignore[arg-type]

        # In resume mode, merge with existing results
        if self._existing_results:
            all_generated_problems = self._existing_results + newly_generated_problems
            logger.info(
                f"Merged {len(self._existing_results)} existing + "
                f"{len(newly_generated_problems)} new = {len(all_generated_problems)} total problems"
            )
        else:
            all_generated_problems = newly_generated_problems

        # Calculate total problems across all questions (original + resumed)
        total_questions = len(all_questions_with_metadata)
        total_successful = len(all_generated_problems)

        # Update run status
        self.run_repo.mark_run_completed(
            RunStats(
                total_problems=total_questions,
                successful_problems=total_successful,
                failed_problems=total_questions - total_successful,
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

        resume_info = ""
        if self.resume_run_id:
            resume_info = f" (resumed from {self.resume_run_id[:8]}...)"

        logger.info(
            f"Run completed successfully{resume_info}! Run ID: {self.run_id}, "
            f"Database: {DATABASE_PATH}, Generated {len(problems)} problems, "
            f"Final deck: {output_filename}_<timestamp>.json"
        )

        return output_filename
