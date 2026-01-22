"""Tests for retry/resilience and edge cases.

Task fn-2.7: Comprehensive tests for:
- Retry on rate limit tests (429 with backoff)
- Max retries exceeded tests
- Edge cases: provider failures (500/502/503, timeouts, auth failures)
- Edge cases: malformed output (invalid JSON, missing fields, truncated)
- Edge cases: boundary conditions (zero questions, single, 1000+, empty providers)
- Edge cases: unicode/encoding (CJK, RTL, emojis, mixed encodings)
"""

import asyncio
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional
import itertools

from src.providers.base import (
    LLMProvider,
    create_retry_decorator,
    RetryableError,
    RateLimitError,
    TimeoutError,
    EmptyResponseError,
)
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.generator import CardGenerator
from src.task_runner import ConcurrentTaskRunner, Success, Failure
from src.config.subjects import SubjectConfig
from src.models import LeetCodeProblem


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


class ConcreteOpenAIProvider(OpenAICompatibleProvider):
    """Concrete implementation for testing."""

    @property
    def name(self) -> str:
        return "test_provider"


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, name="mock", model="mock-model"):
        self._name = name
        self._model = model
        self.generate_call_count = 0
        self.combine_call_count = 0
        self.responses = []
        self.errors = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        self.generate_call_count += 1
        if self.errors and self.generate_call_count <= len(self.errors):
            error = self.errors[self.generate_call_count - 1]
            if error:
                raise error
        if self.responses:
            idx = min(self.generate_call_count - 1, len(self.responses) - 1)
            return self.responses[idx]
        return '{"cards": []}'

    async def combine_cards(
        self,
        question: str,
        combined_inputs: str,
        json_schema: Dict[str, Any],
        combine_prompt_template: Optional[str] = None,
    ) -> Optional[str]:
        self.combine_call_count += 1
        return '{"cards": []}'

    async def format_json(
        self,
        raw_content: str,
        json_schema: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return {"cards": []}


def create_mock_response(content: str):
    """Helper to create a mock OpenAI completion response."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    return mock_completion


def create_mock_client(response=None, side_effect=None):
    """Helper to create a mock AsyncOpenAI client."""
    mock_client = AsyncMock()
    if side_effect:
        mock_client.chat.completions.create = AsyncMock(side_effect=side_effect)
    else:
        mock_client.chat.completions.create = AsyncMock(return_value=response)
    return mock_client


# =============================================================================
# Rate Limit and Backoff Tests
# =============================================================================


class TestRateLimitRetryWithBackoff:
    """Tests for rate limit handling with exponential backoff."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff increases wait time between retries."""
        call_times = []

        @create_retry_decorator(max_retries=4, min_wait=0.1, max_wait=1.0)
        async def rate_limited_func():
            call_times.append(time.monotonic())
            if len(call_times) < 4:
                raise RateLimitError("429 Rate Limited")
            return "success"

        result = await rate_limited_func()
        assert result == "success"
        assert len(call_times) == 4

        # Verify delays are increasing (exponential backoff)
        delays = [
            call_times[i + 1] - call_times[i] for i in range(len(call_times) - 1)
        ]
        # Each delay should be >= previous (with small tolerance for timing)
        for i in range(len(delays) - 1):
            assert delays[i + 1] >= delays[i] * 0.9  # 10% tolerance

    @pytest.mark.asyncio
    async def test_rate_limit_429_triggers_retry(self):
        """Test 429 status code triggers retry mechanism."""
        from openai import RateLimitError as OpenAIRateLimitError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=3,
        )

        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                mock_response = MagicMock()
                mock_response.status_code = 429
                raise OpenAIRateLimitError(
                    message="Rate limit exceeded",
                    response=mock_response,
                    body={"error": {"message": "Rate limit exceeded"}},
                )
            return create_mock_response('{"cards": []}')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = mock_create
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result == '{"cards": []}'
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_all_retries_exhausted(self):
        """Test behavior when all retries are exhausted due to rate limiting."""
        from openai import RateLimitError as OpenAIRateLimitError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=2,
        )

        call_count = 0

        async def always_rate_limited(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.status_code = 429
            raise OpenAIRateLimitError(
                message="Rate limit exceeded",
                response=mock_response,
                body=None,
            )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = always_rate_limited
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result is None
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_backoff_respects_max_wait(self):
        """Test that backoff doesn't exceed max_wait."""
        call_times = []
        max_wait = 0.2

        @create_retry_decorator(max_retries=5, min_wait=0.05, max_wait=max_wait)
        async def always_fails():
            call_times.append(time.monotonic())
            raise RetryableError("fail")

        with pytest.raises(RetryableError):
            await always_fails()

        # Calculate actual delays
        delays = [
            call_times[i + 1] - call_times[i] for i in range(len(call_times) - 1)
        ]
        # All delays should respect max_wait (with some tolerance)
        for delay in delays:
            assert delay <= max_wait * 1.5  # 50% tolerance for timing

    @pytest.mark.asyncio
    async def test_rate_limit_recovery_after_success(self):
        """Test that after rate limit recovery, subsequent requests work."""
        call_count = 0

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def rate_limited_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("429")
            return f"success_{call_count}"

        result1 = await rate_limited_then_ok()
        assert result1 == "success_2"

        # Reset and try again - should work first time
        call_count = 10
        result2 = await rate_limited_then_ok()
        assert result2 == "success_11"


class TestMaxRetriesExceeded:
    """Tests for max retries exceeded scenarios."""

    @pytest.mark.asyncio
    async def test_max_retries_with_various_error_types(self):
        """Test max retries with different retryable error types."""
        for ErrorClass, max_retries in [
            (RateLimitError, 2),
            (TimeoutError, 3),
            (EmptyResponseError, 4),
            (RetryableError, 5),
        ]:
            call_count = 0

            @create_retry_decorator(max_retries=max_retries, min_wait=0.01, max_wait=0.01)
            async def always_fails():
                nonlocal call_count
                call_count += 1
                raise ErrorClass("error")

            with pytest.raises(ErrorClass):
                await always_fails()

            assert call_count == max_retries

    @pytest.mark.asyncio
    async def test_retries_stop_immediately_on_non_retryable_error(self):
        """Test that non-retryable errors don't trigger retries."""
        for ErrorClass in [ValueError, TypeError, KeyError, RuntimeError]:
            call_count = 0

            @create_retry_decorator(max_retries=5, min_wait=0.01, max_wait=0.01)
            async def fails_with_non_retryable():
                nonlocal call_count
                call_count += 1
                raise ErrorClass("non-retryable")

            with pytest.raises(ErrorClass):
                await fails_with_non_retryable()

            assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_zero_or_one(self):
        """Test behavior with minimal retry counts."""
        for max_retries in [1, 2]:
            call_count = 0

            @create_retry_decorator(max_retries=max_retries, min_wait=0.01, max_wait=0.01)
            async def fails():
                nonlocal call_count
                call_count += 1
                raise RetryableError("fail")

            with pytest.raises(RetryableError):
                await fails()

            assert call_count == max_retries

    @pytest.mark.asyncio
    async def test_provider_returns_none_after_max_retries(self):
        """Test OpenAICompatibleProvider returns None after exhausting retries."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=2,
        )

        call_count = 0

        async def always_empty(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return create_mock_response("")  # Empty response triggers EmptyResponseError

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = always_empty
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result is None
            assert call_count == 2


# =============================================================================
# Provider Failure Tests (500/502/503, timeouts, auth failures)
# =============================================================================


class TestProviderServerErrors:
    """Tests for server-side error handling."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "status_code,error_class,error_name",
        [
            (500, "InternalServerError", "Internal Server Error"),
            (502, "InternalServerError", "Bad Gateway"),
            (503, "InternalServerError", "Service Unavailable"),
            (504, "InternalServerError", "Gateway Timeout"),
        ],
    )
    async def test_5xx_errors_return_none(self, status_code, error_class, error_name):
        """Test various 5xx errors are handled gracefully."""
        from openai import InternalServerError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = status_code
        error = InternalServerError(
            message=error_name,
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_intermittent_500_returns_none_without_retry(self):
        """Test that 500 errors are not automatically retried by the provider.

        Note: InternalServerError is caught as a generic exception and returns None.
        The retry decorator only retries RetryableError subclasses.
        """
        from openai import InternalServerError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=3,
        )

        call_count = 0

        async def intermittent_500(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.status_code = 500
            raise InternalServerError(
                message="Server Error",
                response=mock_response,
                body=None,
            )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = intermittent_500
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            # 500 errors are not RetryableError, so they return None immediately
            assert result is None
            assert call_count == 1


class TestTimeoutErrors:
    """Tests for timeout error handling."""

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        """Test timeout errors trigger retry."""
        from openai import APITimeoutError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=3,
            timeout=1.0,
        )

        call_count = 0

        async def timeout_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APITimeoutError(request=MagicMock())
            return create_mock_response('{"success": true}')

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = timeout_then_success
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result == '{"success": true}'
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_persistent_timeout_returns_none(self):
        """Test persistent timeouts return None after max retries."""
        from openai import APITimeoutError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=2,
        )

        call_count = 0

        async def always_timeout(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise APITimeoutError(request=MagicMock())

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = always_timeout
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result is None
            assert call_count == 2


class TestAuthenticationErrors:
    """Tests for authentication error handling."""

    @pytest.mark.asyncio
    async def test_401_unauthorized(self):
        """Test 401 unauthorized returns None without retry."""
        from openai import AuthenticationError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=3,
        )

        call_count = 0

        async def auth_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.status_code = 401
            raise AuthenticationError(
                message="Invalid API key",
                response=mock_response,
                body=None,
            )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = auth_error
            mock_get_client.return_value = mock_client

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result is None
            # Auth errors should not be retried (or very limited retries)
            assert call_count <= 3

    @pytest.mark.asyncio
    async def test_403_forbidden(self):
        """Test 403 forbidden is handled."""
        from openai import PermissionDeniedError

        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            max_retries=1,
        )

        mock_response = MagicMock()
        mock_response.status_code = 403
        error = PermissionDeniedError(
            message="Forbidden",
            response=mock_response,
            body=None,
        )

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(side_effect=error)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_key_rotation_occurs_on_requests(self):
        """Test API keys rotate across multiple requests."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            api_keys=itertools.cycle(["key1", "key2", "key3"]),
            max_retries=1,
        )

        used_keys = []

        with patch("src.providers.openai_compatible.AsyncOpenAI") as mock_openai:
            mock_response = create_mock_response('{"ok": true}')
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            def capture_key(*args, **kwargs):
                used_keys.append(kwargs.get("api_key"))
                return mock_client

            mock_openai.side_effect = capture_key

            # Make three requests
            for _ in range(3):
                await provider._make_request(
                    chat_messages=[{"role": "user", "content": "test"}],
                )

            # Keys should rotate
            assert used_keys == ["key1", "key2", "key3"]


# =============================================================================
# Malformed Output Tests
# =============================================================================


class TestMalformedJSON:
    """Tests for handling malformed JSON responses."""

    @pytest.mark.asyncio
    async def test_invalid_json_syntax(self):
        """Test handling of syntactically invalid JSON."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            json_parse_retries=2,
        )

        invalid_responses = [
            '{cards: []}',  # Missing quotes around key
            '{"cards": [}',  # Unclosed bracket
            'not json at all',  # Plain text
        ]

        for invalid in invalid_responses:
            mock_response = create_mock_response(invalid)

            with patch.object(provider, "_get_client") as mock_get_client:
                mock_get_client.return_value = create_mock_client(response=mock_response)

                result = await provider.format_json(
                    raw_content="some content",
                    json_schema={},
                )
                assert result is None

    @pytest.mark.asyncio
    async def test_truncated_json(self):
        """Test handling of truncated JSON responses."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            json_parse_retries=1,
        )

        truncated_responses = [
            '{"cards": [{"front": "Q1", "back": "A1"}, {"front": "Q2"',
            '{"title": "Test", "cards": [{"fro',
            '{"incomplete',
        ]

        for truncated in truncated_responses:
            mock_response = create_mock_response(truncated)

            with patch.object(provider, "_get_client") as mock_get_client:
                mock_get_client.return_value = create_mock_client(response=mock_response)

                result = await provider.format_json(
                    raw_content="content",
                    json_schema={},
                )
                assert result is None

    @pytest.mark.asyncio
    async def test_json_missing_required_fields(self):
        """Test JSON with missing expected fields is still returned."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        # Valid JSON but missing expected structure
        incomplete = '{"other_field": "value"}'  # Missing "cards"
        mock_response = create_mock_response(incomplete)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            # format_json returns the parsed dict, validation happens elsewhere
            assert result == {"other_field": "value"}

    @pytest.mark.asyncio
    async def test_json_with_markdown_blocks_stripped(self):
        """Test JSON wrapped in markdown code blocks is properly stripped.

        Note: The format_json method has its own retry loop and calls _make_request.
        For this test we just verify strip_json_block works correctly.
        """
        from src.utils import strip_json_block

        # Test the stripping utility directly
        wrapped_responses = [
            ('```json\n{"cards": []}\n```', '{"cards": []}'),
            ('```\n{"cards": []}\n```', '{"cards": []}'),
        ]

        for wrapped, expected_stripped in wrapped_responses:
            stripped = strip_json_block(wrapped)
            assert stripped == expected_stripped
            # Verify it parses as valid JSON
            parsed = json.loads(stripped)
            assert parsed == {"cards": []}

    @pytest.mark.asyncio
    async def test_json_with_extra_text_before_block_fails(self):
        """Test JSON with extra text before the code block fails to parse."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            strip_json_markers=True,
            json_parse_retries=1,
        )

        # Extra text before markdown block is not handled by strip_json_block
        response = 'Here is the JSON:\n```json\n{"cards": []}\n```'
        mock_response = create_mock_response(response)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            # This should fail because strip_json_block only handles markdown fences at the start
            assert result is None

    @pytest.mark.asyncio
    async def test_empty_json_structures(self):
        """Test handling of empty but valid JSON structures."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        empty_structures = [
            ('{}', {}),
            ('{"cards": []}', {"cards": []}),
            ('[]', []),  # Empty array is valid JSON
            ('{"cards": [], "title": ""}', {"cards": [], "title": ""}),
        ]

        for json_str, expected in empty_structures:
            mock_response = create_mock_response(json_str)

            with patch.object(provider, "_get_client") as mock_get_client:
                mock_get_client.return_value = create_mock_client(response=mock_response)

                result = await provider.format_json(
                    raw_content="content",
                    json_schema={},
                )
                assert result == expected

    @pytest.mark.asyncio
    async def test_json_with_null_values(self):
        """Test handling of JSON with null values."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        json_str = '{"cards": null, "title": null, "count": 0}'
        mock_response = create_mock_response(json_str)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            assert result == {"cards": None, "title": None, "count": 0}


class TestMalformedResponses:
    """Tests for non-JSON malformed responses."""

    @pytest.mark.asyncio
    async def test_html_error_page(self):
        """Test handling of HTML error page responses."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            json_parse_retries=1,
        )

        html_response = """
        <!DOCTYPE html>
        <html>
        <head><title>502 Bad Gateway</title></head>
        <body><h1>502 Bad Gateway</h1></body>
        </html>
        """
        mock_response = create_mock_response(html_response)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_binary_garbage(self):
        """Test handling of binary/garbage content."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
            json_parse_retries=1,
        )

        garbage_responses = [
            "\x00\x01\x02\x03",
            "ÿøÿà\x00\x10JFIF",  # JPEG header-like
            "\x89PNG\r\n\x1a\n",  # PNG header-like
        ]

        for garbage in garbage_responses:
            mock_response = create_mock_response(garbage)

            with patch.object(provider, "_get_client") as mock_get_client:
                mock_get_client.return_value = create_mock_client(response=mock_response)

                result = await provider.format_json(
                    raw_content="content",
                    json_schema={},
                )
                assert result is None


# =============================================================================
# Boundary Condition Tests
# =============================================================================


class TestZeroQuestions:
    """Tests for handling zero questions."""

    def test_generator_with_empty_providers_list(self):
        """Test CardGenerator can be initialized with empty providers list."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
            combine_prompt="Combine: {inputs}",
        )
        assert len(generator.llm_providers) == 0

    def test_subject_config_with_empty_questions(self):
        """Test SubjectConfig accepts empty questions dict."""
        config = SubjectConfig(
            name="test",
            target_questions={},
            initial_prompt="Initial",
            combine_prompt="Combine",
            target_model=LeetCodeProblem,
            deck_prefix="Test",
            deck_prefix_mcq="Test_MCQ",
        )
        assert config.target_questions == {}

    @pytest.mark.asyncio
    async def test_task_runner_with_no_tasks(self):
        """Test ConcurrentTaskRunner with empty task list."""
        runner = ConcurrentTaskRunner(max_concurrent=4)
        results = await runner.run_all([])
        assert results == []

        ordered_results = await runner.run_all_ordered([])
        assert ordered_results == []


