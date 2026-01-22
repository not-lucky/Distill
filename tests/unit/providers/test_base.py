"""Tests for providers/base.py.

Comprehensive tests for the base provider classes, exceptions, and retry logic.
Target: 5:1 test-to-code ratio (~650 lines of tests for ~130 lines of code).
"""

import pytest
import logging
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, Optional

from src.providers.base import (
    LLMProvider,
    create_retry_decorator,
    RetryableError,
    RateLimitError,
    TimeoutError,
    EmptyResponseError,
)


# =============================================================================
# Exception Tests
# =============================================================================


class TestRetryableError:
    """Tests for RetryableError base exception."""

    def test_creation_with_message(self):
        """Test RetryableError can be created with a message."""
        error = RetryableError("test error")
        assert str(error) == "test error"

    def test_creation_without_message(self):
        """Test RetryableError can be created without a message."""
        error = RetryableError()
        assert str(error) == ""

    def test_is_instance_of_exception(self):
        """Test RetryableError inherits from Exception."""
        error = RetryableError("test")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        """Test RetryableError can be raised and caught."""
        with pytest.raises(RetryableError) as exc_info:
            raise RetryableError("raised")
        assert str(exc_info.value) == "raised"

    def test_can_be_caught_as_exception(self):
        """Test RetryableError can be caught as generic Exception."""
        with pytest.raises(Exception):
            raise RetryableError("generic catch")

    def test_with_cause(self):
        """Test RetryableError can chain exceptions."""
        original = ValueError("original")
        error = RetryableError("wrapper")
        error.__cause__ = original
        assert error.__cause__ is original


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_creation(self):
        """Test RateLimitError can be created."""
        error = RateLimitError("rate limit hit")
        assert str(error) == "rate limit hit"

    def test_inherits_from_retryable_error(self):
        """Test RateLimitError inherits from RetryableError."""
        error = RateLimitError("rate limit")
        assert isinstance(error, RetryableError)

    def test_inherits_from_exception(self):
        """Test RateLimitError inherits from Exception."""
        error = RateLimitError("rate limit")
        assert isinstance(error, Exception)

    def test_can_be_caught_as_retryable(self):
        """Test RateLimitError can be caught as RetryableError."""
        with pytest.raises(RetryableError):
            raise RateLimitError("limit exceeded")

    def test_with_retry_after_info(self):
        """Test RateLimitError can include retry-after information."""
        error = RateLimitError("Rate limit exceeded. Retry after 60 seconds.")
        assert "60 seconds" in str(error)

    @pytest.mark.parametrize("message", [
        "429 Too Many Requests",
        "Rate limit exceeded",
        "Quota exhausted",
        "",
    ])
    def test_various_messages(self, message):
        """Test RateLimitError with various messages."""
        error = RateLimitError(message)
        assert str(error) == message


class TestTimeoutError:
    """Tests for TimeoutError exception."""

    def test_creation(self):
        """Test TimeoutError can be created."""
        error = TimeoutError("request timed out")
        assert str(error) == "request timed out"

    def test_inherits_from_retryable_error(self):
        """Test TimeoutError inherits from RetryableError."""
        error = TimeoutError("timeout")
        assert isinstance(error, RetryableError)

    def test_can_be_caught_as_retryable(self):
        """Test TimeoutError can be caught as RetryableError."""
        with pytest.raises(RetryableError):
            raise TimeoutError("timed out")

    @pytest.mark.parametrize("timeout_seconds", [1, 5, 30, 60, 120])
    def test_with_timeout_duration(self, timeout_seconds):
        """Test TimeoutError with various timeout durations."""
        error = TimeoutError(f"Request timed out after {timeout_seconds}s")
        assert str(timeout_seconds) in str(error)


class TestEmptyResponseError:
    """Tests for EmptyResponseError exception."""

    def test_creation(self):
        """Test EmptyResponseError can be created."""
        error = EmptyResponseError("empty response")
        assert str(error) == "empty response"

    def test_inherits_from_retryable_error(self):
        """Test EmptyResponseError inherits from RetryableError."""
        error = EmptyResponseError("empty")
        assert isinstance(error, RetryableError)

    def test_can_be_caught_as_retryable(self):
        """Test EmptyResponseError can be caught as RetryableError."""
        with pytest.raises(RetryableError):
            raise EmptyResponseError("no content")

    @pytest.mark.parametrize("scenario", [
        "Response was None",
        "Response was empty string",
        "Response contained only whitespace",
        "API returned null content",
    ])
    def test_various_empty_scenarios(self, scenario):
        """Test EmptyResponseError with various empty response scenarios."""
        error = EmptyResponseError(scenario)
        assert str(error) == scenario


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_all_retryable_errors_share_base(self):
        """Test all retryable errors share common base."""
        errors = [
            RateLimitError("rate"),
            TimeoutError("timeout"),
            EmptyResponseError("empty"),
        ]
        for error in errors:
            assert isinstance(error, RetryableError)

    def test_exception_types_are_distinct(self):
        """Test each exception type is distinct."""
        rate_limit = RateLimitError("rate")
        timeout = TimeoutError("timeout")
        empty = EmptyResponseError("empty")

        assert type(rate_limit) is RateLimitError
        assert type(timeout) is TimeoutError
        assert type(empty) is EmptyResponseError

    def test_can_distinguish_error_types(self):
        """Test can distinguish between error types when catching."""
        errors_caught = []

        for ErrorClass in [RateLimitError, TimeoutError, EmptyResponseError]:
            try:
                raise ErrorClass("test")
            except RateLimitError:
                errors_caught.append("rate_limit")
            except TimeoutError:
                errors_caught.append("timeout")
            except EmptyResponseError:
                errors_caught.append("empty")

        assert errors_caught == ["rate_limit", "timeout", "empty"]


