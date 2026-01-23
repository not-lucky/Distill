"""Tests for progress visualization module."""

import time
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from src.progress import (
    ProgressTracker,
    ProviderStats,
    ProviderStatus,
    TOKEN_PRICING,
)
from src.providers.base import TokenUsage


class TestProviderStatus:
    """Tests for ProviderStatus enum."""

    def test_status_values(self):
        assert ProviderStatus.PENDING.value == "pending"
        assert ProviderStatus.RUNNING.value == "running"
        assert ProviderStatus.SUCCESS.value == "success"
        assert ProviderStatus.FAILED.value == "failed"


class TestProviderStats:
    """Tests for ProviderStats dataclass."""

    def test_creation_with_defaults(self):
        stats = ProviderStats(name="test", model="gpt-4")
        assert stats.name == "test"
        assert stats.model == "gpt-4"
        assert stats.status == ProviderStatus.PENDING
        assert stats.requests_total == 0
        assert stats.requests_success == 0
        assert stats.requests_failed == 0
        assert stats.tokens_input == 0
        assert stats.tokens_output == 0
        assert stats.estimated_cost == 0.0

    def test_status_icon_pending(self):
        stats = ProviderStats(name="test", model="gpt-4", status=ProviderStatus.PENDING)
        assert stats.status_icon == "⏳"

    def test_status_icon_running(self):
        stats = ProviderStats(name="test", model="gpt-4", status=ProviderStatus.RUNNING)
        assert stats.status_icon == "🔄"

    def test_status_icon_success(self):
        stats = ProviderStats(name="test", model="gpt-4", status=ProviderStatus.SUCCESS)
        assert stats.status_icon == "✓"

    def test_status_icon_failed(self):
        stats = ProviderStats(name="test", model="gpt-4", status=ProviderStatus.FAILED)
        assert stats.status_icon == "✗"

    def test_status_style_pending(self):
        stats = ProviderStats(name="test", model="gpt-4", status=ProviderStatus.PENDING)
        assert stats.status_style == "dim"

    def test_status_style_success(self):
        stats = ProviderStats(name="test", model="gpt-4", status=ProviderStatus.SUCCESS)
        assert stats.status_style == "green"

    def test_status_style_failed(self):
        stats = ProviderStats(name="test", model="gpt-4", status=ProviderStatus.FAILED)
        assert stats.status_style == "red"


class TestTokenPricing:
    """Tests for token pricing configuration."""

    def test_has_cerebras_pricing(self):
        assert "cerebras" in TOKEN_PRICING
        assert len(TOKEN_PRICING["cerebras"]) == 2

    def test_has_google_genai_pricing(self):
        assert "google_genai" in TOKEN_PRICING

    def test_antigravity_is_free(self):
        assert TOKEN_PRICING["google_antigravity"] == (0.0, 0.0)


