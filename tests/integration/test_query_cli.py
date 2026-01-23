"""Integration tests for query CLI commands."""

import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from src.cli import main
from src.database import DatabaseManager, Base


@pytest.fixture
def mock_db_with_data(memory_db):
    """Create a mock database with test data."""
    from src.database import Run, Problem, Card, ProviderResult

    with memory_db.session_scope() as session:
        # Create a test run
        run = Run(
            id="test-run-12345678-0000-0000-0000-000000000000",
            mode="leetcode",
            subject="leetcode",
            card_type="standard",
            status="completed",
            total_problems=2,
            successful_problems=2,
            failed_problems=0,
            created_at=datetime(2026, 1, 14, 12, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 1, 14, 12, 30, tzinfo=timezone.utc),
        )
        session.add(run)
        session.flush()

        # Create test problems
        problem1 = Problem(
            run_id=run.id,
            question_name="Two Sum",
            sanitized_name="two_sum",
            category_name="Arrays",
            status="success",
            final_card_count=3,
            processing_time_seconds=15.5,
            created_at=datetime(2026, 1, 14, 12, 5, tzinfo=timezone.utc),
        )
        problem2 = Problem(
            run_id=run.id,
            question_name="Binary Search",
            sanitized_name="binary_search",
            category_name="Search",
            status="success",
            final_card_count=4,
            processing_time_seconds=20.0,
            created_at=datetime(2026, 1, 14, 12, 10, tzinfo=timezone.utc),
        )
        session.add(problem1)
        session.add(problem2)
        session.flush()

        # Create test cards
        for i, (problem, texts) in enumerate([
            (problem1, ["What is Two Sum?", "Describe the approach"]),
            (problem2, ["What is Binary Search?", "Time complexity"]),
        ]):
            for j, text in enumerate(texts):
                card = Card(
                    problem_id=problem.id,
                    run_id=run.id,
                    card_index=j,
                    card_type="Algorithm",
                    front=text,
                    back=f"Answer for: {text}",
                    tags=json.dumps(["test", "algorithm"]),
                    created_at=datetime(2026, 1, 14, 12, 15, tzinfo=timezone.utc),
                )
                session.add(card)

        # Create provider results
        for problem in [problem1, problem2]:
            pr = ProviderResult(
                problem_id=problem.id,
                run_id=run.id,
                provider_name="test_provider",
                provider_model="test-model",
                success=True,
                card_count=3,
                processing_time_seconds=5.0,
                created_at=datetime(2026, 1, 14, 12, 5, tzinfo=timezone.utc),
            )
            session.add(pr)

        session.commit()

    return memory_db


class TestQueryRunsCLI:
    """Tests for 'query runs' CLI command."""

    def test_query_runs_shows_table(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "runs"])

        assert result == 0
        captured = capsys.readouterr()
        assert "test-run" in captured.out or "leetcode" in captured.out

    def test_query_runs_with_limit(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "runs", "--limit", "1"])

        assert result == 0

    def test_query_runs_json_format(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "runs", "--format", "json"])

        assert result == 0
        captured = capsys.readouterr()
        # The output contains a "Found X run(s)" message before the JSON
        # Extract the JSON part (starts with {)
        output = captured.out
        json_start = output.find("{")
        if json_start >= 0:
            json_part = output[json_start:]
            data = json.loads(json_part)
            assert "runs" in data
        else:
            # No data case - should have empty runs
            assert "No results" in output or "Found 0" in output

    def test_query_runs_filter_by_subject(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "runs", "--subject", "leetcode"])

        assert result == 0


class TestQueryRunCLI:
    """Tests for 'query run <id>' CLI command."""

    def test_query_run_shows_details(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "run", "test-run"])

        assert result == 0
        captured = capsys.readouterr()
        assert "leetcode" in captured.out
        assert "Statistics" in captured.out

    def test_query_run_not_found(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "run", "nonexistent-run-id"])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "error" in captured.out.lower()


class TestQueryProblemsCLI:
    """Tests for 'query problems' CLI command."""

    def test_query_problems_shows_table(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "problems"])

        assert result == 0
        captured = capsys.readouterr()
        assert "Two Sum" in captured.out or "Binary Search" in captured.out

    def test_query_problems_with_search(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "problems", "--search", "Binary"])

        assert result == 0

    def test_query_problems_json_format(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "problems", "--format", "json"])

        assert result == 0


class TestQueryProvidersCLI:
    """Tests for 'query providers' CLI command."""

    def test_query_providers_shows_table(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "providers"])

        assert result == 0
        captured = capsys.readouterr()
        assert "test_provider" in captured.out or "test-model" in captured.out

    def test_query_providers_filter_success(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "providers", "--success"])

        assert result == 0

    def test_query_providers_filter_failed(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "providers", "--failed"])

        assert result == 0


class TestQueryCardsCLI:
    """Tests for 'query cards' CLI command."""

    def test_query_cards_shows_table(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "cards"])

        assert result == 0

    def test_query_cards_with_search(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "cards", "--search", "Binary"])

        assert result == 0
        captured = capsys.readouterr()
        # Should find cards containing "Binary"
        assert "Binary" in captured.out or "Found" in captured.out

    def test_query_cards_filter_by_type(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "cards", "--type", "Algorithm"])

        assert result == 0


class TestQueryStatsCLI:
    """Tests for 'query stats' CLI command."""

    def test_query_stats_shows_statistics(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "stats"])

        assert result == 0
        captured = capsys.readouterr()
        assert "Statistics" in captured.out or "Total" in captured.out

    def test_query_stats_filter_by_subject(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "stats", "--subject", "leetcode"])

        assert result == 0

    def test_query_stats_json_format(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query", "stats", "--format", "json"])

        assert result == 0
        captured = capsys.readouterr()
        # Should be valid JSON
        assert '"runs"' in captured.out or '"problems"' in captured.out


class TestQueryCLINoSubcommand:
    """Tests for 'query' command without subcommand."""

    def test_query_without_subcommand_shows_usage(self, mock_db_with_data, capsys):
        with patch.object(DatabaseManager, "get_default", return_value=mock_db_with_data):
            result = main(["query"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Usage" in captured.out or "usage" in captured.out.lower()


class TestQueryCLIHelp:
    """Tests for query help messages."""

    def test_query_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["query", "--help"])
        assert exc_info.value.code == 0

    def test_query_runs_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["query", "runs", "--help"])
        assert exc_info.value.code == 0

    def test_query_cards_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["query", "cards", "--help"])
        assert exc_info.value.code == 0
