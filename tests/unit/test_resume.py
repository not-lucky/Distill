"""Unit tests for resume functionality."""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.repositories import RunRepository, RunStats
from src.database import DatabaseManager, Run, Problem


class TestRunRepositoryResume:
    """Tests for RunRepository resume-related methods."""

    def test_set_run_id_sets_internal_run_id(self, in_memory_db):
        """Test that set_run_id correctly sets the internal run ID."""
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        
        repo.set_run_id("test-run-123")
        
        assert repo.run_id == "test-run-123"

    def test_load_existing_run_returns_none_when_not_found(self, in_memory_db):
        """Test that load_existing_run returns None for non-existent runs."""
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        
        result = repo.load_existing_run("nonexistent-run")
        
        assert result is None

    def test_load_existing_run_returns_run_data(self, in_memory_db):
        """Test that load_existing_run returns correct run data."""
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        
        # Create a run first
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
            user_label="test-label",
        )
        
        # Load it back
        result = repo.load_existing_run(run_id)
        
        assert result is not None
        assert result["id"] == run_id
        assert result["mode"] == "leetcode"
        assert result["subject"] == "leetcode"
        assert result["card_type"] == "standard"
        assert result["status"] == "running"
        assert result["user_label"] == "test-label"

    def test_load_existing_run_with_partial_id(self, in_memory_db):
        """Test that load_existing_run works with partial run IDs."""
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        
        # Create a run
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
        )
        
        # Load with partial ID (first 8 chars)
        partial_id = run_id[:8]
        result = repo.load_existing_run(partial_id)
        
        assert result is not None
        assert result["id"] == run_id

    def test_get_processed_questions_returns_empty_set_for_new_run(self, in_memory_db):
        """Test that get_processed_questions returns empty set for run with no problems."""
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode", 
            card_type="standard",
        )
        
        result = repo.get_processed_questions(run_id)
        
        assert result == set()

    def test_get_processed_questions_returns_successful_questions(self, in_memory_db):
        """Test that get_processed_questions returns only successful questions."""
        from src.database import create_problem, update_problem
        
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
        )
        
        # Create problems with different statuses
        with in_memory_db.session_scope() as session:
            p1 = create_problem(session, run_id, "Two Sum", status="success")
            p2 = create_problem(session, run_id, "Three Sum", status="failed")
            p3 = create_problem(session, run_id, "Binary Search", status="success")
        
        result = repo.get_processed_questions(run_id)
        
        assert result == {"Two Sum", "Binary Search"}
        assert "Three Sum" not in result

    def test_get_existing_results_returns_card_data(self, in_memory_db):
        """Test that get_existing_results returns card data from successful problems."""
        from src.database import create_problem, update_problem
        
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
        )
        
        card_data = {
            "title": "Two Sum",
            "cards": [{"front": "Q", "back": "A"}]
        }
        
        with in_memory_db.session_scope() as session:
            p = create_problem(session, run_id, "Two Sum", status="success")
            update_problem(session, p.id, final_result=json.dumps(card_data))
        
        result = repo.get_existing_results(run_id)
        
        assert len(result) == 1
        assert result[0]["title"] == "Two Sum"
        assert len(result[0]["cards"]) == 1

    def test_get_existing_results_skips_failed_problems(self, in_memory_db):
        """Test that get_existing_results skips failed problems."""
        from src.database import create_problem, update_problem
        
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
        )
        
        with in_memory_db.session_scope() as session:
            create_problem(session, run_id, "Failed Problem", status="failed")
        
        result = repo.get_existing_results(run_id)
        
        assert result == []

    def test_update_run_status_changes_status(self, in_memory_db):
        """Test that update_run_status correctly updates the run status."""
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
        )
        
        # Verify initial status
        run_data = repo.load_existing_run(run_id)
        assert run_data["status"] == "running"
        
        # Mark as failed
        repo.update_run_status("failed")
        
        # Verify updated status
        run_data = repo.load_existing_run(run_id)
        assert run_data["status"] == "failed"

    def test_update_run_status_raises_without_active_run(self, in_memory_db):
        """Test that update_run_status raises error without active run."""
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        
        with pytest.raises(RuntimeError, match="No active run"):
            repo.update_run_status("failed")


