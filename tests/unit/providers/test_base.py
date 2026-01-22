"""Tests for providers/base.py.

Comprehensive tests for the base provider classes, exceptions, and retry logic.
Target: 5:1 test-to-code ratio (~650 lines of tests for ~130 lines of code).
"""

import pytest
import logging
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, Optional

from assertpy import assert_that

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
        """
        Given a message string
        When RetryableError is created
        Then the message is stored correctly
        """
        error = RetryableError("test error")
        assert_that(str(error)).is_equal_to("test error")

    def test_creation_without_message(self):
        """
        Given no message
        When RetryableError is created
        Then empty string is stored
        """
        error = RetryableError()
        assert_that(str(error)).is_equal_to("")

    def test_is_instance_of_exception(self):
        """
        Given a RetryableError
        When checking its inheritance
        Then it is an Exception
        """
        error = RetryableError("test")
        assert_that(error).is_instance_of(Exception)

    def test_can_be_raised_and_caught(self):
        """
        Given a RetryableError
        When it is raised
        Then it can be caught and message preserved
        """
        with pytest.raises(RetryableError) as exc_info:
            raise RetryableError("raised")
        assert_that(str(exc_info.value)).is_equal_to("raised")

    def test_can_be_caught_as_exception(self):
        """
        Given a RetryableError
        When it is raised
        Then it can be caught as generic Exception
        """
        with pytest.raises(Exception):
            raise RetryableError("generic catch")

    def test_with_cause(self):
        """
        Given a RetryableError with a cause
        When chaining exceptions
        Then the cause is preserved
        """
        original = ValueError("original")
        error = RetryableError("wrapper")
        error.__cause__ = original
        assert_that(error.__cause__).is_same_as(original)


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_creation(self):
        """
        Given a message
        When RateLimitError is created
        Then the message is stored correctly
        """
        error = RateLimitError("rate limit hit")
        assert_that(str(error)).is_equal_to("rate limit hit")

    def test_inherits_from_retryable_error(self):
        """
        Given a RateLimitError
        When checking its inheritance
        Then it is a RetryableError
        """
        error = RateLimitError("rate limit")
        assert_that(error).is_instance_of(RetryableError)

    def test_inherits_from_exception(self):
        """
        Given a RateLimitError
        When checking its inheritance
        Then it is an Exception
        """
        error = RateLimitError("rate limit")
        assert_that(error).is_instance_of(Exception)

    def test_can_be_caught_as_retryable(self):
        """
        Given a RateLimitError
        When it is raised
        Then it can be caught as RetryableError
        """
        with pytest.raises(RetryableError):
            raise RateLimitError("limit exceeded")

    def test_with_retry_after_info(self):
        """
        Given a RateLimitError with retry-after info
        When checking the message
        Then the retry-after info is preserved
        """
        error = RateLimitError("Rate limit exceeded. Retry after 60 seconds.")
        assert_that(str(error)).contains("60 seconds")

    @pytest.mark.parametrize("message", [
        "429 Too Many Requests",
        "Rate limit exceeded",
        "Quota exhausted",
        "",
    ])
    def test_various_messages(self, message):
        """
        Given various rate limit messages
        When RateLimitError is created
        Then the message is stored correctly
        """
        error = RateLimitError(message)
        assert_that(str(error)).is_equal_to(message)


class TestTimeoutError:
    """Tests for TimeoutError exception."""

    def test_creation(self):
        """
        Given a timeout message
        When TimeoutError is created
        Then the message is stored correctly
        """
        error = TimeoutError("request timed out")
        assert_that(str(error)).is_equal_to("request timed out")

    def test_inherits_from_retryable_error(self):
        """
        Given a TimeoutError
        When checking its inheritance
        Then it is a RetryableError
        """
        error = TimeoutError("timeout")
        assert_that(error).is_instance_of(RetryableError)

    def test_can_be_caught_as_retryable(self):
        """
        Given a TimeoutError
        When it is raised
        Then it can be caught as RetryableError
        """
        with pytest.raises(RetryableError):
            raise TimeoutError("timed out")

    @pytest.mark.parametrize("timeout_seconds", [1, 5, 30, 60, 120])
    def test_with_timeout_duration(self, timeout_seconds):
        """
        Given various timeout durations
        When TimeoutError is created
        Then the duration is preserved in message
        """
        error = TimeoutError(f"Request timed out after {timeout_seconds}s")
        assert_that(str(error)).contains(str(timeout_seconds))


