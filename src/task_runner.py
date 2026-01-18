"""Task runner utilities for concurrent execution."""

import asyncio
import logging
from typing import Awaitable, Callable, List, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConcurrentTaskRunner:
    """
    Runs async tasks with concurrency control.

    Provides a clean interface for running multiple async tasks
    with a configurable concurrency limit using semaphores.
    """

    def __init__(self, max_concurrent: int = 8):
        """
        Initialize the task runner.

        Args:
            max_concurrent: Maximum number of tasks to run concurrently.
        """
        self.max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore = None

    async def run_all(
        self,
        tasks: List[Callable[[], Awaitable[T]]],
    ) -> List[T]:
        """
        Run all tasks with concurrency control.

        Args:
            tasks: List of async callables (no-argument coroutine functions).

        Returns:
            List of results from all tasks (in order of completion).
            Failed tasks return None.
        """
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        results: List[T] = []

        async def run_with_semaphore(task: Callable[[], Awaitable[T]]) -> T:
            async with self._semaphore:
                try:
                    result = await task()
                    if result is not None:
                        results.append(result)
                    return result
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    return None

        wrapped_tasks = [run_with_semaphore(task) for task in tasks]
        await asyncio.gather(*wrapped_tasks)

        return results

    async def run_all_ordered(
        self,
        tasks: List[Callable[[], Awaitable[T]]],
    ) -> List[T]:
        """
        Run all tasks with concurrency control, preserving order.

        Args:
            tasks: List of async callables.

        Returns:
            List of results in the same order as input tasks.
            Failed tasks return None in their position.
        """
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_with_semaphore(task: Callable[[], Awaitable[T]]) -> T:
            async with self._semaphore:
                try:
                    return await task()
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    return None

        wrapped_tasks = [run_with_semaphore(task) for task in tasks]
        return await asyncio.gather(*wrapped_tasks)