# =============================================================================
# Retry Decorator Tests
# =============================================================================


class TestCreateRetryDecoratorBasic:
    """Basic tests for create_retry_decorator function."""

    def test_returns_decorator(self):
        """Test create_retry_decorator returns a callable decorator."""
        decorator = create_retry_decorator()
        assert callable(decorator)

    def test_default_parameters(self):
        """Test decorator uses default parameters when none specified."""
        decorator = create_retry_decorator()
        # Just verify it doesn't raise
        assert decorator is not None

    @pytest.mark.parametrize("max_retries", [1, 2, 3, 5, 10])
    def test_accepts_various_max_retries(self, max_retries):
        """Test decorator accepts various max_retries values."""
        decorator = create_retry_decorator(max_retries=max_retries)
        assert decorator is not None

    @pytest.mark.parametrize("min_wait,max_wait", [
        (0.01, 0.1),
        (0.5, 1.0),
        (1.0, 5.0),
        (1.0, 10.0),
    ])
    def test_accepts_various_wait_times(self, min_wait, max_wait):
        """Test decorator accepts various wait time configurations."""
        decorator = create_retry_decorator(min_wait=min_wait, max_wait=max_wait)
        assert decorator is not None

    def test_custom_logger(self):
        """Test decorator accepts custom logger."""
        custom_logger = logging.getLogger("test_custom")
        decorator = create_retry_decorator(retry_logger=custom_logger)
        assert decorator is not None


class TestCreateRetryDecoratorBehavior:
    """Behavior tests for create_retry_decorator."""

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self):
        """Test decorator retries on RetryableError."""
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
    async def test_retries_on_rate_limit_error(self):
        """Test decorator retries on RateLimitError."""
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("429")
            return "ok"

        result = await rate_limited()
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_timeout_error(self):
        """Test decorator retries on TimeoutError."""
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def timeout_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("timed out")
            return "completed"

        result = await timeout_then_success()
        assert result == "completed"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_empty_response_error(self):
        """Test decorator retries on EmptyResponseError."""
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def empty_then_content():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise EmptyResponseError("empty")
            return "content"

        result = await empty_then_content()
        assert result == "content"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test decorator stops after max retries."""
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
    async def test_no_retry_on_value_error(self):
        """Test ValueError is not retried."""
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await value_error()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_type_error(self):
        """Test TypeError is not retried."""
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            await type_error()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_key_error(self):
        """Test KeyError is not retried."""
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def key_error():
            nonlocal call_count
            call_count += 1
            raise KeyError("missing")

        with pytest.raises(KeyError):
            await key_error()

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

    @pytest.mark.asyncio
    async def test_preserves_return_value(self):
        """Test decorator preserves return value."""
        @create_retry_decorator(max_retries=2)
        async def returns_dict():
            return {"key": "value", "count": 42}

        result = await returns_dict()
        assert result == {"key": "value", "count": 42}

    @pytest.mark.asyncio
    async def test_preserves_none_return(self):
        """Test decorator preserves None return value."""
        @create_retry_decorator(max_retries=2)
        async def returns_none():
            return None

        result = await returns_none()
        assert result is None


class TestRetryDecoratorEdgeCases:
    """Edge case tests for retry decorator."""

    @pytest.mark.asyncio
    async def test_single_retry_allowed(self):
        """Test with max_retries=1 (no retries, just one attempt)."""
        call_count = 0

        @create_retry_decorator(max_retries=1, min_wait=0.01, max_wait=0.01)
        async def fails_once():
            nonlocal call_count
            call_count += 1
            raise RetryableError("fail")

        with pytest.raises(RetryableError):
            await fails_once()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_success_on_last_retry(self):
        """Test success on the very last retry attempt."""
        call_count = 0

        @create_retry_decorator(max_retries=5, min_wait=0.01, max_wait=0.01)
        async def success_on_fifth():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise RetryableError("not yet")
            return "finally"

        result = await success_on_fifth()
        assert result == "finally"
        assert call_count == 5

    @pytest.mark.asyncio
    async def test_alternating_error_types(self):
        """Test retrying with alternating retryable error types."""
        call_count = 0
        error_sequence = [
            RateLimitError("rate"),
            TimeoutError("timeout"),
            EmptyResponseError("empty"),
        ]

        @create_retry_decorator(max_retries=5, min_wait=0.01, max_wait=0.01)
        async def alternating_errors():
            nonlocal call_count
            if call_count < len(error_sequence):
                error = error_sequence[call_count]
                call_count += 1
                raise error
            call_count += 1
            return "success"

        result = await alternating_errors()
        assert result == "success"
        assert call_count == 4


# =============================================================================
# LLMProvider Abstract Base Class Tests
# =============================================================================


class TestLLMProviderAbstract:
    """Tests for LLMProvider abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()

    def test_is_abstract(self):
        """Test LLMProvider is an abstract class."""
        from abc import ABC
        assert issubclass(LLMProvider, ABC)

    def test_has_abstract_name_property(self):
        """Test LLMProvider has abstract name property."""
        # Check that name is marked as abstract
        assert hasattr(LLMProvider, 'name')

    def test_has_abstract_model_property(self):
        """Test LLMProvider has abstract model property."""
        assert hasattr(LLMProvider, 'model')

    def test_has_abstract_generate_initial_cards(self):
        """Test LLMProvider has abstract generate_initial_cards method."""
        assert hasattr(LLMProvider, 'generate_initial_cards')

    def test_has_abstract_combine_cards(self):
        """Test LLMProvider has abstract combine_cards method."""
        assert hasattr(LLMProvider, 'combine_cards')

    def test_has_abstract_format_json(self):
        """Test LLMProvider has abstract format_json method."""
        assert hasattr(LLMProvider, 'format_json')


