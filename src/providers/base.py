"""Base class and utilities for LLM providers."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

logger = logging.getLogger(__name__)


# Common retryable exceptions
class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass


class RateLimitError(RetryableError):
    """Raised when rate limit is hit."""
    pass


class TimeoutError(RetryableError):
    """Raised when request times out."""
    pass


class EmptyResponseError(RetryableError):
    """Raised when API returns empty/None content."""
    pass


def create_retry_decorator(
    max_retries: int = 5,
    min_wait: float = 1,
    max_wait: float = 10,
    retry_logger: Optional[logging.Logger] = None,
):
    """
    Create a tenacity retry decorator with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        min_wait: Minimum wait time between retries in seconds.
        max_wait: Maximum wait time between retries in seconds.
        retry_logger: Logger for retry events.

    Returns:
        A tenacity retry decorator.
    """
    return retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(RetryableError),
        before_sleep=before_sleep_log(retry_logger or logger, logging.WARNING),
        reraise=True,
    )


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Provides default retry configuration that subclasses should use
    for consistent behavior across all providers.
    """

    # Default retry configuration
    DEFAULT_MAX_RETRIES = 5
    DEFAULT_JSON_PARSE_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0  # seconds

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'llm2deck_cerebras', 'llm2deck_gemini')"""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier (e.g., 'llama3.1-70b', 'gemini-1.5-pro')"""
        pass

    @abstractmethod
    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        """Generates initial cards for a given question."""
        pass

    @abstractmethod
    async def combine_cards(
        self,
        question: str,
        combined_inputs: str,
        json_schema: Dict[str, Any],
        combine_prompt_template: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Combines multiple sets of cards into a single deck."""
        pass
