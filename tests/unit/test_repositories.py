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

    def test_run_stats_equality(self):
        """Test RunStats equality comparison."""
        stats1 = RunStats(total_problems=5, successful_problems=4, failed_problems=1)
        stats2 = RunStats(total_problems=5, successful_problems=4, failed_problems=1)
        assert stats1 == stats2

    def test_run_stats_inequality(self):
        """Test RunStats inequality comparison."""
        stats1 = RunStats(total_problems=5, successful_problems=4, failed_problems=1)
        stats2 = RunStats(total_problems=5, successful_problems=3, failed_problems=2)
        assert stats1 != stats2

    def test_run_stats_large_numbers(self):
        """Test RunStats with large numbers."""
        stats = RunStats(
            total_problems=1000000,
            successful_problems=999999,
            failed_problems=1
        )
        assert stats.total_problems == 1000000


class TestRunRepositoryDbManager:
    """Tests for RunRepository db_manager property."""

    def test_db_manager_uses_injected(self, in_memory_db):
        """Test db_manager property returns injected manager."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        assert repo.db_manager is in_memory_db

    def test_db_manager_falls_back_to_default(self, in_memory_db, monkeypatch):
        """Test db_manager falls back to default when not injected."""
        from src.database import DatabaseManager
        # Set the default
        DatabaseManager.set_default(in_memory_db)
        try:
            repo = RunRepository(Path(":memory:"), db_manager=None)
            assert repo.db_manager is in_memory_db
        finally:
            DatabaseManager.reset_default()


class TestCardRepositoryDbManager:
    """Tests for CardRepository db_manager property."""

    def test_db_manager_uses_injected(self, in_memory_db):
        """Test db_manager property returns injected manager."""
        repo = CardRepository(run_id="test", db_manager=in_memory_db)
        assert repo.db_manager is in_memory_db


class TestRunRepositoryModes:
    """Tests for RunRepository with different modes."""

    def test_leetcode_mode(self, in_memory_db):
        """Test creating leetcode mode run."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.mode == "leetcode"
            assert run.subject == "leetcode"
            assert run.card_type == "standard"

    def test_leetcode_mcq_mode(self, in_memory_db):
        """Test creating leetcode mcq mode run."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="leetcode_mcq",
            subject="leetcode",
            card_type="mcq"
        )
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.mode == "leetcode_mcq"
            assert run.card_type == "mcq"

    def test_cs_mode(self, in_memory_db):
        """Test creating cs mode run."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="cs",
            subject="cs",
            card_type="standard"
        )
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.mode == "cs"
            assert run.subject == "cs"

    def test_cs_mcq_mode(self, in_memory_db):
        """Test creating cs mcq mode run."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="cs_mcq",
            subject="cs",
            card_type="mcq"
        )
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.mode == "cs_mcq"

    def test_physics_mode(self, in_memory_db):
        """Test creating physics mode run."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="physics",
            subject="physics",
            card_type="standard"
        )
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.mode == "physics"

    def test_physics_mcq_mode(self, in_memory_db):
        """Test creating physics mcq mode run."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="physics_mcq",
            subject="physics",
            card_type="mcq"
        )
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.mode == "physics_mcq"

    def test_custom_mode(self, in_memory_db):
        """Test creating custom subject mode run."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="my_custom_subject",
            subject="my_custom_subject",
            card_type="standard"
        )
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.mode == "my_custom_subject"


class TestCardRepositoryProblemCategories:
    """Tests for CardRepository problem category handling."""

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

    def test_problem_without_category(self, card_repo):
        """Test creating problem without category."""
        problem_id = card_repo.create_initial_problem(
            question_name="Simple Question"
        )
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.category_name is None
            assert problem.category_index is None
            assert problem.problem_index is None

    def test_problem_with_full_category_info(self, card_repo):
        """Test creating problem with full category info."""
        problem_id = card_repo.create_initial_problem(
            question_name="Two Sum",
            category_name="Arrays",
            category_index=1,
            problem_index=5
        )
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.category_name == "Arrays"
            assert problem.category_index == 1
            assert problem.problem_index == 5

    def test_problem_category_index_only(self, card_repo):
        """Test creating problem with category index but no name."""
        problem_id = card_repo.create_initial_problem(
            question_name="Question",
            category_index=3
        )
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.category_index == 3

    def test_multiple_problems_same_category(self, card_repo):
        """Test creating multiple problems in same category."""
        problems = []
        for i in range(5):
            pid = card_repo.create_initial_problem(
                question_name=f"Problem {i}",
                category_name="Binary Search",
                category_index=2,
                problem_index=i + 1
            )
            problems.append(pid)

        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            for i, pid in enumerate(problems):
                problem = get_problem(session, pid)
                assert problem.category_name == "Binary Search"
                assert problem.problem_index == i + 1