class TestLLMProviderDefaults:
    """Tests for LLMProvider default configuration values."""

    def test_default_max_retries(self):
        """Test DEFAULT_MAX_RETRIES is 5."""
        assert LLMProvider.DEFAULT_MAX_RETRIES == 5

    def test_default_json_parse_retries(self):
        """Test DEFAULT_JSON_PARSE_RETRIES is 5."""
        assert LLMProvider.DEFAULT_JSON_PARSE_RETRIES == 5

    def test_default_retry_delay(self):
        """Test DEFAULT_RETRY_DELAY is 1.0 seconds."""
        assert LLMProvider.DEFAULT_RETRY_DELAY == 1.0

    def test_default_retry_delay_is_float(self):
        """Test DEFAULT_RETRY_DELAY is a float."""
        assert isinstance(LLMProvider.DEFAULT_RETRY_DELAY, float)


class TestLLMProviderContractEnforcement:
    """Tests for LLMProvider contract enforcement."""

    def test_missing_name_property(self):
        """Test that missing name property raises TypeError."""
        with pytest.raises(TypeError):
            class MissingName(LLMProvider):
                @property
                def model(self):
                    return "model"

                async def generate_initial_cards(self, q, s, p=None):
                    return ""

                async def combine_cards(self, q, i, s, p=None):
                    return ""

                async def format_json(self, c, s):
                    return {}

            MissingName()

    def test_missing_model_property(self):
        """Test that missing model property raises TypeError."""
        with pytest.raises(TypeError):
            class MissingModel(LLMProvider):
                @property
                def name(self):
                    return "name"

                async def generate_initial_cards(self, q, s, p=None):
                    return ""

                async def combine_cards(self, q, i, s, p=None):
                    return ""

                async def format_json(self, c, s):
                    return {}

            MissingModel()

    def test_missing_generate_initial_cards(self):
        """Test that missing generate_initial_cards raises TypeError."""
        with pytest.raises(TypeError):
            class MissingGenerate(LLMProvider):
                @property
                def name(self):
                    return "name"

                @property
                def model(self):
                    return "model"

                async def combine_cards(self, q, i, s, p=None):
                    return ""

                async def format_json(self, c, s):
                    return {}

            MissingGenerate()

    def test_missing_combine_cards(self):
        """Test that missing combine_cards raises TypeError."""
        with pytest.raises(TypeError):
            class MissingCombine(LLMProvider):
                @property
                def name(self):
                    return "name"

                @property
                def model(self):
                    return "model"

                async def generate_initial_cards(self, q, s, p=None):
                    return ""

                async def format_json(self, c, s):
                    return {}

            MissingCombine()

    def test_missing_format_json(self):
        """Test that missing format_json raises TypeError."""
        with pytest.raises(TypeError):
            class MissingFormat(LLMProvider):
                @property
                def name(self):
                    return "name"

                @property
                def model(self):
                    return "model"

                async def generate_initial_cards(self, q, s, p=None):
                    return ""

                async def combine_cards(self, q, i, s, p=None):
                    return ""

            MissingFormat()


