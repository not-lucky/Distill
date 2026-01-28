"""Unit tests for resume functionality."""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.database import DatabaseManager, create_run, create_problem, update_problem, update_run
from src.queries import get_run_by_id, get_successful_questions_for_run, get_successful_problems_with_results


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
        run_id = "test-run-completed"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
                status="completed"
            )
        
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 4
            mock_config.return_value.generation.request_delay = 0.1
            
            with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
                # Mock DatabaseManager.get_default() to return our in_memory_db
                with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                    # Mock get_run_by_id to use our in_memory_db
                    with patch("src.orchestrator.get_run_by_id") as mock_get_run:
                        # Helper to get run from db
                        def get_run_helper(rid):
                            with in_memory_db.session_scope() as session:
                                from src.database import Run
                                run = session.query(Run).filter(Run.id == rid).first()
                                if run:
                                    session.refresh(run)
                                    session.expunge(run)
                                return run

                        mock_get_run.side_effect = get_run_helper

                        orch = Orchestrator(
                            subject_config=mock_subject_config,
                            resume_run_id=run_id,
                        )
                        # Inject db_manager
                        orch.db_manager = in_memory_db

                        result = orch._initialize_for_resume()

                        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_for_resume_fails_on_mode_mismatch(
        self, mock_subject_config, in_memory_db
    ):
        """Test that resume fails when mode doesn't match."""
        from src.orchestrator import Orchestrator
        
        # Create a run with different mode
        run_id = "test-run-mismatch"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="cs",  # Different mode
                subject="cs",
                card_type="standard",
                status="failed"
            )
        
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 4
            mock_config.return_value.generation.request_delay = 0.1
            
            with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
                with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                    with patch("src.orchestrator.get_run_by_id") as mock_get_run:
                        def get_run_helper(rid):
                            with in_memory_db.session_scope() as session:
                                from src.database import Run
                                run = session.query(Run).filter(Run.id == rid).first()
                                if run:
                                    session.refresh(run)
                                    session.expunge(run)
                                return run
                        mock_get_run.side_effect = get_run_helper

                        orch = Orchestrator(
                            subject_config=mock_subject_config,  # leetcode mode
                            resume_run_id=run_id,
                        )
                        orch.db_manager = in_memory_db

                        result = orch._initialize_for_resume()

                        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_for_resume_succeeds_for_failed_run(
        self, mock_subject_config, in_memory_db
    ):
        """Test that resume succeeds for failed runs."""
        from src.orchestrator import Orchestrator
        
        # Create a failed run with some processed questions
        run_id = "test-run-failed"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
                status="failed"
            )

            # Add a successful problem
            card_data = {"title": "Two Sum", "cards": []}
            p = create_problem(session, run_id, "Two Sum", status="success")
            update_problem(session, p.id, final_result=json.dumps(card_data))
        
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 4
            mock_config.return_value.generation.request_delay = 0.1
            
            with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
                with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                    # Mock query functions to use our DB
                    with patch("src.orchestrator.get_run_by_id") as mock_get_run, \
                         patch("src.orchestrator.get_successful_questions_for_run") as mock_get_questions, \
                         patch("src.orchestrator.get_successful_problems_with_results") as mock_get_results:

                        def get_run_helper(rid):
                            with in_memory_db.session_scope() as session:
                                from src.database import Run
                                run = session.query(Run).filter(Run.id == rid).first()
                                if run:
                                    session.refresh(run)
                                    session.expunge(run)
                                return run
                        mock_get_run.side_effect = get_run_helper

                        mock_get_questions.return_value = ["Two Sum"]
                        mock_get_results.return_value = [{"title": "Two Sum"}]

                        orch = Orchestrator(
                            subject_config=mock_subject_config,
                            resume_run_id=run_id,
                        )
                        orch.db_manager = in_memory_db

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
