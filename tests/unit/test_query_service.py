"""Unit tests for the query service."""

import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from src.services.query import (
    QueryService,
    QueryResult,
    _format_datetime,
    _truncate,
    _format_table,
)


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestFormatDatetime:
    """Tests for _format_datetime helper."""

    def test_formats_datetime_correctly(self):
        dt = datetime(2026, 1, 14, 12, 30, 0)
        result = _format_datetime(dt)
        assert result == "2026-01-14 12:30"

    def test_returns_dash_for_none(self):
        result = _format_datetime(None)
        assert result == "-"


class TestTruncate:
    """Tests for _truncate helper."""

    def test_returns_short_text_unchanged(self):
        result = _truncate("hello", 10)
        assert result == "hello"

    def test_truncates_long_text_with_ellipsis(self):
        result = _truncate("hello world this is long", 10)
        assert result == "hello w..."
        assert len(result) == 10

    def test_handles_exact_length(self):
        result = _truncate("hello", 5)
        assert result == "hello"

    def test_uses_default_max_len(self):
        short_text = "x" * 30
        result = _truncate(short_text)
        assert result == short_text

        long_text = "x" * 60
        result = _truncate(long_text)
        assert len(result) == 50
        assert result.endswith("...")


class TestFormatTable:
    """Tests for _format_table helper."""

    def test_formats_simple_table(self):
        headers = ["Name", "Age"]
        rows = [["Alice", "30"], ["Bob", "25"]]
        result = _format_table(headers, rows)

        assert "Name" in result
        assert "Age" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "---" in result  # Separator

    def test_returns_message_for_empty_rows(self):
        headers = ["Name", "Age"]
        rows = []
        result = _format_table(headers, rows)
        assert result == "No results found."

    def test_handles_varying_column_widths(self):
        headers = ["ID", "Very Long Header Name"]
        rows = [["1", "short"], ["2", "much longer content here"]]
        result = _format_table(headers, rows)

        lines = result.split("\n")
        # All content lines should have consistent structure
        assert len(lines) >= 3  # Header, separator, rows

    def test_pads_short_rows(self):
        headers = ["A", "B", "C"]
        rows = [["1", "2"]]  # Missing column C
        result = _format_table(headers, rows)
        # Should not raise an error
        assert "A" in result


# ============================================================================
# QueryResult Tests
# ============================================================================


