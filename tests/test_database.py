"""Tests for DatabaseManager and CRUD operations in src/database.py."""

import json
import pytest
from pathlib import Path
from datetime import datetime

from src.database import (
    DatabaseManager,
    Base,
    Run,
    Problem,
    ProviderResult,
    Card,
    create_run,
    update_run,
    create_problem,
    update_problem,
    create_provider_result,
    create_cards,
    get_run,
    get_problem,
)


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    def test_init_without_path(self):
        """Test DatabaseManager initialization without path."""
        manager = DatabaseManager()
        assert manager.is_initialized is False
        assert manager.db_path is None

    def test_init_with_path(self, tmp_path):
        """Test DatabaseManager initialization with path."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(db_path)
        assert manager.is_initialized is True
        assert manager.db_path == db_path

    def test_initialize(self, tmp_path):
        """Test explicit initialization."""
        manager = DatabaseManager()
        db_path = tmp_path / "test.db"
        manager.initialize(db_path)
        assert manager.is_initialized is True
        assert manager.db_path == db_path

    def test_initialize_in_memory(self):
        """Test initialization with in-memory database."""
        manager = DatabaseManager()
        manager.initialize(Path(":memory:"))
        assert manager.is_initialized is True

    def test_get_session_before_init_raises(self):
        """Test that get_session raises before initialization."""
        manager = DatabaseManager()
        with pytest.raises(RuntimeError, match="not initialized"):
            manager.get_session()

    def test_get_session_after_init(self, in_memory_db):
        """Test getting a session after initialization."""
        session = in_memory_db.get_session()
        assert session is not None
        session.close()

    def test_session_scope_commits(self, in_memory_db):
        """Test that session_scope commits on success."""
        with in_memory_db.session_scope() as session:
            run = Run(
                id="test-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
                status="running"
            )
            session.add(run)

        # Verify the run was committed
        with in_memory_db.session_scope() as session:
            result = session.query(Run).filter(Run.id == "test-run").first()
            assert result is not None
            assert result.mode == "leetcode"

    def test_session_scope_rollback_on_error(self, in_memory_db):
        """Test that session_scope rolls back on error."""
        try:
            with in_memory_db.session_scope() as session:
                run = Run(
                    id="test-run-2",
                    mode="leetcode",
                    subject="leetcode",
                    card_type="standard",
                    status="running"
                )
                session.add(run)
                raise ValueError("Intentional error")
        except ValueError:
            pass

        # Verify the run was NOT committed
        with in_memory_db.session_scope() as session:
            result = session.query(Run).filter(Run.id == "test-run-2").first()
            assert result is None


class TestSingletonPattern:
    """Tests for DatabaseManager singleton pattern."""

    def test_get_default_creates_instance(self):
        """Test that get_default creates a new instance."""
        DatabaseManager.reset_default()
        manager = DatabaseManager.get_default()
        assert manager is not None
        DatabaseManager.reset_default()

    def test_get_default_returns_same_instance(self):
        """Test that get_default returns the same instance."""
        DatabaseManager.reset_default()
        manager1 = DatabaseManager.get_default()
        manager2 = DatabaseManager.get_default()
        assert manager1 is manager2
        DatabaseManager.reset_default()

    def test_set_default(self):
        """Test setting the default manager."""
        DatabaseManager.reset_default()
        custom_manager = DatabaseManager()
        DatabaseManager.set_default(custom_manager)
        assert DatabaseManager.get_default() is custom_manager
        DatabaseManager.reset_default()

    def test_reset_default(self):
        """Test resetting the default manager."""
        DatabaseManager.reset_default()
        manager1 = DatabaseManager.get_default()
        DatabaseManager.reset_default()
        manager2 = DatabaseManager.get_default()
        assert manager1 is not manager2
        DatabaseManager.reset_default()


class TestRunCRUD:
    """Tests for Run CRUD operations."""

    def test_create_run(self, in_memory_db):
        """Test creating a run."""
        with in_memory_db.session_scope() as session:
            run = create_run(
                session=session,
                id="test-run-id",
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
                user_label="test label"
            )
            assert run.id == "test-run-id"
            assert run.mode == "leetcode"
            assert run.subject == "leetcode"
            assert run.card_type == "standard"
            assert run.user_label == "test label"
            assert run.status == "running"

    def test_create_run_with_metadata(self, in_memory_db):
        """Test creating a run with metadata."""
        metadata = {"key": "value", "count": 42}
        with in_memory_db.session_scope() as session:
            run = create_run(
                session=session,
                id="test-metadata",
                mode="cs",
                subject="cs",
                card_type="mcq",
                run_metadata=metadata
            )
            assert run.run_metadata is not None
            parsed = json.loads(run.run_metadata)
            assert parsed == metadata

    def test_update_run(self, in_memory_db):
        """Test updating a run."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="update-test",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            updated = update_run(
                session,
                "update-test",
                status="completed",
                total_problems=10,
                successful_problems=8,
                failed_problems=2
            )
            assert updated.status == "completed"
            assert updated.total_problems == 10
            assert updated.successful_problems == 8
            assert updated.failed_problems == 2
            assert updated.completed_at is not None

    def test_update_run_not_found(self, in_memory_db):
        """Test updating a non-existent run raises error."""
        with pytest.raises(ValueError, match="Run not found"):
            with in_memory_db.session_scope() as session:
                update_run(session, "nonexistent", status="completed")

    def test_get_run(self, in_memory_db):
        """Test getting a run by ID."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="get-test",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            run = get_run(session, "get-test")
            assert run is not None
            assert run.id == "get-test"

    def test_get_run_not_found(self, in_memory_db):
        """Test getting a non-existent run returns None."""
        with in_memory_db.session_scope() as session:
            run = get_run(session, "nonexistent")
            assert run is None


class TestProblemCRUD:
    """Tests for Problem CRUD operations."""

    def test_create_problem(self, in_memory_db):
        """Test creating a problem."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="problem-test-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(
                session=session,
                run_id="problem-test-run",
                question_name="Two Sum",
                category_name="Arrays",
                category_index=1,
                problem_index=1
            )
            assert problem.id is not None
            assert problem.question_name == "Two Sum"
            assert problem.sanitized_name == "two_sum"
            assert problem.category_name == "Arrays"
            assert problem.category_index == 1
            assert problem.problem_index == 1
            assert problem.status == "running"

    def test_update_problem(self, in_memory_db):
        """Test updating a problem."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="update-problem-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(
                session=session,
                run_id="update-problem-run",
                question_name="Binary Search"
            )
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            updated = update_problem(
                session,
                problem_id,
                status="success",
                final_card_count=5,
                processing_time_seconds=2.5
            )
            assert updated.status == "success"
            assert updated.final_card_count == 5
            assert updated.processing_time_seconds == 2.5

    def test_update_problem_not_found(self, in_memory_db):
        """Test updating a non-existent problem raises error."""
        with pytest.raises(ValueError, match="Problem not found"):
            with in_memory_db.session_scope() as session:
                update_problem(session, 99999, status="success")

    def test_get_problem(self, in_memory_db):
        """Test getting a problem by ID."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="get-problem-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(
                session=session,
                run_id="get-problem-run",
                question_name="Test Problem"
            )
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            result = get_problem(session, problem_id)
            assert result is not None
            assert result.question_name == "Test Problem"