class TestOrchestratorResume:
    """Tests for Orchestrator resume functionality."""

    @pytest.fixture
    def mock_subject_config(self):
        """Create a mock subject config."""
        config = MagicMock()
        config.name = "leetcode"
        config.deck_prefix = "LeetCode"
        config.deck_prefix_mcq = "LeetCode MCQ"
        config.initial_prompt = "Test prompt"
        config.combine_prompt = "Combine prompt"
        config.target_questions = {"Arrays": ["Two Sum", "Three Sum"]}
        config.target_model = MagicMock()
        return config

    def test_orchestrator_accepts_resume_run_id(self, mock_subject_config):
        """Test that Orchestrator accepts resume_run_id parameter."""
        from src.orchestrator import Orchestrator
        
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 4
            mock_config.return_value.generation.request_delay = 0.1
            
            orch = Orchestrator(
                subject_config=mock_subject_config,
                resume_run_id="test-run-123",
            )
            
            assert orch.resume_run_id == "test-run-123"

    def test_orchestrator_initializes_empty_processed_questions(self, mock_subject_config):
        """Test that Orchestrator initializes with empty processed questions."""
        from src.orchestrator import Orchestrator
        
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 4
            mock_config.return_value.generation.request_delay = 0.1
            
            orch = Orchestrator(subject_config=mock_subject_config)
            
            assert orch._processed_questions == set()
            assert orch._existing_results == []

    @pytest.mark.asyncio
    async def test_initialize_for_resume_fails_on_completed_run(
        self, mock_subject_config, in_memory_db
    ):
        """Test that resume fails for completed runs."""
        from src.orchestrator import Orchestrator
        
        # Create and complete a run
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
        )
        repo.mark_run_completed(RunStats(total_problems=1, successful_problems=1, failed_problems=0))
        
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 4
            mock_config.return_value.generation.request_delay = 0.1
            
            with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
                orch = Orchestrator(
                    subject_config=mock_subject_config,
                    resume_run_id=run_id,
                )
                orch.run_repo = repo
                
                result = orch._initialize_for_resume()
                
                assert result is False

    @pytest.mark.asyncio
    async def test_initialize_for_resume_fails_on_mode_mismatch(
        self, mock_subject_config, in_memory_db
    ):
        """Test that resume fails when mode doesn't match."""
        from src.orchestrator import Orchestrator
        
        # Create a run with different mode
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="cs",  # Different mode
            subject="cs",
            card_type="standard",
        )
        repo.update_run_status("failed")
        
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 4
            mock_config.return_value.generation.request_delay = 0.1
            
            with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
                orch = Orchestrator(
                    subject_config=mock_subject_config,  # leetcode mode
                    resume_run_id=run_id,
                )
                orch.run_repo = repo
                
                result = orch._initialize_for_resume()
                
                assert result is False

    @pytest.mark.asyncio
    async def test_initialize_for_resume_succeeds_for_failed_run(
        self, mock_subject_config, in_memory_db
    ):
        """Test that resume succeeds for failed runs."""
        from src.orchestrator import Orchestrator
        from src.database import create_problem, update_problem
        
        # Create a failed run with some processed questions
        repo = RunRepository(db_path=":memory:", db_manager=in_memory_db)
        run_id = repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
        )
        
        # Add a successful problem
        card_data = {"title": "Two Sum", "cards": []}
        with in_memory_db.session_scope() as session:
            p = create_problem(session, run_id, "Two Sum", status="success")
            update_problem(session, p.id, final_result=json.dumps(card_data))
        
        repo.update_run_status("failed")
        
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 4
            mock_config.return_value.generation.request_delay = 0.1
            
            with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
                orch = Orchestrator(
                    subject_config=mock_subject_config,
                    resume_run_id=run_id,
                )
                orch.run_repo = repo
                
                result = orch._initialize_for_resume()
                
                assert result is True
                assert "Two Sum" in orch._processed_questions
                assert len(orch._existing_results) == 1


class TestQuestionFiltering:
    """Tests for question filtering in resume mode."""

    def test_filter_removes_processed_questions(self):
        """Test that processed questions are filtered out."""
        all_questions = [
            (1, "Arrays", 1, "Two Sum"),
            (1, "Arrays", 2, "Three Sum"),
            (2, "Trees", 1, "Binary Tree"),
        ]
        processed = {"Two Sum", "Binary Tree"}
        
        remaining = [q for q in all_questions if q[3] not in processed]
        
        assert len(remaining) == 1
        assert remaining[0][3] == "Three Sum"

    def test_filter_keeps_all_when_none_processed(self):
        """Test that all questions kept when none processed."""
        all_questions = [
            (1, "Arrays", 1, "Two Sum"),
            (1, "Arrays", 2, "Three Sum"),
        ]
        processed = set()
        
        remaining = [q for q in all_questions if q[3] not in processed]
        
        assert len(remaining) == 2


class TestCLIResumeArgument:
    """Tests for CLI --resume argument."""

    def test_generate_parser_has_resume_argument(self):
        """Test that generate parser has --resume argument."""
        from src.cli import create_parser
        
        parser = create_parser()
        
        # Parse with resume argument
        args = parser.parse_args(["generate", "leetcode", "--resume", "abc123"])
        
        assert args.resume == "abc123"

    def test_generate_parser_resume_defaults_to_none(self):
        """Test that --resume defaults to None."""
        from src.cli import create_parser
        
        parser = create_parser()
        args = parser.parse_args(["generate", "leetcode"])
        
        assert args.resume is None