class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_successful_result(self):
        result = QueryResult(success=True, data="test data")
        assert result.success is True
        assert result.data == "test data"
        assert result.error is None

    def test_failed_result(self):
        result = QueryResult(success=False, data=None, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_result_with_message(self):
        result = QueryResult(success=True, data="data", message="Found 5 items")
        assert result.message == "Found 5 items"


# ============================================================================
# QueryService Tests
# ============================================================================


class TestQueryServiceListRuns:
    """Tests for QueryService.list_runs method."""

    @patch("src.services.query.queries.get_runs_summary")
    def test_list_runs_table_format(self, mock_get_runs):
        mock_get_runs.return_value = [
            {
                "id": "abc12345-6789-0000-0000-000000000000",
                "subject": "leetcode",
                "card_type": "standard",
                "status": "completed",
                "user_label": None,
                "created_at": "2026-01-14T12:30:00",
                "completed_at": "2026-01-14T13:00:00",
                "total_problems": 10,
                "successful_problems": 10,
                "failed_problems": 0,
                "card_count": 150,
            }
        ]

        service = QueryService()
        result = service.list_runs(limit=10, output_format="table")

        assert result.success is True
        assert "abc12345" in result.data
        assert "leetcode" in result.data
        assert "completed" in result.data

    @patch("src.services.query.queries.get_runs_summary")
    def test_list_runs_json_format(self, mock_get_runs):
        mock_get_runs.return_value = [
            {
                "id": "abc12345-6789-0000-0000-000000000000",
                "subject": "cs",
                "card_type": "mcq",
                "status": "completed",
                "user_label": "test",
                "created_at": "2026-01-14T12:30:00",
                "completed_at": None,
                "total_problems": 5,
                "successful_problems": 5,
                "failed_problems": 0,
                "card_count": 50,
            }
        ]

        service = QueryService()
        result = service.list_runs(limit=10, output_format="json")

        assert result.success is True
        data = json.loads(result.data)
        assert "runs" in data
        assert len(data["runs"]) == 1
        assert data["runs"][0]["subject"] == "cs"

    @patch("src.services.query.queries.get_runs_summary")
    def test_list_runs_empty_result(self, mock_get_runs):
        mock_get_runs.return_value = []

        service = QueryService()
        result = service.list_runs(output_format="table")

        assert result.success is True
        assert "No results found" in result.data

    @patch("src.services.query.queries.get_runs_summary")
    def test_list_runs_passes_filters(self, mock_get_runs):
        mock_get_runs.return_value = []

        service = QueryService()
        service.list_runs(subject="leetcode", status="completed", limit=5)

        mock_get_runs.assert_called_once_with(
            limit=5, subject="leetcode", status="completed"
        )


class TestQueryServiceShowRun:
    """Tests for QueryService.show_run method."""

    @patch("src.services.query.queries.get_run_statistics")
    @patch("src.services.query.queries.get_run_by_id")
    def test_show_run_table_format(self, mock_get_run, mock_get_stats):
        mock_run = MagicMock()
        mock_run.id = "abc12345-0000-0000-0000-000000000000"
        mock_get_run.return_value = mock_run

        mock_get_stats.return_value = {
            "run_id": "abc12345-0000-0000-0000-000000000000",
            "subject": "leetcode",
            "card_type": "standard",
            "mode": "leetcode",
            "status": "completed",
            "user_label": None,
            "created_at": "2026-01-14T12:30:00",
            "completed_at": "2026-01-14T13:00:00",
            "total_problems": 10,
            "successful_problems": 10,
            "failed_problems": 0,
            "success_rate": 100.0,
            "total_cards": 150,
            "avg_cards_per_problem": 15.0,
            "avg_processing_time": 30.5,
            "provider_results": {
                "total": 20,
                "successful": 20,
                "failed": 0,
                "by_provider": {
                    "cerebras": {"total": 10, "successful": 10, "avg_cards": 15.0}
                },
            },
        }

        service = QueryService()
        result = service.show_run("abc12345", output_format="table")

        assert result.success is True
        assert "abc12345" in result.data
        assert "leetcode" in result.data
        assert "100.0%" in result.data

    @patch("src.services.query.queries.get_run_by_id")
    def test_show_run_not_found(self, mock_get_run):
        mock_get_run.return_value = None

        service = QueryService()
        result = service.show_run("nonexistent")

        assert result.success is False
        assert "not found" in result.error.lower()


class TestQueryServiceListProblems:
    """Tests for QueryService.list_problems method."""

    @patch("src.services.query.queries.get_problems")
    def test_list_problems_table_format(self, mock_get_problems):
        mock_problem = MagicMock()
        mock_problem.id = 1
        mock_problem.run_id = "abc12345"
        mock_problem.question_name = "Two Sum"
        mock_problem.status = "success"
        mock_problem.final_card_count = 5
        mock_problem.processing_time_seconds = 10.5
        mock_problem.created_at = datetime(2026, 1, 14, 12, 0, tzinfo=timezone.utc)

        mock_get_problems.return_value = [mock_problem]

        service = QueryService()
        result = service.list_problems(output_format="table")

        assert result.success is True
        assert "Two Sum" in result.data
        assert "success" in result.data

    @patch("src.services.query.queries.get_problems")
    def test_list_problems_json_format(self, mock_get_problems):
        mock_problem = MagicMock()
        mock_problem.id = 1
        mock_problem.run_id = "abc12345"
        mock_problem.question_name = "Two Sum"
        mock_problem.category_name = "Arrays"
        mock_problem.status = "success"
        mock_problem.final_card_count = 5
        mock_problem.processing_time_seconds = 10.5
        mock_problem.created_at = datetime(2026, 1, 14, 12, 0, tzinfo=timezone.utc)

        mock_get_problems.return_value = [mock_problem]

        service = QueryService()
        result = service.list_problems(output_format="json")

        assert result.success is True
        data = json.loads(result.data)
        assert "problems" in data
        assert data["problems"][0]["question_name"] == "Two Sum"


class TestQueryServiceListProviders:
    """Tests for QueryService.list_providers method."""

    @patch("src.services.query.queries.get_provider_results")
    def test_list_providers_table_format(self, mock_get_providers):
        mock_result = MagicMock()
        mock_result.id = 1
        mock_result.problem_id = 1
        mock_result.provider_name = "cerebras"
        mock_result.provider_model = "gpt-oss-120b"
        mock_result.success = True
        mock_result.card_count = 10
        mock_result.processing_time_seconds = 5.5
        mock_result.error_message = None
        mock_result.created_at = datetime(2026, 1, 14, 12, 0, tzinfo=timezone.utc)

        mock_get_providers.return_value = [mock_result]

        service = QueryService()
        result = service.list_providers(output_format="table")

        assert result.success is True
        assert "cerebras" in result.data
        assert "gpt-oss-120b" in result.data
        assert "✓" in result.data  # Success checkmark

    @patch("src.services.query.queries.get_provider_results")
    def test_list_providers_filters_by_success(self, mock_get_providers):
        mock_get_providers.return_value = []

        service = QueryService()
        service.list_providers(success=True)

        mock_get_providers.assert_called_with(
            run_id=None, provider_name=None, success=True, limit=20
        )


class TestQueryServiceListCards:
    """Tests for QueryService.list_cards method."""

    @patch("src.services.query.queries.get_cards")
    def test_list_cards_table_format(self, mock_get_cards):
        mock_card = MagicMock()
        mock_card.id = 1
        mock_card.problem_id = 1
        mock_card.card_type = "Algorithm"
        mock_card.front = "What is binary search?"
        mock_card.back = "A search algorithm..."
        mock_card.tags = '["binary", "search"]'
        mock_card.created_at = datetime(2026, 1, 14, 12, 0, tzinfo=timezone.utc)

        mock_get_cards.return_value = [mock_card]

        service = QueryService()
        result = service.list_cards(output_format="table")

        assert result.success is True
        assert "Algorithm" in result.data
        assert "binary search" in result.data

    @patch("src.services.query.queries.get_cards")
    def test_list_cards_with_search(self, mock_get_cards):
        mock_get_cards.return_value = []

        service = QueryService()
        service.list_cards(search_query="binary search", limit=10)

        mock_get_cards.assert_called_with(
            run_id=None, card_type=None, search_query="binary search", limit=10
        )


class TestQueryServiceShowStats:
    """Tests for QueryService.show_stats method."""

    @patch("src.services.query.queries.get_provider_statistics")
    @patch("src.services.query.queries.get_global_statistics")
    def test_show_stats_table_format(self, mock_global_stats, mock_provider_stats):
        mock_global_stats.return_value = {
            "filter_subject": None,
            "runs": {
                "total": 10,
                "completed": 8,
                "failed": 1,
                "running": 1,
                "completion_rate": 80.0,
            },
            "problems": {
                "total": 100,
                "successful": 90,
                "failed": 10,
                "success_rate": 90.0,
                "avg_processing_time": 30.5,
            },
            "cards": {
                "total": 1500,
                "avg_per_problem": 16.7,
            },
            "by_subject": {
                "leetcode": {"runs": 5, "cards": 800},
                "cs": {"runs": 5, "cards": 700},
            },
        }
        mock_provider_stats.return_value = {
            "providers": {
                "cerebras:gpt-oss-120b": {
                    "provider_name": "cerebras",
                    "model": "gpt-oss-120b",
                    "total_requests": 50,
                    "successful": 48,
                    "failed": 2,
                    "success_rate": 96.0,
                }
            }
        }

        service = QueryService()
        result = service.show_stats(output_format="table")

        assert result.success is True
        assert "Global Statistics" in result.data
        assert "Total:" in result.data
        assert "80.0%" in result.data  # Completion rate

    @patch("src.services.query.queries.get_provider_statistics")
    @patch("src.services.query.queries.get_global_statistics")
    def test_show_stats_json_format(self, mock_global_stats, mock_provider_stats):
        mock_global_stats.return_value = {
            "filter_subject": None,
            "runs": {"total": 10, "completed": 8, "failed": 1, "running": 1, "completion_rate": 80.0},
            "problems": {"total": 100, "successful": 90, "failed": 10, "success_rate": 90.0, "avg_processing_time": 30.5},
            "cards": {"total": 1500, "avg_per_problem": 16.7},
            "by_subject": {},
        }
        mock_provider_stats.return_value = {"providers": {}}

        service = QueryService()
        result = service.show_stats(output_format="json")

        assert result.success is True
        data = json.loads(result.data)
        assert "runs" in data
        assert data["runs"]["total"] == 10

    @patch("src.services.query.queries.get_provider_statistics")
    @patch("src.services.query.queries.get_global_statistics")
    def test_show_stats_with_subject_filter(self, mock_global_stats, mock_provider_stats):
        mock_global_stats.return_value = {
            "filter_subject": "leetcode",
            "runs": {"total": 5, "completed": 5, "failed": 0, "running": 0, "completion_rate": 100.0},
            "problems": {"total": 50, "successful": 50, "failed": 0, "success_rate": 100.0, "avg_processing_time": 25.0},
            "cards": {"total": 800, "avg_per_problem": 16.0},
            "by_subject": {},
        }
        mock_provider_stats.return_value = {"providers": {}}

        service = QueryService()
        result = service.show_stats(subject="leetcode", output_format="table")

        assert result.success is True
        assert "leetcode" in result.data


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestQueryServiceErrorHandling:
    """Tests for error handling in QueryService."""

    @patch("src.services.query.queries.get_runs_summary")
    def test_handles_database_error(self, mock_get_runs):
        mock_get_runs.side_effect = Exception("Database connection failed")

        service = QueryService()
        result = service.list_runs()

        assert result.success is False
        assert "Database connection failed" in result.error

    @patch("src.services.query.queries.get_global_statistics")
    def test_handles_stats_error(self, mock_get_stats):
        mock_get_stats.side_effect = Exception("Query failed")

        service = QueryService()
        result = service.show_stats()

        assert result.success is False
        assert "Query failed" in result.error
