"""Tests for RunRepository and CardRepository in src/repositories.py."""

import json
import pytest
from pathlib import Path

from src.database import DatabaseManager
from src.repositories import RunRepository, CardRepository, RunStats


class TestRunRepository:
    """Tests for RunRepository class."""

    def test_init(self, in_memory_db):
        """Test RunRepository initialization."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        assert repo.db_path == Path(":memory:")
        assert repo.run_id is None

    def test_initialize_database(self, tmp_path):
        """Test database initialization."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager()
        repo = RunRepository(db_path, db_manager=manager)
        repo.initialize_database()
        assert manager.is_initialized

    def test_create_new_run(self, in_memory_db):
        """Test creating a new run."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
            user_label="test"
        )

        assert run_id is not None
        assert repo.run_id == run_id

    def test_create_new_run_with_label(self, in_memory_db):
        """Test creating a run with user label."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="cs_mcq",
            subject="cs",
            card_type="mcq",
            user_label="my test run"
        )

        assert run_id is not None

    def test_mark_run_failed(self, in_memory_db):
        """Test marking a run as failed."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )

        repo.mark_run_failed()

        # Verify status updated
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, repo.run_id)
            assert run.status == "failed"

    def test_mark_run_failed_no_active_run(self, in_memory_db):
        """Test marking failed without active run raises error."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)

        with pytest.raises(RuntimeError, match="No active run"):
            repo.mark_run_failed()

    def test_mark_run_completed(self, in_memory_db):
        """Test marking a run as completed with stats."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )

        stats = RunStats(
            total_problems=10,
            successful_problems=8,
            failed_problems=2
        )
        repo.mark_run_completed(stats)

        # Verify status and stats updated
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, repo.run_id)
            assert run.status == "completed"
            assert run.total_problems == 10
            assert run.successful_problems == 8
            assert run.failed_problems == 2
            assert run.completed_at is not None

    def test_mark_run_completed_no_active_run(self, in_memory_db):
        """Test marking completed without active run raises error."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        stats = RunStats(total_problems=0, successful_problems=0, failed_problems=0)

        with pytest.raises(RuntimeError, match="No active run"):
            repo.mark_run_completed(stats)

    def test_get_card_repository(self, in_memory_db):
        """Test getting a CardRepository for the current run."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )

        card_repo = repo.get_card_repository()

        assert card_repo is not None
        assert isinstance(card_repo, CardRepository)
        assert card_repo.run_id == repo.run_id

    def test_get_card_repository_no_run(self, in_memory_db):
        """Test getting CardRepository without active run raises error."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)

        with pytest.raises(RuntimeError, match="No active run"):
            repo.get_card_repository()

    def test_run_id_property(self, in_memory_db):
        """Test run_id property."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        assert repo.run_id is None

        repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )
        assert repo.run_id is not None


class TestCardRepository:
    """Tests for CardRepository class."""

    @pytest.fixture
    def card_repo(self, in_memory_db):
        """Create a CardRepository with an active run."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )
        return run_repo.get_card_repository()

    def test_init(self, card_repo):
        """Test CardRepository initialization."""
        assert card_repo.run_id is not None

    def test_create_initial_problem(self, card_repo):
        """Test creating an initial problem entry."""
        problem_id = card_repo.create_initial_problem(
            question_name="Two Sum",
            category_name="Arrays",
            category_index=1,
            problem_index=1
        )

        assert problem_id is not None
        assert isinstance(problem_id, int)

    def test_create_initial_problem_minimal(self, card_repo):
        """Test creating a problem with minimal info."""
        problem_id = card_repo.create_initial_problem(
            question_name="Simple Problem"
        )

        assert problem_id is not None

    def test_save_provider_result(self, card_repo):
        """Test saving a provider result."""
        problem_id = card_repo.create_initial_problem(
            question_name="Test Problem"
        )

        card_repo.save_provider_result(
            problem_id=problem_id,
            provider_name="test_provider",
            provider_model="test-model",
            raw_output='{"cards": [{"front": "Q", "back": "A"}]}',
            card_count=1
        )

        # Verify result was saved
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert len(problem.provider_results) == 1
            assert problem.provider_results[0].provider_name == "test_provider"

    def test_save_multiple_provider_results(self, card_repo):
        """Test saving results from multiple providers."""
        problem_id = card_repo.create_initial_problem(
            question_name="Multi Provider Test"
        )

        card_repo.save_provider_result(
            problem_id=problem_id,
            provider_name="provider1",
            provider_model="model1",
            raw_output='{"cards": []}',
            card_count=0
        )
        card_repo.save_provider_result(
            problem_id=problem_id,
            provider_name="provider2",
            provider_model="model2",
            raw_output='{"cards": [{"front": "Q", "back": "A"}]}',
            card_count=1
        )

        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert len(problem.provider_results) == 2

    def test_update_problem_failed(self, card_repo):
        """Test marking a problem as failed."""
        problem_id = card_repo.create_initial_problem(
            question_name="Failing Problem"
        )

        card_repo.update_problem_failed(
            problem_id=problem_id,
            processing_time_seconds=5.5
        )

        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.status == "failed"
            assert problem.processing_time_seconds == 5.5

    def test_save_final_result(self, card_repo):
        """Test saving the final combined result."""
        problem_id = card_repo.create_initial_problem(
            question_name="Final Result Test"
        )

        card_data = {
            "title": "Test",
            "cards": [
                {"front": "Q1", "back": "A1", "card_type": "Basic", "tags": []},
                {"front": "Q2", "back": "A2", "card_type": "Code", "tags": ["tag1"]},
            ]
        }

        card_repo.save_final_result(
            problem_id=problem_id,
            card_data=card_data,
            processing_time_seconds=10.0
        )

        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.status == "success"
            assert problem.final_card_count == 2
            assert problem.processing_time_seconds == 10.0
            assert len(problem.cards) == 2

    def test_save_final_result_empty_cards(self, card_repo):
        """Test saving final result with no cards."""
        problem_id = card_repo.create_initial_problem(
            question_name="Empty Cards Test"
        )

        card_data = {"title": "Empty", "cards": []}

        card_repo.save_final_result(
            problem_id=problem_id,
            card_data=card_data,
            processing_time_seconds=1.0
        )

        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.status == "success"
            assert problem.final_card_count == 0
            assert len(problem.cards) == 0


class TestRunStats:
    """Tests for RunStats dataclass."""

    def test_create_run_stats(self):
        """Test creating RunStats."""
        stats = RunStats(
            total_problems=10,
            successful_problems=8,
            failed_problems=2
        )

        assert stats.total_problems == 10
        assert stats.successful_problems == 8
        assert stats.failed_problems == 2

    def test_run_stats_zero_values(self):
        """Test RunStats with zero values."""
        stats = RunStats(
            total_problems=0,
            successful_problems=0,
            failed_problems=0
        )

        assert stats.total_problems == 0