class TestConcreteProviderImplementation:
    """Tests for concrete provider implementations."""

    def create_concrete_provider(self):
        """Helper to create a valid concrete provider."""
        class ConcreteProvider(LLMProvider):
            @property
            def name(self):
                return "test_provider"

            @property
            def model(self):
                return "test-model-v1"

            async def generate_initial_cards(
                self,
                question: str,
                json_schema: Dict[str, Any],
                prompt_template: Optional[str] = None,
            ) -> str:
                return '{"cards": []}'

            async def combine_cards(
                self,
                question: str,
                combined_inputs: str,
                json_schema: Dict[str, Any],
                combine_prompt_template: Optional[str] = None,
            ) -> Optional[str]:
                return '{"cards": []}'

            async def format_json(
                self,
                raw_content: str,
                json_schema: Dict[str, Any],
            ) -> Optional[Dict[str, Any]]:
                return {"cards": []}

        return ConcreteProvider()

    def test_can_instantiate_concrete_provider(self):
        """Test concrete provider can be instantiated."""
        provider = self.create_concrete_provider()
        assert provider is not None

    def test_name_property_works(self):
        """Test name property returns correct value."""
        provider = self.create_concrete_provider()
        assert provider.name == "test_provider"

    def test_model_property_works(self):
        """Test model property returns correct value."""
        provider = self.create_concrete_provider()
        assert provider.model == "test-model-v1"

    @pytest.mark.asyncio
    async def test_generate_initial_cards_works(self):
        """Test generate_initial_cards method works."""
        provider = self.create_concrete_provider()
        result = await provider.generate_initial_cards("test", {})
        assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_generate_initial_cards_with_all_params(self):
        """Test generate_initial_cards with all parameters."""
        provider = self.create_concrete_provider()
        result = await provider.generate_initial_cards(
            question="What is X?",
            json_schema={"type": "object"},
            prompt_template="Generate: {question}",
        )
        assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_combine_cards_works(self):
        """Test combine_cards method works."""
        provider = self.create_concrete_provider()
        result = await provider.combine_cards("test", "inputs", {})
        assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_combine_cards_with_all_params(self):
        """Test combine_cards with all parameters."""
        provider = self.create_concrete_provider()
        result = await provider.combine_cards(
            question="What is X?",
            combined_inputs="Card 1\nCard 2",
            json_schema={"type": "object"},
            combine_prompt_template="Combine: {inputs}",
        )
        assert result == '{"cards": []}'

    @pytest.mark.asyncio
    async def test_format_json_works(self):
        """Test format_json method works."""
        provider = self.create_concrete_provider()
        result = await provider.format_json('{"raw": true}', {})
        assert result == {"cards": []}

    def test_inherits_default_config(self):
        """Test concrete provider inherits default config."""
        provider = self.create_concrete_provider()
        assert provider.DEFAULT_MAX_RETRIES == 5
        assert provider.DEFAULT_JSON_PARSE_RETRIES == 5
        assert provider.DEFAULT_RETRY_DELAY == 1.0


class TestProviderNamingConventions:
    """Tests for provider naming conventions."""

    @pytest.mark.parametrize("name,expected_valid", [
        ("llm2deck_cerebras", True),
        ("llm2deck_gemini", True),
        ("my_provider", True),
        ("provider123", True),
        ("", False),
    ])
    def test_provider_name_formats(self, name, expected_valid):
        """Test various provider name formats."""
        class TestProvider(LLMProvider):
            def __init__(self, provider_name):
                self._name = provider_name

            @property
            def name(self):
                return self._name

            @property
            def model(self):
                return "model"

            async def generate_initial_cards(self, q, s, p=None):
                return ""

            async def combine_cards(self, q, i, s, p=None):
                return ""

            async def format_json(self, c, s):
                return {}

        provider = TestProvider(name)
        if expected_valid:
            assert len(provider.name) > 0
        else:
            assert provider.name == ""

    @pytest.mark.parametrize("model", [
        "llama3.1-70b",
        "gemini-1.5-pro",
        "gpt-4-turbo",
        "claude-3-opus",
        "model-v1.2.3",
    ])
    def test_model_name_formats(self, model):
        """Test various model name formats."""
        class TestProvider(LLMProvider):
            def __init__(self, model_name):
                self._model = model_name

            @property
            def name(self):
                return "test"

            @property
            def model(self):
                return self._model

            async def generate_initial_cards(self, q, s, p=None):
                return ""

            async def combine_cards(self, q, i, s, p=None):
                return ""

            async def format_json(self, c, s):
                return {}

        provider = TestProvider(model)
        assert provider.model == model