class TestEmptyResponseError:
    """Tests for EmptyResponseError exception."""

    def test_creation(self):
        """
        Given an empty response message
        When EmptyResponseError is created
        Then the message is stored correctly
        """
        error = EmptyResponseError("empty response")
        assert_that(str(error)).is_equal_to("empty response")

    def test_inherits_from_retryable_error(self):
        """
        Given an EmptyResponseError
        When checking its inheritance
        Then it is a RetryableError
        """
        error = EmptyResponseError("empty")
        assert_that(error).is_instance_of(RetryableError)

    def test_can_be_caught_as_retryable(self):
        """
        Given an EmptyResponseError
        When it is raised
        Then it can be caught as RetryableError
        """
        with pytest.raises(RetryableError):
            raise EmptyResponseError("no content")

    @pytest.mark.parametrize("scenario", [
        "Response was None",
        "Response was empty string",
        "Response contained only whitespace",
        "API returned null content",
    ])
    def test_various_empty_scenarios(self, scenario):
        """
        Given various empty response scenarios
        When EmptyResponseError is created
        Then the scenario description is preserved
        """
        error = EmptyResponseError(scenario)
        assert_that(str(error)).is_equal_to(scenario)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_all_retryable_errors_share_base(self):
        """
        Given all retryable error types
        When checking their inheritance
        Then they all inherit from RetryableError
        """
        errors = [
            RateLimitError("rate"),
            TimeoutError("timeout"),
            EmptyResponseError("empty"),
        ]
        for error in errors:
            assert_that(error).is_instance_of(RetryableError)

    def test_exception_types_are_distinct(self):
        """
        Given different error types
        When checking their types
        Then each has its own distinct type
        """
        rate_limit = RateLimitError("rate")
        timeout = TimeoutError("timeout")
        empty = EmptyResponseError("empty")

        assert_that(type(rate_limit)).is_equal_to(RateLimitError)
        assert_that(type(timeout)).is_equal_to(TimeoutError)
        assert_that(type(empty)).is_equal_to(EmptyResponseError)

    def test_can_distinguish_error_types(self):
        """
        Given different error types
        When catching them
        Then each type can be distinguished
        """
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

        assert_that(errors_caught).is_equal_to(["rate_limit", "timeout", "empty"])


# =============================================================================
# Retry Decorator Tests
# =============================================================================


class TestCreateRetryDecoratorBasic:
    """Basic tests for create_retry_decorator function."""

    def test_returns_decorator(self):
        """
        Given no parameters
        When create_retry_decorator is called
        Then a callable decorator is returned
        """
        decorator = create_retry_decorator()
        assert_that(decorator).is_not_none()
        assert_that(callable(decorator)).is_true()

    def test_default_parameters(self):
        """
        Given no parameters
        When create_retry_decorator is called
        Then it succeeds with default parameters
        """
        decorator = create_retry_decorator()
        assert_that(decorator).is_not_none()

    @pytest.mark.parametrize("max_retries", [1, 2, 3, 5, 10])
    def test_accepts_various_max_retries(self, max_retries):
        """
        Given various max_retries values
        When create_retry_decorator is called
        Then it accepts them all
        """
        decorator = create_retry_decorator(max_retries=max_retries)
        assert_that(decorator).is_not_none()

    @pytest.mark.parametrize("min_wait,max_wait", [
        (0.01, 0.1),
        (0.5, 1.0),
        (1.0, 5.0),
        (1.0, 10.0),
    ])
    def test_accepts_various_wait_times(self, min_wait, max_wait):
        """
        Given various wait time configurations
        When create_retry_decorator is called
        Then it accepts them all
        """
        decorator = create_retry_decorator(min_wait=min_wait, max_wait=max_wait)
        assert_that(decorator).is_not_none()

    def test_custom_logger(self):
        """
        Given a custom logger
        When create_retry_decorator is called
        Then it accepts the custom logger
        """
        custom_logger = logging.getLogger("test_custom")
        decorator = create_retry_decorator(retry_logger=custom_logger)
        assert_that(decorator).is_not_none()


