"""Integration tests for resume functionality."""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.database import DatabaseManager, create_run, update_run, create_problem, update_problem
from src.queries import get_run_by_id, get_successful_questions_for_run, get_successful_problems_with_results


class TestResumeWorkflow:
    """Integration tests for complete resume workflow."""

    @pytest.fixture
    def mock_subject_config(self):
        """Create a mock subject config."""
        config = MagicMock()
        config.name = "leetcode"
        config.deck_prefix = "LeetCode"
        config.deck_prefix_mcq = "LeetCode MCQ"
        config.initial_prompt = "Test prompt"
        config.combine_prompt = "Combine prompt"
        config.target_questions = {
            "Arrays": ["Two Sum", "Three Sum", "Four Sum"],
        }
        config.target_model = MagicMock()
        return config

    def test_create_run_process_some_fail_resume_complete(self, in_memory_db, mock_subject_config):
        """Test the full workflow: create run, process some questions, fail, then resume."""
        # Phase 1: Create initial run and process some questions
        run_id = "test-run-1"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
                user_label="test-run",
            )

        # Simulate processing "Two Sum" successfully
        with in_memory_db.session_scope() as session:
            p1 = create_problem(session, run_id, "Two Sum", status="success")
            update_problem(
                session,
                p1.id,
                final_result=json.dumps({
                    "title": "Two Sum",
                    "cards": [{"front": "Q1", "back": "A1"}]
                }),
            )

        # Simulate "Three Sum" failing
        with in_memory_db.session_scope() as session:
            p2 = create_problem(session, run_id, "Three Sum", status="failed")

        # Mark run as failed
        with in_memory_db.session_scope() as session:
            update_run(session, run_id, status="failed")

        # Phase 2: Resume the run (Simulate Orchestrator loading it)
        # Load existing run
        run_data = get_run_by_id(run_id)
        assert run_data is not None
        assert run_data.status == "failed"

        # Get processed questions
        processed = set(get_successful_questions_for_run(run_id))
        assert processed == {"Two Sum"}

        # Get existing results
        existing_results = get_successful_problems_with_results(run_id)
        assert len(existing_results) == 1
        assert existing_results[0]["title"] == "Two Sum"

        # Set up for resume (update status)
        with in_memory_db.session_scope() as session:
            update_run(session, run_id, status="running")

        # Verify status updated
        run_data = get_run_by_id(run_id)
        assert run_data.status == "running"

        # Phase 3: Process remaining questions (simulated)
        with in_memory_db.session_scope() as session:
            p3 = create_problem(session, run_id, "Three Sum", status="success")
            update_problem(
                session,
                p3.id,
                final_result=json.dumps({
                    "title": "Three Sum",
                    "cards": [{"front": "Q2", "back": "A2"}]
                }),
            )
            p4 = create_problem(session, run_id, "Four Sum", status="success")
            update_problem(
                session,
                p4.id,
                final_result=json.dumps({
                    "title": "Four Sum",
                    "cards": [{"front": "Q3", "back": "A3"}]
                }),
            )

        # Mark run as completed
        with in_memory_db.session_scope() as session:
            update_run(
                session,
                run_id,
                status="completed",
                total_problems=3,
                successful_problems=3,
                failed_problems=0,
            )

        # Verify final state
        run_data = get_run_by_id(run_id)
        assert run_data.status == "completed"
        assert run_data.total_problems == 3
        assert run_data.successful_problems == 3

    def test_partial_id_matching_for_resume(self, in_memory_db):
        """Test that partial run IDs work for resume."""
        # Create a run
        run_id = "test-run-partial-matching"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
                status="failed"
            )

        # Try loading with various partial ID lengths
        for length in [8, 12, 16, 20]:
            partial = run_id[:length]
            result = get_run_by_id(partial)
            assert result is not None, f"Failed to match with {length} char ID"
            assert result.id == run_id

    def test_result_merging(self, in_memory_db):
        """Test that existing and new results are properly merged."""
        run_id = "test-run-merge"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
            )

        # Add existing successful results
        with in_memory_db.session_scope() as session:
            for i, name in enumerate(["Problem A", "Problem B"], 1):
                p = create_problem(session, run_id, name, status="success")
                update_problem(
                    session,
                    p.id,
                    final_result=json.dumps({
                        "title": name,
                        "cards": [{"front": f"Q{i}", "back": f"A{i}"}]
                    }),
                )

        with in_memory_db.session_scope() as session:
            update_run(session, run_id, status="failed")

        # Get existing results
        existing = get_successful_problems_with_results(run_id)
        assert len(existing) == 2

        # Simulate new results from resumed generation
        new_results = [
            {"title": "Problem C", "cards": [{"front": "Q3", "back": "A3"}]},
            {"title": "Problem D", "cards": [{"front": "Q4", "back": "A4"}]},
        ]

        # Merge
        all_results = existing + new_results
        assert len(all_results) == 4
        assert {r["title"] for r in all_results} == {
            "Problem A", "Problem B", "Problem C", "Problem D"
        }


class TestResumeValidation:
    """Tests for resume validation logic."""

    def test_cannot_resume_completed_run(self, in_memory_db):
        """Test that completed runs cannot be resumed."""
        run_id = "test-run-complete"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
                status="completed",
            )
            update_run(
                session=session,
                run_id=run_id,
                total_problems=1,
                successful_problems=1
            )

        run_data = get_run_by_id(run_id)
        assert run_data.status == "completed"
        # Validation would happen in orchestrator (tested in unit tests)

    def test_can_resume_failed_run(self, in_memory_db):
        """Test that failed runs can be resumed."""
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

        run_data = get_run_by_id(run_id)
        assert run_data.status == "failed"
        # This run should be resumable

    def test_can_resume_running_run(self, in_memory_db):
        """Test that running (interrupted) runs can be resumed."""
        run_id = "test-run-running"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
                status="running"
            )

        run_data = get_run_by_id(run_id)
        assert run_data.status == "running"
        # This run should be resumable


class TestResumeQueries:
    """Tests for resume-related query functions."""

    def test_get_successful_questions_for_run(self, in_memory_db):
        """Test get_successful_questions_for_run query function."""
        run_id = "test-run-queries"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
            )

            # Add problems with various statuses
            create_problem(session, run_id, "Success 1", status="success")
            create_problem(session, run_id, "Success 2", status="success")
            create_problem(session, run_id, "Failed 1", status="failed")
            create_problem(session, run_id, "Running 1", status="running")

        result = get_successful_questions_for_run(run_id)

        assert len(result) == 2
        assert "Success 1" in result
        assert "Success 2" in result
        assert "Failed 1" not in result
        assert "Running 1" not in result

    def test_get_successful_problems_with_results(self, in_memory_db):
        """Test get_successful_problems_with_results query function."""
        run_id = "test-run-results"
        with in_memory_db.session_scope() as session:
            create_run(
                session=session,
                id=run_id,
                mode="leetcode",
                subject="leetcode",
                card_type="standard",
            )

            # Add successful problem with result
            p = create_problem(session, run_id, "Two Sum", status="success")
            update_problem(
                session,
                p.id,
                final_result=json.dumps({
                    "title": "Two Sum",
                    "difficulty": "Easy",
                    "cards": [
                        {"front": "Q1", "back": "A1", "card_type": "Basic"},
                        {"front": "Q2", "back": "A2", "card_type": "Code"},
                    ]
                }),
            )

        result = get_successful_problems_with_results(run_id)

        assert len(result) == 1
        assert result[0]["title"] == "Two Sum"
        assert result[0]["difficulty"] == "Easy"
        assert len(result[0]["cards"]) == 2