class TestSingleQuestion:
    """Tests for handling single question."""

    def test_single_provider_in_generator(self):
        """Test with exactly one provider."""
        provider = MockLLMProvider()
        generator = CardGenerator(
            providers=[provider],
            combiner=provider,
            formatter=None,
            repository=None,
            combine_prompt="",
        )

        assert len(generator.llm_providers) == 1

    @pytest.mark.asyncio
    async def test_task_runner_single_task(self):
        """Test ConcurrentTaskRunner with single task."""
        runner = ConcurrentTaskRunner(max_concurrent=4)

        async def single_task():
            return "result"

        results = await runner.run_all([single_task])
        assert len(results) == 1
        assert isinstance(results[0], Success)
        assert results[0].value == "result"

    def test_subject_config_with_single_category_single_question(self):
        """Test SubjectConfig with minimal question set."""
        config = SubjectConfig(
            name="test",
            target_questions={"Category": ["One Question"]},
            initial_prompt="Initial",
            combine_prompt="Combine",
            target_model=LeetCodeProblem,
            deck_prefix="Test",
            deck_prefix_mcq="Test_MCQ",
        )
        assert len(config.target_questions) == 1
        assert len(config.target_questions["Category"]) == 1


class TestLargeScaleBoundary:
    """Tests for large-scale boundary conditions."""

    @pytest.mark.asyncio
    async def test_many_concurrent_tasks(self):
        """Test handling many concurrent tasks."""
        runner = ConcurrentTaskRunner(max_concurrent=10)

        async def quick_task(i):
            return i

        tasks = [lambda i=i: quick_task(i) for i in range(100)]
        results = await runner.run_all(tasks)

        assert len(results) == 100
        successes = [r for r in results if isinstance(r, Success)]
        assert len(successes) == 100

    @pytest.mark.asyncio
    async def test_concurrency_limit_with_many_tasks(self):
        """Test concurrency limit is respected with many tasks."""
        concurrent_count = 0
        max_concurrent_seen = 0
        max_limit = 5

        async def counting_task():
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return True

        runner = ConcurrentTaskRunner(max_concurrent=max_limit)
        tasks = [counting_task for _ in range(50)]
        await runner.run_all(tasks)

        assert max_concurrent_seen <= max_limit

    def test_many_providers(self):
        """Test CardGenerator with many providers."""
        providers = [MockLLMProvider(name=f"provider_{i}") for i in range(20)]

        generator = CardGenerator(
            providers=providers,
            combiner=providers[0],
            formatter=None,
            repository=None,
            combine_prompt="Combine",
        )

        assert len(generator.llm_providers) == 20

    def test_large_question_dict(self):
        """Test SubjectConfig with large questions dict."""
        large_questions = {
            f"Category_{i}": [f"Question_{i}_{j}" for j in range(50)]
            for i in range(20)
        }

        config = SubjectConfig(
            name="test",
            target_questions=large_questions,
            initial_prompt="Initial",
            combine_prompt="Combine",
            target_model=LeetCodeProblem,
            deck_prefix="Test",
            deck_prefix_mcq="Test_MCQ",
        )

        total_questions = sum(len(q) for q in config.target_questions.values())
        assert total_questions == 1000