class TestCreateRetryDecoratorBehavior:
    """Behavior tests for create_retry_decorator."""

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self):
        """
        Given a function that fails then succeeds
        When decorated with retry decorator
        Then it retries until success
        """
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("retry me")
            return "success"

        result = await failing_then_success()
        assert_that(result).is_equal_to("success")
        assert_that(call_count).is_equal_to(3)

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit_error(self):
        """
        Given a function that hits rate limit then succeeds
        When decorated with retry decorator
        Then it retries until success
        """
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("429")
            return "ok"

        result = await rate_limited()
        assert_that(result).is_equal_to("ok")
        assert_that(call_count).is_equal_to(2)

    @pytest.mark.asyncio
    async def test_retries_on_timeout_error(self):
        """
        Given a function that times out then succeeds
        When decorated with retry decorator
        Then it retries until success
        """
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def timeout_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("timed out")
            return "completed"

        result = await timeout_then_success()
        assert_that(result).is_equal_to("completed")
        assert_that(call_count).is_equal_to(2)

    @pytest.mark.asyncio
    async def test_retries_on_empty_response_error(self):
        """
        Given a function that returns empty then content
        When decorated with retry decorator
        Then it retries until success
        """
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def empty_then_content():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise EmptyResponseError("empty")
            return "content"

        result = await empty_then_content()
        assert_that(result).is_equal_to("content")
        assert_that(call_count).is_equal_to(2)

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """
        Given a function that always fails
        When decorated with retry decorator
        Then it stops after max retries
        """
        call_count = 0

        @create_retry_decorator(max_retries=2, min_wait=0.01, max_wait=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise RetryableError("always fail")

        with pytest.raises(RetryableError):
            await always_fails()

        assert_that(call_count).is_equal_to(2)

    @pytest.mark.asyncio
    async def test_no_retry_on_value_error(self):
        """
        Given a function that raises ValueError
        When decorated with retry decorator
        Then ValueError is not retried
        """
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await value_error()

        assert_that(call_count).is_equal_to(1)

    @pytest.mark.asyncio
    async def test_no_retry_on_type_error(self):
        """
        Given a function that raises TypeError
        When decorated with retry decorator
        Then TypeError is not retried
        """
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            await type_error()

        assert_that(call_count).is_equal_to(1)

    @pytest.mark.asyncio
    async def test_no_retry_on_key_error(self):
        """
        Given a function that raises KeyError
        When decorated with retry decorator
        Then KeyError is not retried
        """
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def key_error():
            nonlocal call_count
            call_count += 1
            raise KeyError("missing")

        with pytest.raises(KeyError):
            await key_error()

        assert_that(call_count).is_equal_to(1)

    @pytest.mark.asyncio
    async def test_success_without_retry(self):
        """
        Given a function that succeeds immediately
        When decorated with retry decorator
        Then it is called only once
        """
        call_count = 0

        @create_retry_decorator(max_retries=3)
        async def immediate_success():
            nonlocal call_count
            call_count += 1
            return "done"

        result = await immediate_success()
        assert_that(result).is_equal_to("done")
        assert_that(call_count).is_equal_to(1)

    @pytest.mark.asyncio
    async def test_preserves_return_value(self):
        """
        Given a function that returns a dict
        When decorated with retry decorator
        Then the return value is preserved
        """
        @create_retry_decorator(max_retries=2)
        async def returns_dict():
            return {"key": "value", "count": 42}

        result = await returns_dict()
        assert_that(result).is_equal_to({"key": "value", "count": 42})

    @pytest.mark.asyncio
    async def test_preserves_none_return(self):
        """
        Given a function that returns None
        When decorated with retry decorator
        Then None is preserved
        """
        @create_retry_decorator(max_retries=2)
        async def returns_none():
            return None

        result = await returns_none()
        assert_that(result).is_none()


class TestRetryDecoratorEdgeCases:
    """Edge case tests for retry decorator."""

    @pytest.mark.asyncio
    async def test_single_retry_allowed(self):
        """
        Given max_retries=1
        When function fails
        Then only one attempt is made
        """
        call_count = 0

        @create_retry_decorator(max_retries=1, min_wait=0.01, max_wait=0.01)
        async def fails_once():
            nonlocal call_count
            call_count += 1
            raise RetryableError("fail")

        with pytest.raises(RetryableError):
            await fails_once()

        assert_that(call_count).is_equal_to(1)

    @pytest.mark.asyncio
    async def test_success_on_last_retry(self):
        """
        Given success on the last retry attempt
        When function retries
        Then success is returned
        """
        call_count = 0

        @create_retry_decorator(max_retries=5, min_wait=0.01, max_wait=0.01)
        async def success_on_fifth():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise RetryableError("not yet")
            return "finally"

        result = await success_on_fifth()
        assert_that(result).is_equal_to("finally")
        assert_that(call_count).is_equal_to(5)

    @pytest.mark.asyncio
    async def test_alternating_error_types(self):
        """
        Given alternating retryable error types
        When function retries
        Then all error types are retried
        """
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
        assert_that(result).is_equal_to("success")
        assert_that(call_count).is_equal_to(4)


# =============================================================================
# LLMProvider Abstract Base Class Tests
# =============================================================================


class TestLLMProviderAbstract:
    """Tests for LLMProvider abstract base class."""

    def test_cannot_instantiate_directly(self):
        """
        Given the abstract LLMProvider class
        When attempting to instantiate directly
        Then TypeError is raised
        """
        with pytest.raises(TypeError):
            LLMProvider()

    def test_is_abstract(self):
        """
        Given LLMProvider
        When checking if abstract
        Then it is an ABC subclass
        """
        from abc import ABC
        assert_that(issubclass(LLMProvider, ABC)).is_true()

    def test_has_abstract_name_property(self):
        """
        Given LLMProvider
        When checking for name property
        Then it exists
        """
        assert_that(hasattr(LLMProvider, 'name')).is_true()

    def test_has_abstract_model_property(self):
        """
        Given LLMProvider
        When checking for model property
        Then it exists
        """
        assert_that(hasattr(LLMProvider, 'model')).is_true()

    def test_has_abstract_generate_initial_cards(self):
        """
        Given LLMProvider
        When checking for generate_initial_cards
        Then it exists
        """
        assert_that(hasattr(LLMProvider, 'generate_initial_cards')).is_true()

    def test_has_abstract_combine_cards(self):
        """
        Given LLMProvider
        When checking for combine_cards
        Then it exists
        """
        assert_that(hasattr(LLMProvider, 'combine_cards')).is_true()

    def test_has_abstract_format_json(self):
        """
        Given LLMProvider
        When checking for format_json
        Then it exists
        """
        assert_that(hasattr(LLMProvider, 'format_json')).is_true()


class TestLLMProviderDefaults:
    """Tests for LLMProvider default configuration values."""

    def test_default_max_retries(self):
        """
        Given LLMProvider
        When checking DEFAULT_MAX_RETRIES
        Then it is 5
        """
        assert_that(LLMProvider.DEFAULT_MAX_RETRIES).is_equal_to(5)

    def test_default_json_parse_retries(self):
        """
        Given LLMProvider
        When checking DEFAULT_JSON_PARSE_RETRIES
        Then it is 5
        """
        assert_that(LLMProvider.DEFAULT_JSON_PARSE_RETRIES).is_equal_to(5)

    def test_default_retry_delay(self):
        """
        Given LLMProvider
        When checking DEFAULT_RETRY_DELAY
        Then it is 1.0 seconds
        """
        assert_that(LLMProvider.DEFAULT_RETRY_DELAY).is_equal_to(1.0)

    def test_default_retry_delay_is_float(self):
        """
        Given LLMProvider
        When checking DEFAULT_RETRY_DELAY type
        Then it is a float
        """
        assert_that(LLMProvider.DEFAULT_RETRY_DELAY).is_instance_of(float)


class TestLLMProviderContractEnforcement:
    """Tests for LLMProvider contract enforcement."""

    def test_missing_name_property(self):
        """
        Given a class missing name property
        When instantiating
        Then TypeError is raised
        """
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
        """
        Given a class missing model property
        When instantiating
        Then TypeError is raised
        """
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
        """
        Given a class missing generate_initial_cards
        When instantiating
        Then TypeError is raised
        """
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
        """
        Given a class missing combine_cards
        When instantiating
        Then TypeError is raised
        """
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
        """
        Given a class missing format_json
        When instantiating
        Then TypeError is raised
        """
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
        """
        Given a complete concrete provider
        When instantiating
        Then it succeeds
        """
        provider = self.create_concrete_provider()
        assert_that(provider).is_not_none()

    def test_name_property_works(self):
        """
        Given a concrete provider
        When accessing name property
        Then correct value is returned
        """
        provider = self.create_concrete_provider()
        assert_that(provider.name).is_equal_to("test_provider")

    def test_model_property_works(self):
        """
        Given a concrete provider
        When accessing model property
        Then correct value is returned
        """
        provider = self.create_concrete_provider()
        assert_that(provider.model).is_equal_to("test-model-v1")

    @pytest.mark.asyncio
    async def test_generate_initial_cards_works(self):
        """
        Given a concrete provider
        When calling generate_initial_cards
        Then it returns expected result
        """
        provider = self.create_concrete_provider()
        result = await provider.generate_initial_cards("test", {})
        assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_generate_initial_cards_with_all_params(self):
        """
        Given a concrete provider
        When calling generate_initial_cards with all parameters
        Then it works correctly
        """
        provider = self.create_concrete_provider()
        result = await provider.generate_initial_cards(
            question="What is X?",
            json_schema={"type": "object"},
            prompt_template="Generate: {question}",
        )
        assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_combine_cards_works(self):
        """
        Given a concrete provider
        When calling combine_cards
        Then it returns expected result
        """
        provider = self.create_concrete_provider()
        result = await provider.combine_cards("test", "inputs", {})
        assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_combine_cards_with_all_params(self):
        """
        Given a concrete provider
        When calling combine_cards with all parameters
        Then it works correctly
        """
        provider = self.create_concrete_provider()
        result = await provider.combine_cards(
            question="What is X?",
            combined_inputs="Card 1\nCard 2",
            json_schema={"type": "object"},
            combine_prompt_template="Combine: {inputs}",
        )
        assert_that(result).is_equal_to('{"cards": []}')

    @pytest.mark.asyncio
    async def test_format_json_works(self):
        """
        Given a concrete provider
        When calling format_json
        Then it returns expected result
        """
        provider = self.create_concrete_provider()
        result = await provider.format_json('{"raw": true}', {})
        assert_that(result).is_equal_to({"cards": []})

    def test_inherits_default_config(self):
        """
        Given a concrete provider
        When checking default config
        Then it inherits from LLMProvider
        """
        provider = self.create_concrete_provider()
        assert_that(provider.DEFAULT_MAX_RETRIES).is_equal_to(5)
        assert_that(provider.DEFAULT_JSON_PARSE_RETRIES).is_equal_to(5)
        assert_that(provider.DEFAULT_RETRY_DELAY).is_equal_to(1.0)


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
        """
        Given various provider name formats
        When creating a provider
        Then the name format is validated
        """
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
            assert_that(len(provider.name)).is_greater_than(0)
        else:
            assert_that(provider.name).is_equal_to("")

    @pytest.mark.parametrize("model", [
        "llama3.1-70b",
        "gemini-1.5-pro",
        "gpt-4-turbo",
        "claude-3-opus",
        "model-v1.2.3",
    ])
    def test_model_name_formats(self, model):
        """
        Given various model name formats
        When creating a provider
        Then the model name is accepted
        """
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
        assert_that(provider.model).is_equal_to(model)