class TestCardRepositoryProviderResults:
    """Extended tests for CardRepository provider result handling."""

    @pytest.fixture
    def card_repo(self, in_memory_db):
        """Create a CardRepository with an active run."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="cs",
            subject="cs",
            card_type="standard"
        )
        return run_repo.get_card_repository()

    def test_save_provider_result_without_card_count(self, card_repo):
        """Test saving provider result without card count."""
        problem_id = card_repo.create_initial_problem(question_name="Test")
        card_repo.save_provider_result(
            problem_id=problem_id,
            provider_name="nvidia",
            provider_model="llama-70b",
            raw_output='{"cards": []}'
        )
        from src.database import ProviderResult
        with card_repo.db_manager.session_scope() as session:
            result = session.query(ProviderResult).filter_by(
                problem_id=problem_id
            ).first()
            assert result.card_count is None

    def test_save_provider_result_large_output(self, card_repo):
        """Test saving provider result with large raw output."""
        problem_id = card_repo.create_initial_problem(question_name="Large Output")
        large_output = json.dumps({"data": "x" * 100000})
        card_repo.save_provider_result(
            problem_id=problem_id,
            provider_name="test",
            provider_model="test-model",
            raw_output=large_output,
            card_count=0
        )
        from src.database import ProviderResult
        with card_repo.db_manager.session_scope() as session:
            result = session.query(ProviderResult).filter_by(
                problem_id=problem_id
            ).first()
            assert len(result.raw_output) > 100000

    def test_save_provider_result_unicode(self, card_repo):
        """Test saving provider result with unicode content."""
        problem_id = card_repo.create_initial_problem(question_name="Unicode")
        unicode_output = json.dumps(
            {"cards": [{"front": "中文", "back": "日本語"}]},
            ensure_ascii=False
        )
        card_repo.save_provider_result(
            problem_id=problem_id,
            provider_name="test",
            provider_model="test-model",
            raw_output=unicode_output,
            card_count=1
        )
        from src.database import ProviderResult
        with card_repo.db_manager.session_scope() as session:
            result = session.query(ProviderResult).filter_by(
                problem_id=problem_id
            ).first()
            assert "中文" in result.raw_output


class TestCardRepositoryFinalResults:
    """Extended tests for CardRepository final result handling."""

    @pytest.fixture
    def card_repo(self, in_memory_db):
        """Create a CardRepository with an active run."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="physics",
            subject="physics",
            card_type="standard"
        )
        return run_repo.get_card_repository()

    def test_save_final_result_stores_json(self, card_repo):
        """Test that final result is stored as JSON."""
        problem_id = card_repo.create_initial_problem(question_name="JSON Test")
        card_data = {
            "title": "JSON Test",
            "topic": "Testing",
            "difficulty": "Easy",
            "cards": [
                {"front": "Q", "back": "A", "card_type": "Basic", "tags": ["t1"]}
            ]
        }
        card_repo.save_final_result(
            problem_id=problem_id,
            card_data=card_data,
            processing_time_seconds=1.0
        )
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            stored_data = json.loads(problem.final_result)
            assert stored_data["title"] == "JSON Test"
            assert stored_data["topic"] == "Testing"
            assert stored_data["difficulty"] == "Easy"

    def test_save_final_result_many_cards(self, card_repo):
        """Test saving final result with many cards."""
        problem_id = card_repo.create_initial_problem(question_name="Many Cards")
        cards = [
            {"front": f"Q{i}", "back": f"A{i}", "card_type": "Basic", "tags": []}
            for i in range(50)
        ]
        card_repo.save_final_result(
            problem_id=problem_id,
            card_data={"title": "Many Cards", "cards": cards},
            processing_time_seconds=30.0
        )
        from src.database import get_problem, Card
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.final_card_count == 50
            saved_cards = session.query(Card).filter_by(problem_id=problem_id).all()
            assert len(saved_cards) == 50

    def test_save_final_result_zero_time(self, card_repo):
        """Test saving final result with zero processing time."""
        problem_id = card_repo.create_initial_problem(question_name="Fast")
        card_repo.save_final_result(
            problem_id=problem_id,
            card_data={"title": "Fast", "cards": []},
            processing_time_seconds=0.0
        )
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.processing_time_seconds == 0.0

    def test_save_final_result_large_time(self, card_repo):
        """Test saving final result with large processing time."""
        problem_id = card_repo.create_initial_problem(question_name="Slow")
        card_repo.save_final_result(
            problem_id=problem_id,
            card_data={"title": "Slow", "cards": []},
            processing_time_seconds=999999.99
        )
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.processing_time_seconds == 999999.99


