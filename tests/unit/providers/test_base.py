"""Tests for providers/base.py."""

import pytest
import logging
from unittest.mock import MagicMock, AsyncMock

from src.providers.base import (
    LLMProvider,
    create_retry_decorator,
    RetryableError,
    RateLimitError,
    TimeoutError,
    EmptyResponseError,
)


class TestExceptions:
    """Tests for custom exception classes."""

    def test_retryable_error(self):
        """Test RetryableError exception."""
        error = RetryableError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_rate_limit_error_is_retryable(self):
        """Test RateLimitError inherits from RetryableError."""
        error = RateLimitError("rate limit hit")
        assert isinstance(error, RetryableError)
        assert isinstance(error, Exception)

    def test_timeout_error_is_retryable(self):
        """Test TimeoutError inherits from RetryableError."""
        error = TimeoutError("request timed out")
        assert isinstance(error, RetryableError)

    def test_empty_response_error_is_retryable(self):
        """Test EmptyResponseError inherits from RetryableError."""
        error = EmptyResponseError("empty response")
        assert isinstance(error, RetryableError)


class TestCreateRetryDecorator:
    """Tests for create_retry_decorator function."""

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self):
        """Test that decorator retries on RetryableError."""
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("retry me")
            return "success"

        result = await failing_then_success()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that decorator stops after max retries."""
        call_count = 0

        @create_retry_decorator(max_retries=2, min_wait=0.01, max_wait=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise RetryableError("always fail")

        with pytest.raises(RetryableError):
            await always_fails()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """Test that non-RetryableErrors are not retried."""
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def non_retryable_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await non_retryable_fail()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_success_without_retry(self):
        """Test successful call without any retries."""
        call_count = 0

        @create_retry_decorator(max_retries=3)
        async def immediate_success():
            nonlocal call_count
            call_count += 1
            return "done"

        result = await immediate_success()
        assert result == "done"
        assert call_count == 1

    def test_custom_logger(self):
        """Test that custom logger is used."""
        custom_logger = logging.getLogger("test_logger")
        decorator = create_retry_decorator(
            max_retries=2,
            retry_logger=custom_logger
        )
        assert decorator is not None


class TestLLMProviderAbstract:
    """Tests for LLMProvider abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()

    def test_default_retry_configuration(self):
        """Test default retry configuration values."""
        assert LLMProvider.DEFAULT_MAX_RETRIES == 5
        assert LLMProvider.DEFAULT_JSON_PARSE_RETRIES == 5
        assert LLMProvider.DEFAULT_RETRY_DELAY == 1.0

    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        class ConcreteProvider(LLMProvider):
            @property
            def name(self):
                return "concrete"

            @property
            def model(self):
                return "test-model"

            async def generate_initial_cards(self, question, json_schema, prompt_template=None):
                return '{"cards": []}'

            async def combine_cards(self, question, combined_inputs, json_schema, combine_prompt_template=None):
                return '{"cards": []}'

            async def format_json(self, raw_content, json_schema):
                return {"cards": []}

        provider = ConcreteProvider()
        assert provider.name == "concrete"
        assert provider.model == "test-model"

    @pytest.mark.asyncio
    async def test_abstract_methods_required(self):
        """Test that abstract methods must be implemented."""
        # Missing generate_initial_cards
        with pytest.raises(TypeError):
            class IncompleteProvider(LLMProvider):
                @property
                def name(self):
                    return "incomplete"

                @property
                def model(self):
                    return "model"

            IncompleteProvider()