class TestProviderResultCRUD:
    """Tests for ProviderResult CRUD operations."""

    def test_create_provider_result(self, in_memory_db):
        """Test creating a provider result."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="provider-result-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(
                session=session,
                run_id="provider-result-run",
                question_name="Test"
            )
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            result = create_provider_result(
                session=session,
                problem_id=problem_id,
                run_id="provider-result-run",
                provider_name="test_provider",
                provider_model="test-model",
                success=True,
                raw_output='{"cards": []}',
                card_count=0
            )
            assert result.id is not None
            assert result.provider_name == "test_provider"
            assert result.provider_model == "test-model"
            assert result.success is True
            assert result.raw_output == '{"cards": []}'

    def test_create_provider_result_failure(self, in_memory_db):
        """Test creating a failed provider result."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="provider-fail-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(
                session=session,
                run_id="provider-fail-run",
                question_name="Test"
            )
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            result = create_provider_result(
                session=session,
                problem_id=problem_id,
                run_id="provider-fail-run",
                provider_name="failing_provider",
                provider_model="fail-model",
                success=False,
                error_message="API timeout"
            )
            assert result.success is False
            assert result.error_message == "API timeout"


class TestCardCRUD:
    """Tests for Card CRUD operations."""

    def test_create_cards(self, in_memory_db):
        """Test creating multiple cards."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="card-test-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(
                session=session,
                run_id="card-test-run",
                question_name="Test"
            )
            problem_id = problem.id

        cards_data = [
            {"front": "Q1", "back": "A1", "card_type": "Concept", "tags": ["tag1"]},
            {"front": "Q2", "back": "A2", "card_type": "Code", "tags": ["tag2", "tag3"]},
        ]

        with in_memory_db.session_scope() as session:
            cards = create_cards(
                session=session,
                problem_id=problem_id,
                run_id="card-test-run",
                cards_data=cards_data
            )
            assert len(cards) == 2
            assert cards[0].front == "Q1"
            assert cards[0].back == "A1"
            assert cards[0].card_type == "Concept"
            assert cards[0].card_index == 0
            assert cards[1].card_index == 1

    def test_create_cards_empty_list(self, in_memory_db):
        """Test creating cards with empty list."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="empty-cards-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(
                session=session,
                run_id="empty-cards-run",
                question_name="Test"
            )
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            cards = create_cards(
                session=session,
                problem_id=problem_id,
                run_id="empty-cards-run",
                cards_data=[]
            )
            assert cards == []


class TestDatabaseModels:
    """Tests for database model relationships."""

    def test_run_problems_relationship(self, in_memory_db):
        """Test Run to Problems relationship."""
        with in_memory_db.session_scope() as session:
            run = create_run(
                session=session,
                id="rel-test-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            create_problem(session, "rel-test-run", "Problem 1")
            create_problem(session, "rel-test-run", "Problem 2")

        with in_memory_db.session_scope() as session:
            run = get_run(session, "rel-test-run")
            assert len(run.problems) == 2

    def test_problem_cards_relationship(self, in_memory_db):
        """Test Problem to Cards relationship."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="cards-rel-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(session, "cards-rel-run", "Test")
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            create_cards(
                session,
                problem_id,
                "cards-rel-run",
                [{"front": "Q", "back": "A", "card_type": "Basic", "tags": []}]
            )

        with in_memory_db.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert len(problem.cards) == 1