class TestProgressTracker:
    """Tests for ProgressTracker class."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console that doesn't output."""
        return Console(file=StringIO(), force_terminal=True)

    @pytest.fixture
    def tracker(self, mock_console):
        """Create a tracker with mock console."""
        return ProgressTracker(
            total_questions=10,
            provider_names=[("cerebras", "llama-70b"), ("google_genai", "gemini-pro")],
            console=mock_console,
        )

    def test_initialization(self, tracker):
        assert tracker.total_questions == 10
        assert tracker.completed_questions == 0
        assert tracker.failed_questions == 0
        assert tracker.current_question is None
        assert len(tracker.providers) == 2
        assert "cerebras/llama-70b" in tracker.providers
        assert "google_genai/gemini-pro" in tracker.providers

    def test_start_and_stop(self, tracker):
        tracker.start()
        assert tracker.live is not None
        assert tracker.task_id is not None
        assert tracker.start_time is not None
        tracker.stop()
        assert tracker.live is None

    def test_start_question(self, tracker):
        tracker.start()
        tracker.start_question("Two Sum")
        assert tracker.current_question == "Two Sum"
        tracker.stop()

    def test_complete_question_success(self, tracker):
        tracker.start()
        tracker.start_question("Two Sum")
        tracker.complete_question("Two Sum", success=True, duration=5.0)
        assert tracker.completed_questions == 1
        assert tracker.failed_questions == 0
        assert len(tracker.question_times) == 1
        assert tracker.question_times[0] == 5.0
        tracker.stop()

    def test_complete_question_failure(self, tracker):
        tracker.start()
        tracker.start_question("Two Sum")
        tracker.complete_question("Two Sum", success=False, duration=3.0)
        assert tracker.completed_questions == 0
        assert tracker.failed_questions == 1
        tracker.stop()

    def test_update_provider_status(self, tracker):
        tracker.start()
        tracker.update_provider_status(
            provider_name="cerebras",
            model="llama-70b",
            status=ProviderStatus.SUCCESS,
            success=True,
            tokens_input=100,
            tokens_output=200,
        )
        stats = tracker.providers["cerebras/llama-70b"]
        assert stats.status == ProviderStatus.SUCCESS
        assert stats.requests_total == 1
        assert stats.requests_success == 1
        assert stats.tokens_input == 100
        assert stats.tokens_output == 200
        tracker.stop()

    def test_update_provider_status_failure(self, tracker):
        tracker.start()
        tracker.update_provider_status(
            provider_name="cerebras",
            model="llama-70b",
            status=ProviderStatus.FAILED,
            success=False,
        )
        stats = tracker.providers["cerebras/llama-70b"]
        assert stats.requests_failed == 1
        tracker.stop()

    def test_cost_calculation(self, tracker):
        tracker.start()
        # Cerebras pricing: $0.60 per 1M input, $0.60 per 1M output
        tracker.update_provider_status(
            provider_name="cerebras",
            model="llama-70b",
            status=ProviderStatus.SUCCESS,
            success=True,
            tokens_input=1_000_000,  # 1M tokens
            tokens_output=1_000_000,  # 1M tokens
        )
        stats = tracker.providers["cerebras/llama-70b"]
        # Expected: $0.60 + $0.60 = $1.20
        assert stats.estimated_cost == pytest.approx(1.2, abs=0.01)
        tracker.stop()

    def test_eta_calculation_initial(self, tracker):
        eta = tracker._calculate_eta()
        assert eta == "calculating..."

    def test_eta_calculation_with_data(self, tracker):
        tracker.start()
        tracker.completed_questions = 5
        tracker.question_times = [10.0, 12.0, 8.0, 11.0, 9.0]  # avg = 10
        eta = tracker._calculate_eta()
        # 5 remaining * 10s avg = 50s
        assert "50" in eta or "0." in eta  # Could be "50s" or "0.8m"
        tracker.stop()

    def test_rolling_average_window(self, tracker):
        tracker.start()
        # Add more than 10 times
        for i in range(15):
            tracker.complete_question(f"Q{i}", success=True, duration=float(i))
        # Should only keep last 10
        assert len(tracker.question_times) == 10
        assert tracker.question_times[0] == 5.0  # First of last 10
        tracker.stop()

    def test_get_summary(self, tracker):
        tracker.start()
        tracker.complete_question("Q1", success=True, duration=5.0)
        tracker.complete_question("Q2", success=False, duration=3.0)
        tracker.update_provider_status(
            "cerebras", "llama-70b", ProviderStatus.SUCCESS, True, 100, 200
        )
        
        summary = tracker.get_summary()
        
        assert summary["total_questions"] == 10
        assert summary["completed_questions"] == 1
        assert summary["failed_questions"] == 1
        assert summary["total_time_seconds"] > 0
        assert "cerebras/llama-70b" in summary["providers"]
        tracker.stop()

    def test_new_provider_added_dynamically(self, tracker):
        tracker.start()
        # Add a provider that wasn't in initial list
        tracker.update_provider_status(
            provider_name="new_provider",
            model="new-model",
            status=ProviderStatus.SUCCESS,
            success=True,
        )
        assert "new_provider/new-model" in tracker.providers
        tracker.stop()


class TestProgressTrackerEdgeCases:
    """Edge case tests for ProgressTracker."""

    @pytest.fixture
    def mock_console(self):
        return Console(file=StringIO(), force_terminal=True)

    def test_zero_questions(self, mock_console):
        tracker = ProgressTracker(
            total_questions=0,
            provider_names=[],
            console=mock_console,
        )
        assert tracker.total_questions == 0
        tracker.start()
        summary = tracker.get_summary()
        assert summary["total_questions"] == 0
        tracker.stop()

    def test_single_provider(self, mock_console):
        tracker = ProgressTracker(
            total_questions=1,
            provider_names=[("solo", "model")],
            console=mock_console,
        )
        assert len(tracker.providers) == 1
        tracker.start()
        tracker.stop()

    def test_long_question_name(self, mock_console):
        tracker = ProgressTracker(
            total_questions=1,
            provider_names=[("p", "m")],
            console=mock_console,
        )
        tracker.start()
        long_name = "A" * 200
        tracker.start_question(long_name)
        assert tracker.current_question == long_name
        tracker.stop()

    def test_unicode_in_question_name(self, mock_console):
        tracker = ProgressTracker(
            total_questions=1,
            provider_names=[("p", "m")],
            console=mock_console,
        )
        tracker.start()
        tracker.start_question("二分搜索 🔍")
        assert tracker.current_question == "二分搜索 🔍"
        tracker.stop()

    def test_stop_without_start(self, mock_console):
        tracker = ProgressTracker(
            total_questions=1,
            provider_names=[("p", "m")],
            console=mock_console,
        )
        # Should not raise
        tracker.stop()

    def test_unknown_provider_pricing(self, mock_console):
        tracker = ProgressTracker(
            total_questions=1,
            provider_names=[("unknown_provider", "model")],
            console=mock_console,
        )
        tracker.start()
        tracker.update_provider_status(
            "unknown_provider", "model", ProviderStatus.SUCCESS, True, 1000, 1000
        )
        # Should use 0 pricing for unknown provider
        stats = tracker.providers["unknown_provider/model"]
        assert stats.estimated_cost == 0.0
        tracker.stop()
