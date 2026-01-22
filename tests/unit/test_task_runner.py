"""Tests for ConcurrentTaskRunner in src/task_runner.py."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from assertpy import assert_that

from src.task_runner import ConcurrentTaskRunner, Success, Failure


class TestSuccessAndFailure:
    """Tests for Success and Failure result types."""

    def test_success_creation(self):
        """
        Given a value
        When Success is created
        Then value is stored correctly
        """
        result = Success(value="test_value")
        assert_that(result.value).is_equal_to("test_value")

    def test_success_is_success(self):
        """
        Given a Success result
        When checking result type
        Then is_success returns True and is_failure returns False
        """
        result = Success(value=42)
        assert_that(result.is_success()).is_true()
        assert_that(result.is_failure()).is_false()

    def test_failure_creation(self):
        """
        Given an exception
        When Failure is created
        Then exception is stored correctly
        """
        exception = ValueError("test error")
        result = Failure(exception=exception)
        assert_that(result.exception).is_equal_to(exception)

    def test_failure_is_failure(self):
        """
        Given a Failure result
        When checking result type
        Then is_failure returns True and is_success returns False
        """
        result = Failure(exception=Exception("error"))
        assert_that(result.is_failure()).is_true()
        assert_that(result.is_success()).is_false()

    def test_success_with_none_value(self):
        """
        Given None as value
        When Success is created
        Then None is stored and is_success is True
        """
        result = Success(value=None)
        assert_that(result.value).is_none()
        assert_that(result.is_success()).is_true()

    def test_success_with_complex_value(self):
        """
        Given a complex nested value
        When Success is created
        Then entire value is preserved
        """
        data = {"cards": [1, 2, 3], "nested": {"key": "value"}}
        result = Success(value=data)
        assert_that(result.value).is_equal_to(data)

    def test_success_is_frozen(self):
        """
        Given a Success result
        When attempting to modify value
        Then AttributeError is raised
        """
        result = Success(value="test")
        with pytest.raises(AttributeError):
            result.value = "new_value"

    def test_failure_is_frozen(self):
        """
        Given a Failure result
        When attempting to modify exception
        Then AttributeError is raised
        """
        result = Failure(exception=Exception("test"))
        with pytest.raises(AttributeError):
            result.exception = Exception("new")


class TestConcurrentTaskRunner:
    """Tests for ConcurrentTaskRunner class."""

    @pytest.mark.asyncio
    async def test_run_all_single_task(self):
        """
        Given a single async task
        When run_all is called
        Then one Success result is returned
        """
        async def task():
            return "result"

        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([task])

        assert_that(results).is_length(1)
        assert_that(results[0]).is_instance_of(Success)
        assert_that(results[0].value).is_equal_to("result")

    @pytest.mark.asyncio
    async def test_run_all_multiple_tasks(self):
        """
        Given multiple async tasks
        When run_all is called
        Then all results are collected
        """
        async def task1():
            return 1

        async def task2():
            return 2

        async def task3():
            return 3

        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([task1, task2, task3])

        assert_that(results).is_length(3)
        values = [r.value for r in results if isinstance(r, Success)]
        assert_that(set(values)).is_equal_to({1, 2, 3})

    @pytest.mark.asyncio
    async def test_run_all_with_failure(self):
        """
        Given tasks where one fails
        When run_all is called
        Then both Success and Failure results are returned
        """
        async def success_task():
            return "success"

        async def failing_task():
            raise ValueError("test error")

        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([success_task, failing_task])

        assert_that(results).is_length(2)
        successes = [r for r in results if isinstance(r, Success)]
        failures = [r for r in results if isinstance(r, Failure)]
        assert_that(successes).is_length(1)
        assert_that(failures).is_length(1)
        assert_that(failures[0].exception).is_instance_of(ValueError)

    @pytest.mark.asyncio
    async def test_run_all_respects_concurrency_limit(self):
        """
        Given more tasks than concurrency limit
        When run_all is called
        Then concurrent execution stays within limit
        """
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

        assert_that(max_concurrent_seen).is_less_than_or_equal_to(3)

    @pytest.mark.asyncio
    async def test_run_all_with_request_delay(self):
        """
        Given a request delay configuration
        When run_all is called
        Then all tasks complete with delay applied
        """
        call_count = 0

        async def counting_task():
            nonlocal call_count
            call_count += 1
            return call_count

        tasks = [counting_task for _ in range(3)]
        runner = ConcurrentTaskRunner(max_concurrent=10, request_delay=0.01)
        results = await runner.run_all(tasks)

        assert_that(results).is_length(3)
        assert_that(call_count).is_equal_to(3)

    @pytest.mark.asyncio
    async def test_run_all_empty_task_list(self):
        """
        Given an empty task list
        When run_all is called
        Then empty results list is returned
        """
        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([])
        assert_that(results).is_empty()

    @pytest.mark.asyncio
    async def test_run_all_ordered_preserves_order(self):
        """
        Given tasks with different completion times
        When run_all_ordered is called
        Then results are in original task order
        """
        async def make_task(value, delay):
            async def task():
                await asyncio.sleep(delay)
                return value
            return task

        task1 = await make_task(1, 0.05)
        task2 = await make_task(2, 0.01)  # Completes faster
        task3 = await make_task(3, 0.03)

        runner = ConcurrentTaskRunner(max_concurrent=10)
        results = await runner.run_all_ordered([task1, task2, task3])

        assert_that(results).is_length(3)
        assert_that(results[0].value).is_equal_to(1)
        assert_that(results[1].value).is_equal_to(2)
        assert_that(results[2].value).is_equal_to(3)

    @pytest.mark.asyncio
    async def test_run_all_ordered_with_failure(self):
        """
        Given tasks where one fails
        When run_all_ordered is called
        Then failure is at correct position in results
        """
        async def success():
            return "ok"

        async def failure():
            raise RuntimeError("fail")

        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all_ordered([success, failure, success])

        assert_that(results).is_length(3)
        assert_that(results[0]).is_instance_of(Success)
        assert_that(results[1]).is_instance_of(Failure)
        assert_that(results[2]).is_instance_of(Success)

    @pytest.mark.asyncio
    async def test_run_all_no_delay_for_last_task(self):
        """
        Given a request delay and multiple tasks
        When run_all is called
        Then no delay is added after the last task
        """
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

        assert_that(end - start).is_less_than(0.2)

    @pytest.mark.asyncio
    async def test_default_values(self):
        """
        Given no constructor arguments
        When ConcurrentTaskRunner is created
        Then defaults are applied correctly
        """
        runner = ConcurrentTaskRunner()
        assert_that(runner.max_concurrent).is_equal_to(8)
        assert_that(runner.request_delay).is_equal_to(0.0)

    @pytest.mark.asyncio
    async def test_custom_concurrency(self):
        """
        Given custom concurrency settings
        When ConcurrentTaskRunner is created
        Then custom values are stored
        """
        runner = ConcurrentTaskRunner(max_concurrent=16, request_delay=0.5)
        assert_that(runner.max_concurrent).is_equal_to(16)
        assert_that(runner.request_delay).is_equal_to(0.5)

    @pytest.mark.asyncio
    async def test_all_tasks_complete_on_failure(self):
        """
        Given tasks where one fails
        When run_all is called
        Then all tasks including failures complete
        """
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

        assert_that(results).is_length(3)
        assert_that(set(completed)).is_equal_to({1, 2, 3})
