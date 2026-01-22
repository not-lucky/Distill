"""Property-based tests with Hypothesis.

Task fn-2.8: Property-based tests for:
- Card generation properties
- JSON parsing properties
- Provider response handling properties
"""

import json
import pytest

from assertpy import assert_that
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.strategies import composite
from unittest.mock import AsyncMock, MagicMock, patch
import itertools
from typing import Dict, Any, Optional, List

from src.utils import strip_json_block, sanitize_filename
from src.providers.base import (
    LLMProvider,
    create_retry_decorator,
    RetryableError,
    RateLimitError,
    TimeoutError,
    EmptyResponseError,
)
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.config.subjects import SubjectConfig
from src.models import LeetCodeProblem
from src.task_runner import ConcurrentTaskRunner, Success, Failure


# =============================================================================
# Custom Strategies
# =============================================================================


# Strategy for valid JSON-like strings
@composite
def json_objects(draw):
    """Generate valid JSON objects."""
    keys = draw(st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"),
                                   whitelist_characters="_"),
            min_size=1,
            max_size=20,
        ),
        min_size=0,
        max_size=5,
        unique=True,
    ))
    values = draw(st.lists(
        st.one_of(
            st.text(max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.none(),
        ),
        min_size=len(keys),
        max_size=len(keys),
    ))
    return dict(zip(keys, values))


# Strategy for card-like dictionaries
@composite
def card_dicts(draw):
    """Generate card-like dictionaries."""
    return {
        "front": draw(st.text(min_size=1, max_size=200)),
        "back": draw(st.text(min_size=1, max_size=500)),
    }


# Strategy for question strings
question_strategy = st.text(min_size=1, max_size=100)


# Strategy for category names
category_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
                           whitelist_characters="-_"),
    min_size=1,
    max_size=50,
)


# Strategy for model names
model_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"),
                           whitelist_characters="-_."),
    min_size=1,
    max_size=50,
)


# Strategy for base URLs
base_url_strategy = st.sampled_from([
    "https://api.openai.com/v1",
    "https://api.cerebras.ai/v1",
    "http://localhost:8080/v1",
    "https://api.example.com/v1",
])


# Strategy for timeout values
timeout_strategy = st.floats(min_value=1.0, max_value=600.0)


# Strategy for temperature values
temperature_strategy = st.floats(min_value=0.0, max_value=2.0)


# =============================================================================
# Test Provider Subclass
# =============================================================================


class ConcreteOpenAIProvider(OpenAICompatibleProvider):
    """Concrete implementation for testing."""

    @property
    def name(self) -> str:
        return "test_provider"


# =============================================================================
# Property Tests: JSON Parsing
# =============================================================================


class TestJSONParsingProperties:
    """Property-based tests for JSON parsing."""

    @given(st.dictionaries(
        keys=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),
                whitelist_characters="_"
            ),
            min_size=1,
            max_size=20,
        ),
        values=st.one_of(
            st.text(max_size=100),
            st.integers(min_value=-1000000, max_value=1000000),
            st.booleans(),
        ),
        min_size=0,
        max_size=10,
    ))
    @settings(max_examples=50)
    def test_valid_json_roundtrip(self, data):
        """Property: valid JSON data should roundtrip through serialization."""
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        assert_that(parsed).is_equal_to(data)

    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=50)
    def test_strip_json_block_preserves_content(self, content):
        """Property: strip_json_block should not lose non-marker content."""
        assume(not content.startswith("```"))
        assume(not content.endswith("```"))

        # If content doesn't have markers, it should remain unchanged (except whitespace)
        result = strip_json_block(content)
        assert_that(result).is_equal_to(content.strip())

    @given(json_objects())
    @settings(max_examples=50)
    def test_markdown_wrapped_json_parses(self, obj):
        """Property: JSON wrapped in markdown should parse after stripping."""
        json_str = json.dumps(obj)
        wrapped = f"```json\n{json_str}\n```"

        stripped = strip_json_block(wrapped)
        parsed = json.loads(stripped)
        assert_that(parsed).is_equal_to(obj)

    @given(json_objects())
    @settings(max_examples=50)
    def test_plain_markdown_wrapped_json_parses(self, obj):
        """Property: JSON in plain markdown should parse after stripping."""
        json_str = json.dumps(obj)
        wrapped = f"```\n{json_str}\n```"

        stripped = strip_json_block(wrapped)
        parsed = json.loads(stripped)
        assert_that(parsed).is_equal_to(obj)

    @given(st.text())
    @settings(max_examples=100)
    def test_strip_json_block_never_raises(self, content):
        """Property: strip_json_block should never raise exceptions."""
        try:
            result = strip_json_block(content)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"strip_json_block raised {type(e).__name__}: {e}")


