"""Repository pattern for database operations."""

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.database import (
    DatabaseManager,
    create_run,
    update_run,
    create_problem,
    update_problem,
    create_provider_result,
    create_cards,
)

logger = logging.getLogger(__name__)


@dataclass
class RunStats:
    """Statistics for a completed run."""

    total_problems: int
    successful_problems: int
    failed_problems: int


class RunRepository:
    """
    Repository for run lifecycle operations.

    Encapsulates database initialization and run management,
    providing a clean interface for the orchestrator.
    """

    def __init__(
        self,
        db_path: Path,
        db_manager: Optional[DatabaseManager] = None,
    ):
        """
        Initialize the repository.

        Args:
            db_path: Path to the SQLite database file.
            db_manager: Optional DatabaseManager instance for dependency injection.
                       If None, uses the default singleton.
        """
        self.db_path = db_path
        self._db_manager = db_manager
        self._run_id: Optional[str] = None

    @property
    def db_manager(self) -> DatabaseManager:
        """Get the database manager, using default if not explicitly set."""
        if self._db_manager is not None:
            return self._db_manager
        return DatabaseManager.get_default()

    @property
    def run_id(self) -> Optional[str]:
        """Get the current run ID."""
        return self._run_id

    def initialize_database(self) -> None:
        """Initialize the database and create tables if needed."""
        self.db_manager.initialize(self.db_path)

    def create_new_run(
        self,
        mode: str,
        subject: str,
        card_type: str,
        user_label: Optional[str] = None,
    ) -> str:
        """
        Create a new run entry in the database.

        Args:
            mode: Generation mode (e.g., "leetcode", "cs_mcq").
            subject: Subject name (e.g., "leetcode", "cs").
            card_type: Card type ("standard" or "mcq").
            user_label: Optional user-provided label.

        Returns:
            The generated run ID.
        """
        self._run_id = str(uuid.uuid4())
        with self.db_manager.session_scope() as session:
            create_run(
                session=session,
                id=self._run_id,
                user_label=user_label,
                mode=mode,
                subject=subject,
                card_type=card_type,
                status="running",
            )
        return self._run_id

    def mark_run_failed(self) -> None:
        """Mark the current run as failed."""
        if not self._run_id:
            raise RuntimeError("No active run to mark as failed")

        with self.db_manager.session_scope() as session:
            update_run(session, self._run_id, status="failed")
        logger.info(f"Marked run {self._run_id} as failed")

    def mark_run_completed(self, stats: RunStats) -> None:
        """
        Mark the current run as completed with statistics.

        Args:
            stats: Run statistics including problem counts.
        """
        if not self._run_id:
            raise RuntimeError("No active run to mark as completed")

        with self.db_manager.session_scope() as session:
            update_run(
                session=session,
                run_id=self._run_id,
                status="completed",
                total_problems=stats.total_problems,
                successful_problems=stats.successful_problems,
                failed_problems=stats.failed_problems,
            )
        logger.info(f"Marked run {self._run_id} as completed")

    def get_card_repository(self) -> "CardRepository":
        """
        Get a CardRepository for the current run.

        Returns:
            CardRepository instance bound to this run.

        Raises:
            RuntimeError: If no run has been created yet.
        """
        if not self._run_id:
            raise RuntimeError("No active run. Call create_new_run() first.")
        return CardRepository(run_id=self._run_id, db_manager=self._db_manager)

    def set_run_id(self, run_id: str) -> None:
        """
        Set the run ID for resume mode.

        Args:
            run_id: The existing run ID to resume.
        """
        self._run_id = run_id

    def load_existing_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Load an existing run by ID for resumption.

        Args:
            run_id: The run ID (can be partial, will match prefix).

        Returns:
            Dictionary with run metadata, or None if not found.
        """
        from src.queries import get_run_by_id

        run = get_run_by_id(run_id)
        if not run:
            return None

        return {
            "id": run.id,
            "mode": run.mode,
            "subject": run.subject,
            "card_type": run.card_type,
            "status": run.status,
            "user_label": run.user_label,
            "total_problems": run.total_problems,
            "successful_problems": run.successful_problems,
            "failed_problems": run.failed_problems,
        }

    def get_processed_questions(self, run_id: str) -> set[str]:
        """
        Get set of question names that were successfully processed in a run.

        Args:
            run_id: The run ID.

        Returns:
            Set of question names that completed successfully.
        """
        from src.queries import get_successful_questions_for_run

        return set(get_successful_questions_for_run(run_id))

    def get_existing_results(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get existing successful results from a run.

        Args:
            run_id: The run ID.

        Returns:
            List of card data dictionaries from successful problems.
        """
        from src.queries import get_successful_problems_with_results

        return get_successful_problems_with_results(run_id)

    def update_run_status(self, status: str) -> None:
        """
        Update the status of the current run.

        Args:
            status: New status ("running", "completed", "failed").
        """
        if not self._run_id:
            raise RuntimeError("No active run to update")

        with self.db_manager.session_scope() as session:
            update_run(session, self._run_id, status=status)
        logger.info(f"Updated run {self._run_id} status to {status}")


