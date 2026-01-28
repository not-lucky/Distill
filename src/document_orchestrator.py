"""Document ingestion orchestrator for LLM2Deck."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import DATABASE_PATH
from src.config.loader import load_config
from src.document import (
    DocumentInfo,
    discover_documents,
    get_document_count,
    SUPPORTED_EXTENSIONS,
)
from src.generator import CardGenerator
from src.models import DocumentProblem
from src.progress import ProgressTracker, ProviderStatus
from src.prompts import PromptLoader
from src.providers.base import TokenUsage
from src.repositories import RunRepository, RunStats, RunCostData
from src.services.cost import CostEstimator, CostEstimate
from src.setup import initialize_providers
from src.task_runner import ConcurrentTaskRunner, Success, TaskInfo
from src.utils import save_final_deck

logger = logging.getLogger(__name__)


class DocumentOrchestrator:
    """Coordinates document-based card generation workflow."""

    def __init__(
        self,
        source_dir: Path,
        deck_name: Optional[str] = None,
        run_label: Optional[str] = None,
        dry_run: bool = False,
        bypass_cache_lookup: bool = False,
        budget_limit_usd: Optional[float] = None,
        estimate_only: bool = False,
        extensions: Optional[set] = None,
    ):
        """
        Initialize the document orchestrator.

        Args:
            source_dir: Directory containing documents to process
            deck_name: Override the deck name (default: derived from source_dir name)
            run_label: Optional user-provided label for the run
            dry_run: If True, show what would be done without making changes
            bypass_cache_lookup: If True, skip cache lookup but still store results
            budget_limit_usd: Optional maximum budget in USD
            estimate_only: If True, show cost estimate and exit without generating
            extensions: Set of file extensions to process (default: .md, .txt, .rst, .html)
        """
        self.source_dir = Path(source_dir).resolve()
        self.deck_name_override = deck_name
        self.run_label = run_label
        self.dry_run = dry_run
        self.bypass_cache_lookup = bypass_cache_lookup
        self.budget_limit_usd = budget_limit_usd
        self.estimate_only = estimate_only
        self.extensions = extensions or SUPPORTED_EXTENSIONS

        self.run_repo = RunRepository(DATABASE_PATH)
        self.card_generator: Optional[CardGenerator] = None
        self.progress_tracker: Optional[ProgressTracker] = None
        self._llm_providers: List = []
        self._combiner = None
        self._formatter = None

        # Load prompts
        self.prompt_loader = PromptLoader()
        prompts_dir = self.prompt_loader.prompts_dir / "document"
        self.initial_prompt = (prompts_dir / "initial.md").read_text(encoding="utf-8")
        self.combine_prompt = (prompts_dir / "combine.md").read_text(encoding="utf-8")

        # Cost tracking
        self.cost_estimator = CostEstimator()
        self._current_cost_usd: float = 0.0
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._budget_exceeded: bool = False

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
        return "document"

    @property
    def deck_prefix(self) -> str:
        """Get the deck prefix for Anki."""
        if self.deck_name_override:
            return self.deck_name_override
        # Derive from source directory name
        from src.document import _dirname_to_deck_name
        return _dirname_to_deck_name(self.source_dir.name)

    async def initialize(self) -> bool:
        """
        Initialize database and providers.

        Returns:
            True if initialization successful, False otherwise.
        """
        # Validate source directory
        if not self.source_dir.exists():
            logger.error(f"Source directory not found: {self.source_dir}")
            return False

        if not self.source_dir.is_dir():
            logger.error(f"Source path is not a directory: {self.source_dir}")
            return False

        # Check for documents
        doc_count = get_document_count(self.source_dir, self.extensions)
        if doc_count == 0:
            logger.error(
                f"No documents found in {self.source_dir} "
                f"(supported extensions: {', '.join(sorted(self.extensions))})"
            )
            return False

        if self.dry_run or self.estimate_only:
            logger.info("[DRY RUN] Would initialize database and create run")
        else:
            # Initialize database and create run
            self.run_repo.initialize_database()
            self.run_repo.create_new_run(
                mode=self.generation_mode,
                subject="document",
                card_type="standard",
                user_label=self.run_label,
            )
            logger.info(f"Run ID: {self.run_id}")

            if self.budget_limit_usd is not None:
                self.run_repo.set_budget_limit(self.budget_limit_usd)

        # Initialize providers
        llm_providers, combiner, formatter = await initialize_providers()

        # Apply bypass_cache_lookup setting
        if self.bypass_cache_lookup:
            for provider in llm_providers:
                if hasattr(provider, "bypass_cache_lookup"):
                    setattr(provider, "bypass_cache_lookup", True)
            if combiner and hasattr(combiner, "bypass_cache_lookup"):
                setattr(combiner, "bypass_cache_lookup", True)
            if formatter and hasattr(formatter, "bypass_cache_lookup"):
                setattr(formatter, "bypass_cache_lookup", True)

        # If no explicit combiner, use first provider
        if combiner is None:
            if not llm_providers:
                if not self.dry_run:
                    self.run_repo.mark_run_failed()
                return False
            combiner = llm_providers[0]
            llm_providers = llm_providers[1:]

        if combiner is None:
            if not self.dry_run:
                self.run_repo.mark_run_failed()
            return False

        self._llm_providers = llm_providers
        self._combiner = combiner
        self._formatter = formatter

        if self.dry_run or self.estimate_only:
            logger.info(f"[DRY RUN] Combiner: {combiner.name} ({combiner.model})")
            if formatter:
                logger.info(f"[DRY RUN] Formatter: {formatter.name} ({formatter.model})")
            logger.info(f"[DRY RUN] Generators: {[(p.name, p.model) for p in llm_providers]}")

        # Get repository for card operations (None in dry run or estimate-only mode)
        repository = None if (self.dry_run or self.estimate_only) else self.run_repo.get_card_repository()

        # Initialize generator with document-specific combine prompt
        self.card_generator = CardGenerator(
            providers=llm_providers,
            combiner=combiner,
            formatter=formatter,
            repository=repository,
            combine_prompt=self.combine_prompt,
            dry_run=self.dry_run or self.estimate_only,
        )

        return True

    def _get_all_provider_tuples(self) -> List[Tuple[str, str]]:
        """Get list of (provider_name, model) tuples for all providers."""
        all_providers: List[Tuple[str, str]] = []
        for p in self._llm_providers:
            all_providers.append((p.name, p.model))
        if self._combiner:
            all_providers.append((self._combiner.name, self._combiner.model))
        if self._formatter and self._formatter != self._combiner:
            all_providers.append((self._formatter.name, self._formatter.model))
        return all_providers

    def _display_cost_estimate(self, estimate: CostEstimate) -> None:
        """Display cost estimate to the user."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("COST ESTIMATE")
        logger.info("=" * 60)
        logger.info(f"Documents to process: {estimate.total_questions}")
        logger.info(
            f"Estimated tokens: {estimate.estimated_input_tokens:,} in / "
            f"{estimate.estimated_output_tokens:,} out"
        )
        logger.info(f"Estimated total cost: ${estimate.total_estimated_cost_usd:.4f}")
        logger.info("")
        logger.info("Per provider:")
        for provider in estimate.providers:
            logger.info(
                f"  {provider.provider_name}/{provider.model}: "
                f"${provider.estimated_cost_usd:.4f}"
            )
        logger.info("=" * 60)
        if self.budget_limit_usd is not None:
            logger.info(f"Budget limit: ${self.budget_limit_usd:.2f}")
            if estimate.total_estimated_cost_usd > self.budget_limit_usd:
                logger.warning(
                    f"⚠️  Estimated cost (${estimate.total_estimated_cost_usd:.4f}) "
                    f"exceeds budget (${self.budget_limit_usd:.2f})"
                )
        logger.info("")

    def _get_cost_data(self) -> RunCostData:
        """Build RunCostData from current tracking state."""
        return RunCostData(
            total_input_tokens=self._total_input_tokens,
            total_output_tokens=self._total_output_tokens,
            total_estimated_cost_usd=self._current_cost_usd,
            budget_limit_usd=self.budget_limit_usd,
            budget_exceeded=self._budget_exceeded,
        )

    def _build_document_prompt(self, doc: DocumentInfo) -> str:
        """Build the initial prompt for a document."""
        import json
        json_schema = json.dumps(DocumentProblem.model_json_schema(), indent=2)
        
        prompt = self.initial_prompt
        prompt = prompt.replace("{title}", doc.title)
        prompt = prompt.replace("{topic_path}", doc.topic_path)
        prompt = prompt.replace("{document_content}", doc.content)
        prompt = prompt.replace("{schema}", json_schema)
        return prompt

    async def run(self) -> List[Dict[str, Any]]:
        """
        Execute the document ingestion workflow.

        Returns:
            List of generated problem dictionaries.
        """
        if self.card_generator is None:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        card_generator = self.card_generator

        # Discover all documents
        documents = list(discover_documents(self.source_dir, self.extensions))

        # Apply deck name override if provided
        if self.deck_name_override:
            for doc in documents:
                doc.deck_name = self.deck_name_override

        if not documents:
            logger.warning("No documents found to process")
            return []

        # Get provider tuples for cost estimation
        all_providers = self._get_all_provider_tuples()

        # Show cost estimate
        cost_estimate = self.cost_estimator.estimate_run_cost(
            providers=all_providers,
            question_count=len(documents),
        )
        self._display_cost_estimate(cost_estimate)

        # Handle estimate-only mode
        if self.estimate_only:
            logger.info("[ESTIMATE ONLY] Exiting without generating cards")
            return []

        if self.dry_run:
            logger.info(f"[DRY RUN] Would process {len(documents)} documents")
            logger.info(f"[DRY RUN] Deck structure preview:")
            for doc in documents[:10]:
                logger.info(f"[DRY RUN]   {doc.full_deck_path}")
                logger.info(f"[DRY RUN]     <- {doc.relative_path}")
            if len(documents) > 10:
                logger.info(f"[DRY RUN]   ... and {len(documents) - 10} more documents")
            return []

        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(
            total_questions=len(documents),
            provider_names=all_providers,
        )

        # Set up token usage callback
        def on_token_usage(provider_name: str, model: str, usage: TokenUsage, success: bool):
            self._total_input_tokens += usage.input_tokens
            self._total_output_tokens += usage.output_tokens
            cost = self.cost_estimator.calculate_cost(
                provider_name, usage.input_tokens, usage.output_tokens
            )
            self._current_cost_usd += cost

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

        # Wire up callbacks
        for provider in self._llm_providers:
            if hasattr(provider, "on_token_usage"):
                provider.on_token_usage = on_token_usage
        if hasattr(self._combiner, "on_token_usage"):
            self._combiner.on_token_usage = on_token_usage
        if self._formatter and hasattr(self._formatter, "on_token_usage"):
            self._formatter.on_token_usage = on_token_usage

        logger.info(f"Starting generation for {len(documents)} documents...")

        # Create task functions for each document
        def make_task(doc: DocumentInfo, doc_idx: int):
            async def task():
                # Build custom prompt with document content
                custom_prompt = self._build_document_prompt(doc)

                result = await card_generator.process_question(
                    question=doc.title,
                    prompt_template=custom_prompt,
                    model_class=DocumentProblem,
                    category_index=doc_idx,
                    category_name=doc.full_deck_path,
                    problem_index=0,
                )

                # Add source file info to result
                if result:
                    result["source_file"] = str(doc.file_path)
                    result["deck_path"] = doc.full_deck_path

                return result

            return task

        tasks = [make_task(doc, idx) for idx, doc in enumerate(documents, 1)]
        task_names = [doc.full_deck_path for doc in documents]

        # Set up progress callbacks
        def on_task_start(info: TaskInfo):
            if self.progress_tracker:
                self.progress_tracker.start_question(info.name)

        def on_task_complete(info: TaskInfo, success: bool):
            if self.progress_tracker:
                self.progress_tracker.complete_question(
                    info.name, success=success, duration=info.duration
                )

        # Start progress display
        self.progress_tracker.start()

        try:
            task_runner = ConcurrentTaskRunner(
                max_concurrent=self.concurrent_requests,
                request_delay=self.request_delay,
                on_task_start=on_task_start,
                on_task_complete=on_task_complete,
            )
            results = await task_runner.run_all(tasks, task_names=task_names)
        finally:
            self.progress_tracker.stop()
            self.progress_tracker.print_summary()

        # Extract successful results
        generated_problems: List[Dict[str, Any]] = []
        for result in results:
            if isinstance(result, Success) and result.value is not None:
                generated_problems.append(result.value)

        # Update run status
        self.run_repo.mark_run_completed(
            RunStats(
                total_problems=len(documents),
                successful_problems=len(generated_problems),
                failed_problems=len(documents) - len(generated_problems),
            ),
            cost_data=self._get_cost_data(),
        )

        # Log cost summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("ACTUAL COST SUMMARY")
        logger.info("=" * 60)
        logger.info(
            f"Total tokens: {self._total_input_tokens:,} in / "
            f"{self._total_output_tokens:,} out"
        )
        logger.info(f"Total cost: ${self._current_cost_usd:.4f}")
        if self.budget_limit_usd is not None:
            remaining = self.budget_limit_usd - self._current_cost_usd
            logger.info(f"Budget remaining: ${remaining:.4f}")
        logger.info("=" * 60)

        return generated_problems

    def save_results(self, problems: List[Dict[str, Any]]) -> Optional[str]:
        """
        Save generated problems to JSON file.

        Args:
            problems: List of generated problem dictionaries

        Returns:
            Output filename if saved, None if no problems to save.
        """
        output_filename = f"document_{self.deck_prefix}_anki_deck"

        if self.estimate_only:
            return None

        if self.dry_run:
            if problems:
                logger.info(
                    f"[DRY RUN] Would save {len(problems)} problems to "
                    f"{output_filename}_<timestamp>.json"
                )
            else:
                logger.info(
                    f"[DRY RUN] Would save results to {output_filename}_<timestamp>.json"
                )
            return output_filename

        if not problems:
            logger.warning("No cards generated.")
            return None

        save_final_deck(problems, output_filename)

        cost_info = ""
        if self._current_cost_usd > 0:
            cost_info = f", Cost: ${self._current_cost_usd:.4f}"

        logger.info(
            f"Run completed successfully! Run ID: {self.run_id}, "
            f"Database: {DATABASE_PATH}, Generated {len(problems)} problems{cost_info}, "
            f"Final deck: {output_filename}_<timestamp>.json"
        )

        return output_filename
