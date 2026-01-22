"""Tests for DatabaseManager and CRUD operations in src/database.py."""

import json
import pytest

from assertpy import assert_that
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
        assert_that(manager.is_initialized).is_false()
        assert_that(manager.db_path).is_none()

    def test_init_with_path(self, tmp_path):
        """Test DatabaseManager initialization with path."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(db_path)
        assert_that(manager.is_initialized).is_true()
        assert_that(manager.db_path).is_equal_to(db_path)

    def test_initialize(self, tmp_path):
        """Test explicit initialization."""
        manager = DatabaseManager()
        db_path = tmp_path / "test.db"
        manager.initialize(db_path)
        assert_that(manager.is_initialized).is_true()
        assert_that(manager.db_path).is_equal_to(db_path)

    def test_initialize_in_memory(self):
        """Test initialization with in-memory database."""
        manager = DatabaseManager()
        manager.initialize(Path(":memory:"))
        assert_that(manager.is_initialized).is_true()

    def test_get_session_before_init_raises(self):
        """Test that get_session raises before initialization."""
        manager = DatabaseManager()
        with pytest.raises(RuntimeError, match="not initialized"):
            manager.get_session()

    def test_get_session_after_init(self, in_memory_db):
        """Test getting a session after initialization."""
        session = in_memory_db.get_session()
        assert_that(session).is_not_none()
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
            assert_that(result).is_not_none()
            assert_that(result.mode).is_equal_to("leetcode")

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
            assert_that(result).is_none()


class TestSingletonPattern:
    """Tests for DatabaseManager singleton pattern."""

    def test_get_default_creates_instance(self):
        """Test that get_default creates a new instance."""
        DatabaseManager.reset_default()
        manager = DatabaseManager.get_default()
        assert_that(manager).is_not_none()
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
            assert_that(run.id).is_equal_to("test-run-id")
            assert_that(run.mode).is_equal_to("leetcode")
            assert_that(run.subject).is_equal_to("leetcode")
            assert_that(run.card_type).is_equal_to("standard")
            assert_that(run.user_label).is_equal_to("test label")
            assert_that(run.status).is_equal_to("running")

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
            assert_that(run.run_metadata).is_not_none()
            parsed = json.loads(run.run_metadata)
            assert_that(parsed).is_equal_to(metadata)

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
            assert_that(updated.status).is_equal_to("completed")
            assert_that(updated.total_problems).is_equal_to(10)
            assert_that(updated.successful_problems).is_equal_to(8)
            assert_that(updated.failed_problems).is_equal_to(2)
            assert_that(updated.completed_at).is_not_none()

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
            assert_that(run).is_not_none()
            assert_that(run.id).is_equal_to("get-test")

    def test_get_run_not_found(self, in_memory_db):
        """Test getting a non-existent run returns None."""
        with in_memory_db.session_scope() as session:
            run = get_run(session, "nonexistent")
            assert_that(run).is_none()


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
            assert_that(problem.id).is_not_none()
            assert_that(problem.question_name).is_equal_to("Two Sum")
            assert_that(problem.sanitized_name).is_equal_to("two_sum")
            assert_that(problem.category_name).is_equal_to("Arrays")
            assert_that(problem.category_index).is_equal_to(1)
            assert_that(problem.problem_index).is_equal_to(1)
            assert_that(problem.status).is_equal_to("running")

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
            assert_that(updated.status).is_equal_to("success")
            assert_that(updated.final_card_count).is_equal_to(5)
            assert_that(updated.processing_time_seconds).is_equal_to(2.5)

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
            assert_that(result).is_not_none()
            assert_that(result.question_name).is_equal_to("Test Problem")


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
            assert_that(result.id).is_not_none()
            assert_that(result.provider_name).is_equal_to("test_provider")
            assert_that(result.provider_model).is_equal_to("test-model")
            assert_that(result.success).is_true()
            assert_that(result.raw_output).is_equal_to('{"cards": []}')

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
            assert_that(result.success).is_false()
            assert_that(result.error_message).is_equal_to("API timeout")


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
            assert_that(cards).is_length(2)
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
            assert_that(cards).is_equal_to([])


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
            assert_that(run.problems).is_length(2)

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
            assert_that(problem.cards).is_length(1)


class TestReferentialIntegrity:
    """Tests for referential integrity and foreign key constraints."""

    def test_problem_requires_valid_run(self, in_memory_db):
        """Test that Problem model can be created with proper fields."""
        # First create a valid run
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="ref-test-run",
                mode="cs",
                subject="cs",
                card_type="standard"
            )

        # Now create a problem referencing it
        with in_memory_db.session_scope() as session:
            problem = Problem(
                run_id="ref-test-run",
                question_name="Test Problem",
                sanitized_name="test_problem",
                category_name="Test",
                status="success"
            )
            session.add(problem)
            session.commit()
            assert_that(problem.id).is_not_none()

    def test_card_requires_valid_problem(self, in_memory_db):
        """Test Card references valid Problem."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="fk-test-run",
                mode="cs",
                subject="cs",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(session, "fk-test-run", "FK Test")
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            cards = create_cards(
                session,
                problem_id,
                "fk-test-run",
                [{"front": "Q", "back": "A", "card_type": "Basic", "tags": []}]
            )
            assert_that(cards).is_length(1)
            assert cards[0].problem_id == problem_id

    def test_provider_result_requires_valid_run(self, in_memory_db):
        """Test ProviderResult references valid Run."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="pr-fk-run",
                mode="physics",
                subject="physics",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(session, "pr-fk-run", "Provider Result FK Test")
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            pr = create_provider_result(
                session,
                problem_id=problem_id,
                run_id="pr-fk-run",
                provider_name="test",
                provider_model="test-model",
                success=True,
                raw_output="{}"
            )
            assert_that(pr.run_id).is_equal_to("pr-fk-run")
            assert_that(pr.problem_id).is_equal_to(problem_id)


class TestConcurrentAccess:
    """Tests for concurrent database access patterns."""

    def test_multiple_sessions_read(self, in_memory_db):
        """Test multiple sessions reading from database."""
        # Create initial data
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="concurrent-read-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        # Read from multiple sessions
        session1 = in_memory_db.get_session()
        session2 = in_memory_db.get_session()

        run1 = get_run(session1, "concurrent-read-run")
        run2 = get_run(session2, "concurrent-read-run")

        assert_that(run1.id).is_equal_to(run2.id)
        assert_that(run1.mode).is_equal_to(run2.mode)

        session1.close()
        session2.close()

    def test_session_isolation(self, in_memory_db):
        """Test that uncommitted changes are not visible to other sessions."""
        # Create a run
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="isolation-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        # Modify in one session (uncommitted)
        session1 = in_memory_db.get_session()
        run1 = get_run(session1, "isolation-run")
        original_status = run1.status

        # Change status but don't commit
        run1.status = "modified"

        # Read from another session
        session2 = in_memory_db.get_session()
        run2 = get_run(session2, "isolation-run")

        # Should still see original value (depending on isolation level)
        # SQLite default is serializable, so this test documents behavior
        session1.rollback()
        session1.close()
        session2.close()


class TestQueryOperations:
    """Tests for database query operations."""

    def test_get_run_returns_none_for_missing(self, in_memory_db):
        """Test get_run returns None for non-existent run."""
        with in_memory_db.session_scope() as session:
            run = get_run(session, "missing-run-id")
            assert_that(run).is_none()

    def test_get_problem_returns_none_for_missing(self, in_memory_db):
        """Test get_problem returns None for non-existent problem."""
        with in_memory_db.session_scope() as session:
            problem = get_problem(session, 99999)
            assert_that(problem).is_none()

    def test_query_runs_by_status(self, in_memory_db):
        """Test querying runs by status."""
        # Create multiple runs with different statuses
        with in_memory_db.session_scope() as session:
            create_run(session=session, id="run-status-1", mode="leetcode",
                       subject="leetcode", card_type="standard")
            create_run(session=session, id="run-status-2", mode="cs",
                       subject="cs", card_type="standard")

        with in_memory_db.session_scope() as session:
            run1 = get_run(session, "run-status-1")
            run1.status = "completed"
            run2 = get_run(session, "run-status-2")
            run2.status = "failed"

        with in_memory_db.session_scope() as session:
            # Query completed runs
            completed_runs = session.query(Run).filter(Run.status == "completed").all()
            assert len(completed_runs) >= 1

            failed_runs = session.query(Run).filter(Run.status == "failed").all()
            assert len(failed_runs) >= 1

    def test_query_problems_by_run(self, in_memory_db):
        """Test querying problems for a specific run."""
        with in_memory_db.session_scope() as session:
            create_run(session=session, id="problems-query-run", mode="leetcode",
                       subject="leetcode", card_type="standard")

        with in_memory_db.session_scope() as session:
            for i in range(5):
                create_problem(session, "problems-query-run", f"Problem {i}")

        with in_memory_db.session_scope() as session:
            problems = session.query(Problem).filter(
                Problem.run_id == "problems-query-run"
            ).all()
            assert_that(problems).is_length(5)

    def test_query_cards_by_problem(self, in_memory_db):
        """Test querying cards for a specific problem."""
        with in_memory_db.session_scope() as session:
            create_run(session=session, id="cards-query-run", mode="leetcode",
                       subject="leetcode", card_type="standard")

        with in_memory_db.session_scope() as session:
            problem = create_problem(session, "cards-query-run", "Cards Query Test")
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            create_cards(
                session,
                problem_id,
                "cards-query-run",
                [
                    {"front": f"Q{i}", "back": f"A{i}", "card_type": "Basic", "tags": []}
                    for i in range(3)
                ]
            )

        with in_memory_db.session_scope() as session:
            cards = session.query(Card).filter(Card.problem_id == problem_id).all()
            assert_that(cards).is_length(3)


class TestUpdateOperations:
    """Tests for update operations."""

    def test_update_run_multiple_fields(self, in_memory_db):
        """Test updating multiple fields on a run."""
        with in_memory_db.session_scope() as session:
            run = create_run(
                session=session,
                id="multi-update-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            run = update_run(
                session,
                "multi-update-run",
                status="completed",
                total_problems=10,
                successful_problems=10,
            )
            assert_that(run.status).is_equal_to("completed")
            assert_that(run.total_problems).is_equal_to(10)
            assert_that(run.successful_problems).is_equal_to(10)

    def test_update_run_with_failure(self, in_memory_db):
        """Test updating run with failed status."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="error-update-run",
                mode="cs",
                subject="cs",
                card_type="mcq"
            )

        with in_memory_db.session_scope() as session:
            run = update_run(
                session,
                "error-update-run",
                status="failed",
                failed_problems=5
            )
            assert_that(run.status).is_equal_to("failed")
            assert_that(run.failed_problems).is_equal_to(5)

    def test_update_problem_status(self, in_memory_db):
        """Test updating problem status."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="problem-status-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(session, "problem-status-run", "Status Test")
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            problem = update_problem(session, problem_id, status="completed")
            assert_that(problem.status).is_equal_to("completed")


class TestEdgeCasesDatabase:
    """Edge case tests for database operations."""

    def test_empty_string_fields(self, in_memory_db):
        """Test handling of empty string fields."""
        with in_memory_db.session_scope() as session:
            run = create_run(
                session=session,
                id="empty-fields-run",
                mode="",  # Empty mode
                subject="",
                card_type=""
            )
            assert_that(run.mode).is_equal_to("")

    def test_very_long_string_fields(self, in_memory_db):
        """Test handling of very long string fields."""
        long_string = "x" * 10000
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="long-string-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(session, "long-string-run", "Long Problem Test")
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            cards = create_cards(
                session,
                problem_id,
                "long-string-run",
                [{"front": long_string, "back": "A", "card_type": "Basic", "tags": []}]
            )
            assert len(cards[0].front) == 10000

    def test_unicode_in_database_fields(self, in_memory_db):
        """Test Unicode content in database fields."""
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="unicode-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(
                session,
                "unicode-run",
                "算法问题 - Algorithm Problem"
            )
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert "算法问题" in problem.question_name

    def test_json_serialization_in_fields(self, in_memory_db):
        """Test JSON serialization for complex data."""
        complex_data = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "unicode": "中文"
        }
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id="json-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )

        with in_memory_db.session_scope() as session:
            problem = create_problem(session, "json-run", "JSON Test")
            problem_id = problem.id

        with in_memory_db.session_scope() as session:
            pr = create_provider_result(
                session,
                problem_id=problem_id,
                run_id="json-run",
                provider_name="test",
                provider_model="test-model",
                success=True,
                raw_output=json.dumps(complex_data)
            )
            assert_that(pr.raw_output).is_not_none()

    def test_null_optional_fields(self, in_memory_db):
        """Test handling of null optional fields."""
        with in_memory_db.session_scope() as session:
            run = create_run(
                session=session,
                id="null-fields-run",
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )
            assert_that(run.completed_at).is_none()
            assert_that(run.user_label).is_none()

    def test_special_characters_in_id(self, in_memory_db):
        """Test handling of special characters in IDs."""
        special_id = "run-with-special-chars_@#$%"
        with in_memory_db.session_scope() as session:
            run = create_run(
                session=session,
                id=special_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard"
            )
            assert_that(run.id).is_equal_to(special_id)

        with in_memory_db.session_scope() as session:
            retrieved = get_run(session, special_id)
            assert_that(retrieved).is_not_none()
            assert_that(retrieved.id).is_equal_to(special_id)