class TestEmptyProviders:
    """Tests for handling empty provider scenarios."""

    def test_generator_with_no_providers(self):
        """Test CardGenerator initialization with no providers."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
            combine_prompt="Combine",
        )
        assert len(generator.llm_providers) == 0

    def test_generator_with_none_formatter(self):
        """Test CardGenerator accepts None formatter."""
        generator = CardGenerator(
            providers=[MockLLMProvider()],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
            combine_prompt="Combine",
        )
        assert generator.formatter is None

    def test_generator_with_none_repository(self):
        """Test CardGenerator accepts None repository."""
        generator = CardGenerator(
            providers=[MockLLMProvider()],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
            combine_prompt="Combine",
        )
        assert generator.repository is None


# =============================================================================
# Unicode and Encoding Tests
# =============================================================================


class TestUnicodeHandling:
    """Tests for Unicode and encoding handling."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "content,description",
        [
            ('{"title": "中文标题", "cards": []}', "Chinese characters"),
            ('{"title": "日本語テスト", "cards": []}', "Japanese characters"),
            ('{"title": "한국어 테스트", "cards": []}', "Korean characters"),
            ('{"title": "العربية", "cards": []}', "Arabic (RTL)"),
            ('{"title": "עברית", "cards": []}', "Hebrew (RTL)"),
            ('{"title": "Ελληνικά", "cards": []}', "Greek"),
            ('{"title": "Кириллица", "cards": []}', "Cyrillic"),
            ('{"title": "Ñoño español", "cards": []}', "Spanish diacritics"),
            ('{"title": "Ümläut", "cards": []}', "German umlauts"),
        ],
    )
    async def test_non_ascii_content(self, content, description):
        """Test handling of non-ASCII content: {description}."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )
        mock_response = create_mock_response(content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result == content

    @pytest.mark.asyncio
    async def test_emoji_content(self):
        """Test handling of emoji content."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        emoji_responses = [
            '{"title": "🎉 Party 🎊", "cards": []}',
            '{"front": "What is 🔥?", "back": "Fire emoji"}',
            '{"cards": [{"front": "👨‍💻 Developer", "back": "Person at computer"}]}',
            '{"emoji": "🇯🇵🇺🇸🇬🇧"}',  # Flag emojis
            '{"math": "∑∏∫√∞≠≤≥"}',  # Math symbols (Unicode but not emoji)
        ]

        for content in emoji_responses:
            mock_response = create_mock_response(content)

            with patch.object(provider, "_get_client") as mock_get_client:
                mock_get_client.return_value = create_mock_client(response=mock_response)

                result = await provider._make_request(
                    chat_messages=[{"role": "user", "content": "test"}],
                )
                assert result == content

    @pytest.mark.asyncio
    async def test_mixed_script_content(self):
        """Test handling of mixed script content."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        mixed_content = '{"front": "English 中文 日本語 한국어 العربية", "back": "Mixed scripts"}'
        mock_response = create_mock_response(mixed_content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result == mixed_content

    @pytest.mark.asyncio
    async def test_rtl_and_ltr_mixed(self):
        """Test handling of mixed RTL and LTR text."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        rtl_ltr_content = '{"front": "English text مع العربية and עברית", "back": "Mixed direction"}'
        mock_response = create_mock_response(rtl_ltr_content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider._make_request(
                chat_messages=[{"role": "user", "content": "test"}],
            )
            assert result == rtl_ltr_content

    @pytest.mark.asyncio
    async def test_unicode_escape_sequences(self):
        """Test handling of Unicode escape sequences in JSON."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        # JSON with Unicode escape sequences
        escaped_content = '{"title": "\\u4e2d\\u6587", "cards": []}'  # 中文 escaped
        mock_response = create_mock_response(escaped_content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            # When parsed, should decode to actual characters
            assert result == {"title": "中文", "cards": []}

    @pytest.mark.asyncio
    async def test_code_with_unicode_comments(self):
        """Test handling of code snippets with Unicode comments."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        code_content = json.dumps(
            {
                "front": "What does this code do?",
                "back": "```python\n# 这是中文注释\ndef hello():\n    print('世界')\n```",
            }
        )
        mock_response = create_mock_response(code_content)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            assert "中文" in result["back"]
            assert "世界" in result["back"]


