"""Tests for ConcurrentTaskRunner in src/task_runner.py."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.task_runner import ConcurrentTaskRunner, Success, Failure


class TestSuccessAndFailure:
    """Tests for Success and Failure result types."""

    def test_success_creation(self):
        """Test creating a Success result."""
        result = Success(value="test_value")
        assert result.value == "test_value"

    def test_success_is_success(self):
        """Test Success.is_success returns True."""
        result = Success(value=42)
        assert result.is_success() is True
        assert result.is_failure() is False

    def test_failure_creation(self):
        """Test creating a Failure result."""
        exception = ValueError("test error")
        result = Failure(exception=exception)
        assert result.exception == exception

    def test_failure_is_failure(self):
        """Test Failure.is_failure returns True."""
        result = Failure(exception=Exception("error"))
        assert result.is_failure() is True
        assert result.is_success() is False

    def test_success_with_none_value(self):
        """Test Success with None value."""
        result = Success(value=None)
        assert result.value is None
        assert result.is_success() is True

    def test_success_with_complex_value(self):
        """Test Success with complex value."""
        data = {"cards": [1, 2, 3], "nested": {"key": "value"}}
        result = Success(value=data)
        assert result.value == data

    def test_success_is_frozen(self):
        """Test that Success is immutable (frozen dataclass)."""
        result = Success(value="test")
        with pytest.raises(AttributeError):
            result.value = "new_value"

    def test_failure_is_frozen(self):
        """Test that Failure is immutable (frozen dataclass)."""
        result = Failure(exception=Exception("test"))
        with pytest.raises(AttributeError):
            result.exception = Exception("new")


class TestConcurrentTaskRunner:
    """Tests for ConcurrentTaskRunner class."""

    @pytest.mark.asyncio
    async def test_run_all_single_task(self):
        """Test running a single task."""
        async def task():
            return "result"

        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([task])

        assert len(results) == 1
        assert isinstance(results[0], Success)
        assert results[0].value == "result"

    @pytest.mark.asyncio
    async def test_run_all_multiple_tasks(self):
        """Test running multiple tasks."""
        async def task1():
            return 1

        async def task2():
            return 2

        async def task3():
            return 3

        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([task1, task2, task3])

        assert len(results) == 3
        values = [r.value for r in results if isinstance(r, Success)]
        assert set(values) == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_run_all_with_failure(self):
        """Test running tasks where one fails."""
        async def success_task():
            return "success"

        async def failing_task():
            raise ValueError("test error")

        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([success_task, failing_task])

        assert len(results) == 2
        successes = [r for r in results if isinstance(r, Success)]
        failures = [r for r in results if isinstance(r, Failure)]
        assert len(successes) == 1
        assert len(failures) == 1
        assert isinstance(failures[0].exception, ValueError)

    @pytest.mark.asyncio
    async def test_run_all_respects_concurrency_limit(self):
        """Test that concurrency limit is respected."""
        concurrent_count = 0
        max_concurrent_seen = 0

        async def counting_task():
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return True

        tasks = [counting_task for _ in range(10)]
        runner = ConcurrentTaskRunner(max_concurrent=3)
        await runner.run_all(tasks)

        # Max concurrent should not exceed the limit
        assert max_concurrent_seen <= 3

    @pytest.mark.asyncio
    async def test_run_all_with_request_delay(self):
        """Test that request delay is applied between task scheduling."""
        call_count = 0

        async def counting_task():
            nonlocal call_count
            call_count += 1
            return call_count

        tasks = [counting_task for _ in range(3)]
        runner = ConcurrentTaskRunner(max_concurrent=10, request_delay=0.01)
        results = await runner.run_all(tasks)

        # All tasks should complete
        assert len(results) == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_run_all_empty_task_list(self):
        """Test running with empty task list."""
        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([])
        assert results == []

    @pytest.mark.asyncio
    async def test_run_all_ordered_preserves_order(self):
        """Test that run_all_ordered preserves task order in results."""
        async def make_task(value, delay):
            async def task():
                await asyncio.sleep(delay)
                return value
            return task

        # Create tasks with different delays to ensure they complete in different order
        task1 = await make_task(1, 0.05)
        task2 = await make_task(2, 0.01)  # Completes faster
        task3 = await make_task(3, 0.03)

        runner = ConcurrentTaskRunner(max_concurrent=10)
        results = await runner.run_all_ordered([task1, task2, task3])

        # Results should be in same order as input, not completion order
        assert len(results) == 3
        assert results[0].value == 1
        assert results[1].value == 2
        assert results[2].value == 3

    @pytest.mark.asyncio
    async def test_run_all_ordered_with_failure(self):
        """Test run_all_ordered handles failures correctly."""
        async def success():
            return "ok"

        async def failure():
            raise RuntimeError("fail")

        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all_ordered([success, failure, success])

        assert len(results) == 3
        assert isinstance(results[0], Success)
        assert isinstance(results[1], Failure)
        assert isinstance(results[2], Success)

    @pytest.mark.asyncio
    async def test_run_all_no_delay_for_last_task(self):
        """Test that no delay is added after the last task."""
        start_times = []
        end_time = None

        async def timing_task():
            start_times.append(asyncio.get_event_loop().time())
            return True

        tasks = [timing_task for _ in range(2)]
        runner = ConcurrentTaskRunner(max_concurrent=10, request_delay=0.1)

        start = asyncio.get_event_loop().time()
        await runner.run_all(tasks)
        end = asyncio.get_event_loop().time()

        # Should have delay between first and second, but not after second
        # Total time should be ~0.1s (one delay), not ~0.2s (two delays)
        assert end - start < 0.2

    @pytest.mark.asyncio
    async def test_default_values(self):
        """Test ConcurrentTaskRunner default values."""
        runner = ConcurrentTaskRunner()
        assert runner.max_concurrent == 8
        assert runner.request_delay == 0.0

    @pytest.mark.asyncio
    async def test_custom_concurrency(self):
        """Test ConcurrentTaskRunner with custom concurrency."""
        runner = ConcurrentTaskRunner(max_concurrent=16, request_delay=0.5)
        assert runner.max_concurrent == 16
        assert runner.request_delay == 0.5

    @pytest.mark.asyncio
    async def test_all_tasks_complete_on_failure(self):
        """Test that all tasks complete even when some fail."""
        completed = []

        async def task1():
            completed.append(1)
            return 1

        async def task2():
            completed.append(2)
            raise ValueError("error")

        async def task3():
            completed.append(3)
            return 3

        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([task1, task2, task3])

        assert len(results) == 3
        assert set(completed) == {1, 2, 3}
