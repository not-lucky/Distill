"""Task runner utilities for concurrent execution."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, List, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class Success(Generic[T]):
    """Represents a successful task result."""

    value: T

    def is_success(self) -> bool:
        return True

    def is_failure(self) -> bool:
        return False


@dataclass(frozen=True)
class Failure:
    """Represents a failed task result."""

    exception: Exception

    def is_success(self) -> bool:
        return False

    def is_failure(self) -> bool:
        return True


Result = Union[Success[T], Failure]


class ConcurrentTaskRunner:
    """
    Runs async tasks with concurrency control.

    Provides a clean interface for running multiple async tasks
    with a configurable concurrency limit using semaphores.
    Supports optional delays between starting each request to prevent rate limiting.
    """

    def __init__(self, max_concurrent: int = 8, request_delay: float = 0.0):
        """
        Initialize the task runner.

        Args:
            max_concurrent: Maximum number of tasks to run concurrently.
            request_delay: Delay in seconds between starting each request within a batch.
        """
        self.max_concurrent = max_concurrent
        self.request_delay = request_delay
        self._semaphore: asyncio.Semaphore = None

    async def run_all(
        self,
        tasks: List[Callable[[], Awaitable[T]]],
    ) -> List[Result[T]]:
        """
        Run all tasks with concurrency control and staggered starts.

        Args:
            tasks: List of async callables (no-argument coroutine functions).

        Returns:
            List of Result objects (Success or Failure) in order of completion.
        """
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        results: List[Result[T]] = []

        async def run_with_semaphore(task: Callable[[], Awaitable[T]]) -> Result[T]:
            async with self._semaphore:
                try:
                    value = await task()
                    result = Success(value)
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    result = Failure(e)
                results.append(result)
                return result

        # Start tasks with optional delay between each
        wrapped_tasks = []
        for i, task in enumerate(tasks):
            wrapped_tasks.append(run_with_semaphore(task))
            # Add delay before starting next task (skip delay after last task)
            if self.request_delay > 0 and i < len(tasks) - 1:
                await asyncio.sleep(self.request_delay)

        await asyncio.gather(*wrapped_tasks)

        return results

    async def run_all_ordered(
        self,
        tasks: List[Callable[[], Awaitable[T]]],
    ) -> List[Result[T]]:
        """
        Run all tasks with concurrency control and staggered starts, preserving order.

        Args:
            tasks: List of async callables.

        Returns:
            List of Result objects (Success or Failure) in the same order as input tasks.
        """
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_with_semaphore(task: Callable[[], Awaitable[T]]) -> Result[T]:
            async with self._semaphore:
                try:
                    value = await task()
                    return Success(value)
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    return Failure(e)

        # Start tasks with optional delay between each
        wrapped_tasks = []
        for i, task in enumerate(tasks):
            wrapped_tasks.append(run_with_semaphore(task))
            # Add delay before starting next task (skip delay after last task)
            if self.request_delay > 0 and i < len(tasks) - 1:
                await asyncio.sleep(self.request_delay)

        return await asyncio.gather(*wrapped_tasks)