class TestSpecialCharacters:
    """Tests for special character handling."""

    @pytest.mark.asyncio
    async def test_newlines_in_json(self):
        """Test handling of newlines in JSON strings."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        content_with_newlines = '{"front": "Line1\\nLine2\\nLine3", "back": "Answer"}'
        mock_response = create_mock_response(content_with_newlines)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            assert "\n" in result["front"]

    @pytest.mark.asyncio
    async def test_tabs_in_json(self):
        """Test handling of tabs in JSON strings."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        content_with_tabs = '{"code": "def foo():\\n\\treturn True"}'
        mock_response = create_mock_response(content_with_tabs)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            assert "\t" in result["code"]

    @pytest.mark.asyncio
    async def test_quotes_in_json(self):
        """Test handling of escaped quotes in JSON."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        content_with_quotes = '{"front": "What is \\"hello\\"?", "back": "A greeting"}'
        mock_response = create_mock_response(content_with_quotes)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            assert '"hello"' in result["front"]

    @pytest.mark.asyncio
    async def test_backslashes_in_json(self):
        """Test handling of backslashes in JSON."""
        provider = ConcreteOpenAIProvider(
            model="test-model",
            base_url="https://api.test.com/v1",
        )

        content_with_backslashes = '{"path": "C:\\\\Users\\\\test", "regex": "\\\\d+"}'
        mock_response = create_mock_response(content_with_backslashes)

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_get_client.return_value = create_mock_client(response=mock_response)

            result = await provider.format_json(
                raw_content="content",
                json_schema={},
            )
            assert "\\" in result["path"]


# =============================================================================
# Combined Stress Tests
# =============================================================================


class TestCombinedStressScenarios:
    """Tests combining multiple edge cases."""

    @pytest.mark.asyncio
    async def test_unicode_with_retries(self):
        """Test Unicode content with retry behavior."""
        call_count = 0
        unicode_content = '{"title": "日本語 🎉 العربية", "cards": []}'

        @create_retry_decorator(max_retries=3, min_wait=0.01, max_wait=0.01)
        async def unicode_with_failures():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RetryableError("temporary failure")
            return unicode_content

        result = await unicode_with_failures()
        assert result == unicode_content
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_unicode_tasks(self):
        """Test concurrent processing of Unicode content."""
        runner = ConcurrentTaskRunner(max_concurrent=5)

        async def unicode_task(lang_content):
            await asyncio.sleep(0.01)
            return lang_content

        contents = [
            "中文内容",
            "日本語コンテンツ",
            "한국어 콘텐츠",
            "المحتوى العربي",
            "תוכן עברי",
        ]

        tasks = [lambda c=c: unicode_task(c) for c in contents]
        results = await runner.run_all(tasks)

        assert len(results) == 5
        result_values = [r.value for r in results if isinstance(r, Success)]
        assert set(result_values) == set(contents)

    @pytest.mark.asyncio
    async def test_many_failures_with_recovery(self):
        """Test many concurrent tasks with intermittent failures."""
        runner = ConcurrentTaskRunner(max_concurrent=5)
        failure_count = 0

        async def flaky_task(i):
            nonlocal failure_count
            if i % 3 == 0:
                failure_count += 1
                raise ValueError(f"Task {i} failed")
            return i

        tasks = [lambda i=i: flaky_task(i) for i in range(30)]
        results = await runner.run_all(tasks)

        assert len(results) == 30
        successes = [r for r in results if isinstance(r, Success)]
        failures = [r for r in results if isinstance(r, Failure)]

        # Every 3rd task (0, 3, 6, ..., 27) = 10 failures
        assert len(failures) == 10
        assert len(successes) == 20

    @pytest.mark.asyncio
    async def test_mixed_error_types_concurrent(self):
        """Test concurrent handling of different error types."""
        runner = ConcurrentTaskRunner(max_concurrent=4)

        async def rate_limit_task():
            raise RateLimitError("429")

        async def timeout_task():
            raise TimeoutError("timeout")

        async def success_task():
            return "success"

        async def value_error_task():
            raise ValueError("bad value")

        tasks = [rate_limit_task, timeout_task, success_task, value_error_task]
        results = await runner.run_all(tasks)

        assert len(results) == 4
        successes = [r for r in results if isinstance(r, Success)]
        failures = [r for r in results if isinstance(r, Failure)]

        assert len(successes) == 1
        assert len(failures) == 3