class TestIntegrationWorkflow:
    """Integration tests for full repository workflow."""

    def test_full_successful_workflow(self, in_memory_db):
        """Test complete successful generation workflow."""
        # Start run
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = run_repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
            user_label="integration-test"
        )

        # Get card repository
        card_repo = run_repo.get_card_repository()

        # Create and process problems
        problem_ids = []
        for name in ["Two Sum", "Valid Parentheses", "Merge Intervals"]:
            pid = card_repo.create_initial_problem(
                question_name=name,
                category_name="Arrays",
                category_index=1,
                problem_index=len(problem_ids) + 1
            )
            problem_ids.append(pid)

            # Save provider result
            card_repo.save_provider_result(
                problem_id=pid,
                provider_name="nvidia",
                provider_model="llama-70b",
                raw_output='{"cards": []}',
                card_count=2
            )

            # Save final result
            card_repo.save_final_result(
                problem_id=pid,
                card_data={
                    "title": name,
                    "cards": [
                        {"front": f"Q1 {name}", "back": "A1", "card_type": "Basic", "tags": []},
                        {"front": f"Q2 {name}", "back": "A2", "card_type": "Concept", "tags": []}
                    ]
                },
                processing_time_seconds=5.0
            )

        # Complete run
        run_repo.mark_run_completed(RunStats(
            total_problems=3,
            successful_problems=3,
            failed_problems=0
        ))

        # Verify final state
        from src.database import get_run, get_problem, Card
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.status == "completed"
            assert run.total_problems == 3
            assert run.successful_problems == 3

            # Check all problems
            for pid in problem_ids:
                problem = get_problem(session, pid)
                assert problem.status == "success"
                assert problem.final_card_count == 2

            # Check cards
            cards = session.query(Card).filter_by(run_id=run_id).all()
            assert len(cards) == 6  # 2 cards per problem

    def test_partial_failure_workflow(self, in_memory_db):
        """Test workflow with some failures."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = run_repo.create_new_run(
            mode="cs",
            subject="cs",
            card_type="standard"
        )
        card_repo = run_repo.get_card_repository()

        # Success
        success_id = card_repo.create_initial_problem(question_name="Success Q")
        card_repo.save_final_result(
            problem_id=success_id,
            card_data={"title": "Success Q", "cards": [
                {"front": "Q", "back": "A", "card_type": "Basic", "tags": []}
            ]},
            processing_time_seconds=3.0
        )

        # Failure
        fail_id = card_repo.create_initial_problem(question_name="Failed Q")
        card_repo.update_problem_failed(problem_id=fail_id, processing_time_seconds=1.0)

        run_repo.mark_run_completed(RunStats(
            total_problems=2,
            successful_problems=1,
            failed_problems=1
        ))

        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.status == "completed"
            assert run.successful_problems == 1
            assert run.failed_problems == 1

    def test_run_failure_workflow(self, in_memory_db):
        """Test workflow when entire run fails."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = run_repo.create_new_run(
            mode="physics",
            subject="physics",
            card_type="mcq"
        )

        run_repo.mark_run_failed()

        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.status == "failed"


class TestEdgeCasesRepositories:
    """Edge case tests for repositories."""

    @pytest.fixture
    def card_repo(self, in_memory_db):
        """Create a CardRepository with an active run."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="test",
            subject="test",
            card_type="standard"
        )
        return run_repo.get_card_repository()

    def test_unicode_question_name(self, card_repo):
        """Test Unicode characters in question names."""
        problem_id = card_repo.create_initial_problem(
            question_name="算法问题 - 二分搜索"
        )
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert "算法问题" in problem.question_name

    def test_very_long_question_name(self, card_repo):
        """Test very long question names."""
        long_name = "A" * 1000
        problem_id = card_repo.create_initial_problem(question_name=long_name)
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert len(problem.question_name) == 1000

    def test_special_characters_in_question(self, card_repo):
        """Test special characters in question names."""
        special_name = "Question with <special> & \"chars\" 'quotes'"
        problem_id = card_repo.create_initial_problem(question_name=special_name)
        from src.database import get_problem
        with card_repo.db_manager.session_scope() as session:
            problem = get_problem(session, problem_id)
            assert problem.question_name == special_name

    def test_empty_user_label(self, in_memory_db):
        """Test run with empty string user label."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="test",
            subject="test",
            card_type="standard",
            user_label=""
        )
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert run.user_label == ""

    def test_very_long_user_label(self, in_memory_db):
        """Test run with very long user label."""
        repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        long_label = "x" * 500
        run_id = repo.create_new_run(
            mode="test",
            subject="test",
            card_type="standard",
            user_label=long_label
        )
        from src.database import get_run
        with in_memory_db.session_scope() as session:
            run = get_run(session, run_id)
            assert len(run.user_label) == 500
