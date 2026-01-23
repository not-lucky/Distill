"""Task runner utilities for concurrent execution."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class TaskInfo:
    """Information about a task for progress tracking."""
    index: int
    name: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


# Callback type for task completion
TaskCallback = Callable[[TaskInfo, bool], None]  # (task_info, success) -> None


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
    Supports optional progress callbacks for monitoring.
    """

    def __init__(
        self,
        max_concurrent: int = 8,
        request_delay: float = 0.0,
        on_task_start: Optional[Callable[[TaskInfo], None]] = None,
        on_task_complete: Optional[TaskCallback] = None,
    ):
        """
        Initialize the task runner.

        Args:
            max_concurrent: Maximum number of tasks to run concurrently.
            request_delay: Delay in seconds between starting each request within a batch.
            on_task_start: Callback when a task starts (receives TaskInfo).
            on_task_complete: Callback when a task completes (receives TaskInfo, success).
        """
        self.max_concurrent = max_concurrent
        self.request_delay = request_delay
        self.on_task_start = on_task_start
        self.on_task_complete = on_task_complete
        self._semaphore: asyncio.Semaphore = None

    async def run_all(
        self,
        tasks: List[Callable[[], Awaitable[T]]],
        task_names: Optional[List[str]] = None,
    ) -> List[Result[T]]:
        """
        Run all tasks with concurrency control and staggered starts.

        Args:
            tasks: List of async callables (no-argument coroutine functions).
            task_names: Optional list of task names for progress tracking.

        Returns:
            List of Result objects (Success or Failure) in order of completion.
        """
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        results: List[Result[T]] = []
        
        # Generate default names if not provided
        names = task_names or [f"Task {i+1}" for i in range(len(tasks))]

        async def run_with_semaphore(idx: int, task: Callable[[], Awaitable[T]], name: str) -> Result[T]:
            task_info = TaskInfo(index=idx, name=name)
            
            async with self._semaphore:
                task_info.start_time = time.time()
                
                # Notify task start
                if self.on_task_start:
                    self.on_task_start(task_info)
                
                try:
                    value = await task()
                    result = Success(value)
                    success = True
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    result = Failure(e)
                    success = False
                
                task_info.end_time = time.time()
                
                # Notify task complete
                if self.on_task_complete:
                    self.on_task_complete(task_info, success)
                
                results.append(result)
                return result

        # Start tasks with optional delay between each
        wrapped_tasks = []
        for i, (task, name) in enumerate(zip(tasks, names)):
            wrapped_tasks.append(run_with_semaphore(i, task, name))
            # Add delay before starting next task (skip delay after last task)
            if self.request_delay > 0 and i < len(tasks) - 1:
                await asyncio.sleep(self.request_delay)

        await asyncio.gather(*wrapped_tasks)

        return results

    async def run_all_ordered(
        self,
        tasks: List[Callable[[], Awaitable[T]]],
        task_names: Optional[List[str]] = None,
    ) -> List[Result[T]]:
        """
        Run all tasks with concurrency control and staggered starts, preserving order.

        Args:
            tasks: List of async callables.
            task_names: Optional list of task names for progress tracking.

        Returns:
            List of Result objects (Success or Failure) in the same order as input tasks.
        """
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Generate default names if not provided
        names = task_names or [f"Task {i+1}" for i in range(len(tasks))]

        async def run_with_semaphore(idx: int, task: Callable[[], Awaitable[T]], name: str) -> Result[T]:
            task_info = TaskInfo(index=idx, name=name)
            
            async with self._semaphore:
                task_info.start_time = time.time()
                
                # Notify task start
                if self.on_task_start:
                    self.on_task_start(task_info)
                
                try:
                    value = await task()
                    result = Success(value)
                    success = True
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    result = Failure(e)
                    success = False
                
                task_info.end_time = time.time()
                
                # Notify task complete
                if self.on_task_complete:
                    self.on_task_complete(task_info, success)
                
                return result

        # Start tasks with optional delay between each
        wrapped_tasks = []
        for i, (task, name) in enumerate(zip(tasks, names)):
            wrapped_tasks.append(run_with_semaphore(i, task, name))
            # Add delay before starting next task (skip delay after last task)
            if self.request_delay > 0 and i < len(tasks) - 1:
                await asyncio.sleep(self.request_delay)

        return await asyncio.gather(*wrapped_tasks)