class CardRepository:
    """
    Repository for card generation database operations.

    Encapsulates all database access for the card generation workflow,
    providing a clean interface that decouples business logic from persistence.
    """

    def __init__(
        self,
        run_id: str,
        db_manager: Optional[DatabaseManager] = None,
    ):
        """
        Initialize the repository.

        Args:
            run_id: The ID of the current run.
            db_manager: Optional DatabaseManager instance for dependency injection.
                       If None, uses the default singleton.
        """
        self.run_id = run_id
        self._db_manager = db_manager

    @property
    def db_manager(self) -> DatabaseManager:
        """Get the database manager, using default if not explicitly set."""
        if self._db_manager is not None:
            return self._db_manager
        return DatabaseManager.get_default()

    def create_initial_problem(
        self,
        question_name: str,
        category_name: Optional[str] = None,
        category_index: Optional[int] = None,
        problem_index: Optional[int] = None,
    ) -> int:
        """
        Create a new problem entry in the database.

        Args:
            question_name: The name of the question/problem.
            category_name: Optional category name.
            category_index: Optional 1-based category index.
            problem_index: Optional 1-based problem index within category.

        Returns:
            The ID of the created problem.
        """
        with self.db_manager.session_scope() as session:
            problem = create_problem(
                session=session,
                run_id=self.run_id,
                question_name=question_name,
                category_name=category_name,
                category_index=category_index,
                problem_index=problem_index,
                status="running",
            )
            # problem.id is an int Column, cast to int for return type
            return int(problem.id)  # type: ignore[arg-type]

    def save_provider_result(
        self,
        problem_id: int,
        provider_name: str,
        provider_model: str,
        raw_output: str,
        card_count: Optional[int] = None,
    ) -> None:
        """
        Save a provider's generation result to the database.

        Args:
            problem_id: ID of the problem this result belongs to.
            provider_name: Name of the provider.
            provider_model: Model used by the provider.
            raw_output: Raw JSON string output from the provider.
            card_count: Optional count of cards in the result.
        """
        with self.db_manager.session_scope() as session:
            create_provider_result(
                session=session,
                problem_id=problem_id,
                run_id=self.run_id,
                provider_name=provider_name,
                provider_model=provider_model,
                success=True,
                raw_output=raw_output,
                card_count=card_count,
            )

    def update_problem_failed(
        self,
        problem_id: int,
        processing_time_seconds: float,
    ) -> None:
        """
        Mark a problem as failed.

        Args:
            problem_id: ID of the problem to update.
            processing_time_seconds: Time spent processing before failure.
        """
        with self.db_manager.session_scope() as session:
            update_problem(
                session=session,
                problem_id=problem_id,
                status="failed",
                processing_time_seconds=processing_time_seconds,
            )

    def save_final_result(
        self,
        problem_id: int,
        card_data: Dict[str, Any],
        processing_time_seconds: float,
    ) -> None:
        """
        Save the final combined result to the database.

        Args:
            problem_id: ID of the problem.
            card_data: Final card data dictionary.
            processing_time_seconds: Total processing time.
        """
        with self.db_manager.session_scope() as session:
            # Update problem with final result
            update_problem(
                session=session,
                problem_id=problem_id,
                status="success",
                final_result=json.dumps(card_data),
                final_card_count=len(card_data.get("cards", [])),
                processing_time_seconds=processing_time_seconds,
            )

            # Save individual cards
            create_cards(
                session=session,
                problem_id=problem_id,
                run_id=self.run_id,
                cards_data=card_data.get("cards", []),
            )

        logger.info(
            f"Saved {len(card_data.get('cards', []))} cards to database for problem {problem_id}"
        )