# =============================================================================
# Property Tests: Filename Sanitization
# =============================================================================


class TestFilenameSanitizationProperties:
    """Property-based tests for filename sanitization."""

    @given(st.text(max_size=200))
    @settings(max_examples=100)
    def test_sanitize_never_raises(self, input_str):
        """Property: sanitize_filename should never raise exceptions."""
        try:
            result = sanitize_filename(input_str)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"sanitize_filename raised {type(e).__name__}: {e}")

    @given(st.text(min_size=1, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd")
    )))
    @settings(max_examples=50)
    def test_alphanumeric_preserved(self, input_str):
        """Property: alphanumeric content should be mostly preserved."""
        result = sanitize_filename(input_str)
        # Result should be lowercase version
        assert_that(result).is_equal_to(input_str.lower())

    @given(st.text(max_size=100))
    @settings(max_examples=100)
    def test_no_special_chars_in_result(self, input_str):
        """Property: result should contain only safe filename characters."""
        result = sanitize_filename(input_str)
        # Only alphanumeric, underscores, and hyphens allowed
        for char in result:
            assert char.isalnum() or char in "_-", f"Invalid char: {char}"

    @given(st.text(max_size=100))
    @settings(max_examples=50)
    def test_result_is_lowercase(self, input_str):
        """Property: result should be lowercase."""
        result = sanitize_filename(input_str)
        assert_that(result).is_equal_to(result.lower())


# =============================================================================
# Property Tests: Provider Initialization
# =============================================================================


class TestProviderInitializationProperties:
    """Property-based tests for provider initialization."""

    @given(
        model=model_name_strategy,
        base_url=base_url_strategy,
        timeout=timeout_strategy,
        temperature=temperature_strategy,
    )
    @settings(max_examples=50)
    def test_provider_init_accepts_valid_params(
        self, model, base_url, timeout, temperature
    ):
        """Property: provider init should accept valid parameters."""
        assume(len(model) > 0)

        provider = ConcreteOpenAIProvider(
            model=model,
            base_url=base_url,
            timeout=timeout,
            temperature=temperature,
        )

        assert_that(provider.model).is_equal_to(model)
        assert_that(provider.base_url).is_equal_to(base_url)
        assert_that(provider.timeout).is_equal_to(timeout)
        assert_that(provider.temperature).is_equal_to(temperature)

    @given(max_retries=st.integers(min_value=1, max_value=20))
    @settings(max_examples=20)
    def test_max_retries_stored(self, max_retries):
        """Property: max_retries should be stored correctly."""
        provider = ConcreteOpenAIProvider(
            model="test",
            base_url="https://api.test.com",
            max_retries=max_retries,
        )
        assert_that(provider.max_retries).is_equal_to(max_retries)

    @given(json_parse_retries=st.integers(min_value=1, max_value=20))
    @settings(max_examples=20)
    def test_json_parse_retries_stored(self, json_parse_retries):
        """Property: json_parse_retries should be stored correctly."""
        provider = ConcreteOpenAIProvider(
            model="test",
            base_url="https://api.test.com",
            json_parse_retries=json_parse_retries,
        )
        assert_that(provider.json_parse_retries).is_equal_to(json_parse_retries)


# =============================================================================
# Property Tests: Subject Configuration
# =============================================================================


class TestSubjectConfigProperties:
    """Property-based tests for SubjectConfig."""

    @given(
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="_-"
        )),
        deck_prefix=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=30)
    def test_subject_config_creation(self, name, deck_prefix):
        """Property: SubjectConfig should accept valid parameters."""
        assume(len(name) > 0 and len(deck_prefix) > 0)

        config = SubjectConfig(
            name=name,
            target_questions={"Category": ["Question"]},
            initial_prompt="Test prompt",
            combine_prompt="Combine prompt",
            target_model=LeetCodeProblem,
            deck_prefix=deck_prefix,
            deck_prefix_mcq=f"{deck_prefix}_MCQ",
        )

        assert_that(config.name).is_equal_to(name)
        assert_that(config.deck_prefix).is_equal_to(deck_prefix)

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll"),
            whitelist_characters=" _-"
        )),
        values=st.lists(
            st.text(min_size=1, max_size=50),
            min_size=1,
            max_size=10,
        ),
        min_size=0,
        max_size=5,
    ))
    @settings(max_examples=30)
    def test_question_dict_stored(self, questions):
        """Property: questions dict should be stored as-is."""
        config = SubjectConfig(
            name="test",
            target_questions=questions,
            initial_prompt="Test",
            combine_prompt="Combine",
            target_model=LeetCodeProblem,
            deck_prefix="Test",
            deck_prefix_mcq="Test_MCQ",
        )

        assert_that(config.target_questions).is_equal_to(questions)


