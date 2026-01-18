"""Repository pattern for database operations."""

import json
import logging
from typing import Dict, List, Optional, Any

from src.database import (
    get_session,
    create_problem,
    update_problem,
    create_provider_result,
    create_cards,
)

logger = logging.getLogger(__name__)


class CardRepository:
    """
    Repository for card generation database operations.

    Encapsulates all database access for the card generation workflow,
    providing a clean interface that decouples business logic from persistence.
    """

    def __init__(self, run_id: str):
        """
        Initialize the repository.

        Args:
            run_id: The ID of the current run.
        """
        self.run_id = run_id

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
        session = get_session()
        try:
            problem = create_problem(
                session=session,
                run_id=self.run_id,
                question_name=question_name,
                category_name=category_name,
                category_index=category_index,
                problem_index=problem_index,
                status="running",
            )
            return problem.id
        finally:
            session.close()

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
        session = get_session()
        try:
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
        finally:
            session.close()

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
        session = get_session()
        try:
            update_problem(
                session=session,
                problem_id=problem_id,
                status="failed",
                processing_time_seconds=processing_time_seconds,
            )
        finally:
            session.close()

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
        session = get_session()
        try:
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
        finally:
            session.close()