# =============================================================================
# Property Tests: Retry Decorator
# =============================================================================


class TestRetryDecoratorProperties:
    """Property-based tests for retry decorator behavior."""

    @given(max_retries=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_retry_count_respected(self, max_retries):
        """Property: retry count should not exceed max_retries."""
        call_count = 0

        @create_retry_decorator(max_retries=max_retries, min_wait=0.001, max_wait=0.001)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise RetryableError("fail")

        with pytest.raises(RetryableError):
            await always_fails()

        assert_that(call_count).is_equal_to(max_retries)

    @given(success_at=st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_success_on_nth_attempt(self, success_at):
        """Property: should succeed when attempt succeeds within retry limit."""
        call_count = 0
        max_retries = success_at + 2  # Ensure enough retries

        @create_retry_decorator(max_retries=max_retries, min_wait=0.001, max_wait=0.001)
        async def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < success_at:
                raise RetryableError("not yet")
            return "success"

        result = await fails_then_succeeds()
        assert_that(result).is_equal_to("success")
        assert_that(call_count).is_equal_to(success_at)


# =============================================================================
# Property Tests: Task Runner
# =============================================================================


class TestTaskRunnerProperties:
    """Property-based tests for ConcurrentTaskRunner."""

    @given(task_count=st.integers(min_value=0, max_value=50))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_all_tasks_return_results(self, task_count):
        """Property: run_all should return result for every task."""
        runner = ConcurrentTaskRunner(max_concurrent=5)

        async def simple_task(i):
            return i

        tasks = [lambda i=i: simple_task(i) for i in range(task_count)]
        results = await runner.run_all(tasks)

        assert len(results) == task_count

    @given(
        max_concurrent=st.integers(min_value=1, max_value=10),
        task_count=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_concurrency_limit_respected(self, max_concurrent, task_count):
        """Property: concurrent execution should not exceed limit."""
        import asyncio

        concurrent_count = 0
        max_seen = 0

        async def counting_task():
            nonlocal concurrent_count, max_seen
            concurrent_count += 1
            max_seen = max(max_seen, concurrent_count)
            await asyncio.sleep(0.001)
            concurrent_count -= 1
            return True

        runner = ConcurrentTaskRunner(max_concurrent=max_concurrent)
        tasks = [counting_task for _ in range(task_count)]
        await runner.run_all(tasks)

        assert max_seen <= max_concurrent

    @given(success_indices=st.lists(st.booleans(), min_size=1, max_size=20))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_success_failure_separation(self, success_indices):
        """Property: successes and failures should be correctly identified."""
        runner = ConcurrentTaskRunner(max_concurrent=10)

        async def conditional_task(should_succeed):
            if should_succeed:
                return "ok"
            raise ValueError("failed")

        tasks = [lambda s=s: conditional_task(s) for s in success_indices]
        results = await runner.run_all(tasks)

        expected_successes = sum(success_indices)
        expected_failures = len(success_indices) - expected_successes

        actual_successes = len([r for r in results if isinstance(r, Success)])
        actual_failures = len([r for r in results if isinstance(r, Failure)])

        assert_that(actual_successes).is_equal_to(expected_successes)
        assert_that(actual_failures).is_equal_to(expected_failures)


# =============================================================================
# Property Tests: Success/Failure Types
# =============================================================================


class TestResultTypeProperties:
    """Property-based tests for Success/Failure result types."""

    @given(st.one_of(
        st.text(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.none(),
        st.lists(st.integers()),
        st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.integers(),
        ),
    ))
    @settings(max_examples=50)
    def test_success_stores_any_value(self, value):
        """Property: Success should store any value correctly."""
        result = Success(value=value)
        assert_that(result.value).is_equal_to(value)
        assert result.is_success() is True
        assert result.is_failure() is False

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=30)
    def test_failure_stores_exception(self, message):
        """Property: Failure should store exception correctly."""
        exception = ValueError(message)
        result = Failure(exception=exception)

        assert result.exception is exception
        assert result.is_failure() is True
        assert result.is_success() is False


# =============================================================================
# Property Tests: Error Class Hierarchy
# =============================================================================


class TestErrorHierarchyProperties:
    """Property-based tests for error class hierarchy."""

    @given(message=st.text(max_size=200))
    @settings(max_examples=30)
    def test_rate_limit_error_inherits_retryable(self, message):
        """Property: RateLimitError should be RetryableError."""
        error = RateLimitError(message)
        assert isinstance(error, RetryableError)
        assert isinstance(error, Exception)

    @given(message=st.text(max_size=200))
    @settings(max_examples=30)
    def test_timeout_error_inherits_retryable(self, message):
        """Property: TimeoutError should be RetryableError."""
        error = TimeoutError(message)
        assert isinstance(error, RetryableError)
        assert isinstance(error, Exception)

    @given(message=st.text(max_size=200))
    @settings(max_examples=30)
    def test_empty_response_error_inherits_retryable(self, message):
        """Property: EmptyResponseError should be RetryableError."""
        error = EmptyResponseError(message)
        assert isinstance(error, RetryableError)
        assert isinstance(error, Exception)

    @given(
        error_class=st.sampled_from([RateLimitError, TimeoutError, EmptyResponseError]),
        message=st.text(max_size=100),
    )
    @settings(max_examples=30)
    def test_error_message_preserved(self, error_class, message):
        """Property: error message should be preserved."""
        error = error_class(message)
        assert str(error) == message


# =============================================================================
# Property Tests: Unicode Handling
# =============================================================================


class TestUnicodeProperties:
    """Property-based tests for Unicode handling."""

    @given(st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Lo", "Nl", "Nd", "Zs"),
        ),
        max_size=500,
    ))
    @settings(max_examples=50)
    def test_unicode_json_roundtrip(self, text):
        """Property: Unicode text should roundtrip through JSON."""
        data = {"content": text}
        json_str = json.dumps(data, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert_that(parsed).is_equal_to(data)

    @given(st.text(alphabet=st.characters(
        whitelist_categories=("Lo",),  # Other letters (CJK, etc.)
    ), min_size=1, max_size=100))
    @settings(max_examples=30)
    def test_cjk_characters_preserved(self, text):
        """Property: CJK characters should be preserved in JSON."""
        data = {"text": text}
        json_str = json.dumps(data, ensure_ascii=False)
        assert_that(json_str).contains(text)
        parsed = json.loads(json_str)
        assert parsed["text"] == text

    @given(st.text(max_size=100))
    @settings(max_examples=50)
    def test_escaped_unicode_roundtrip(self, text):
        """Property: escaped Unicode should roundtrip correctly."""
        data = {"text": text}
        # Force ASCII escaping
        json_str = json.dumps(data, ensure_ascii=True)
        parsed = json.loads(json_str)
        assert_that(parsed).is_equal_to(data)


# =============================================================================
# Property Tests: API Key Iterator
# =============================================================================


class TestAPIKeyIteratorProperties:
    """Property-based tests for API key iteration."""

    @given(keys=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10))
    @settings(max_examples=30)
    def test_key_cycling(self, keys):
        """Property: keys should cycle through in order."""
        provider = ConcreteOpenAIProvider(
            model="test",
            base_url="https://api.test.com",
            api_keys=itertools.cycle(keys),
        )

        retrieved = [provider._get_api_key() for _ in range(len(keys) * 2)]

        # First cycle
        assert retrieved[:len(keys)] == keys
        # Second cycle (cycling back)
        assert retrieved[len(keys):] == keys

    def test_none_keys_returns_empty(self):
        """Property: None api_keys should return empty string."""
        provider = ConcreteOpenAIProvider(
            model="test",
            base_url="https://api.test.com",
            api_keys=None,
        )

        assert provider._get_api_key() == ""


# =============================================================================
# Property Tests: Extra Request Parameters
# =============================================================================


class TestExtraParamsProperties:
    """Property-based tests for extra request parameters."""

    @given(top_p=st.floats(min_value=0.0, max_value=1.0))
    @settings(max_examples=30)
    def test_top_p_included_when_set(self, top_p):
        """Property: top_p should be included when set."""
        provider = ConcreteOpenAIProvider(
            model="test",
            base_url="https://api.test.com",
            top_p=top_p,
        )

        params = provider._get_extra_request_params()
        assert params.get("top_p") == top_p

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll"),
        )),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=0,
        max_size=5,
    ))
    @settings(max_examples=30)
    def test_extra_params_passed_through(self, extra_params):
        """Property: extra_params should be included in result."""
        provider = ConcreteOpenAIProvider(
            model="test",
            base_url="https://api.test.com",
            extra_params=extra_params,
        )

        params = provider._get_extra_request_params()
        for key, value in extra_params.items():
            assert params.get(key) == value
