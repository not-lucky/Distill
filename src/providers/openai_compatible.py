"""Base class for LLM providers using OpenAI-compatible APIs."""

import json
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Iterator, Callable

from openai import AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError
from openai import APITimeoutError as OpenAITimeoutError
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from src.providers.base import (
    LLMProvider,
    TokenUsage,
    TokenUsageCallback,
    create_retry_decorator,
    RetryableError,
    RateLimitError,
    TimeoutError,
    EmptyResponseError,
)
from src.prompts import prompts
from src.utils import strip_json_block
from src.cache import generate_cache_key, CacheRepository
from src.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """
    Base class for providers using OpenAI-compatible APIs.

    Subclasses only need to define:
    - name property
    - __init__ that calls super().__init__() with appropriate config
    - Optionally override _get_extra_request_params() for provider-specific params
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        api_keys: Optional[Iterator[str]] = None,
        timeout: float = 120.0,
        max_retries: Optional[int] = None,
        json_parse_retries: Optional[int] = None,
        temperature: float = 0.4,
        max_tokens: Optional[int] = None,
        strip_json_markers: bool = True,
        top_p: Optional[float] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        bypass_cache_lookup: bool = False,
        on_token_usage: Optional[TokenUsageCallback] = None,
    ):
        """
        Initialize an OpenAI-compatible provider.

        Args:
            model: Model identifier
            base_url: API base URL
            api_keys: Optional iterator of API keys (for rotation)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for requests (default: DEFAULT_MAX_RETRIES)
            json_parse_retries: Maximum retries for JSON parsing (default: DEFAULT_JSON_PARSE_RETRIES)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response (None for API default)
            strip_json_markers: Whether to strip ```json markers from responses
            top_p: Nucleus sampling parameter (None for API default)
            extra_params: Additional provider-specific parameters
            use_cache: Whether to use response caching (default: True)
            bypass_cache_lookup: If True, skip cache lookup but still store results (default: False)
            on_token_usage: Callback for token usage updates (provider, model, usage, success)
        """
        self.model_name = model
        self.base_url = base_url
        self.api_key_iterator = api_keys
        self.timeout = timeout
        self.max_retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        self.json_parse_retries = json_parse_retries if json_parse_retries is not None else self.DEFAULT_JSON_PARSE_RETRIES
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.strip_json_markers = strip_json_markers
        self.top_p = top_p
        self.extra_params = extra_params or {}
        self.use_cache = use_cache
        self.bypass_cache_lookup = bypass_cache_lookup
        self.on_token_usage = on_token_usage

    @property
    def model(self) -> str:
        return self.model_name

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    def _get_api_key(self) -> str:
        """Get the next API key from the iterator, or empty string if none."""
        if self.api_key_iterator is None:
            return ""
        return next(self.api_key_iterator)

    def _get_client(self) -> AsyncOpenAI:
        """Create an AsyncOpenAI client instance."""
        return AsyncOpenAI(
            api_key=self._get_api_key(),
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def _get_extra_request_params(self) -> Dict[str, Any]:
        """
        Get provider-specific request parameters.

        Uses top_p and extra_params from config. Subclasses can override
        to add additional provider-specific logic.

        Returns:
            Dict of extra parameters to pass to chat.completions.create()
        """
        params = {}
        if self.top_p is not None:
            params["top_p"] = self.top_p
        params.update(self.extra_params)
        return params

    async def _make_request(
        self,
        chat_messages: List[Dict[str, Any]],
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Make a request to the API with retry logic and optional caching.

        Args:
            chat_messages: List of chat messages
            json_schema: Optional JSON schema (used for response formatting)

        Returns:
            Response content string, or None if all retries failed
        """
        cache_key: Optional[str] = None

        # Cache lookup (skip if bypass_cache_lookup is True)
        if self.use_cache:
            try:
                db_manager = DatabaseManager.get_default()
                if db_manager.is_initialized:
                    cache_key = generate_cache_key(
                        provider_name=self.name,
                        model=self.model_name,
                        messages=chat_messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        top_p=self.top_p,
                        json_schema=json_schema,
                    )
                    # Only do cache lookup if not bypassing
                    if not self.bypass_cache_lookup:
                        with db_manager.session_scope() as session:
                            cache_repo = CacheRepository(session)
                            cached = cache_repo.get(cache_key)
                            if cached is not None:
                                logger.info(f"[CACHE HIT] {self.name}/{self.model_name}")
                                return cached
            except Exception as e:
                # Log but don't fail if cache lookup fails
                logger.debug(f"[CACHE] Lookup failed, proceeding without cache: {e}")

        retry_decorator = create_retry_decorator(
            max_retries=self.max_retries,
            retry_logger=logger,
        )

        @retry_decorator
        async def _do_request() -> tuple[str, TokenUsage]:
            try:
                client = self._get_client()

                request_params = {
                    "model": self.model_name,
                    "messages": chat_messages,
                    "temperature": self.temperature,
                }

                if self.max_tokens is not None:
                    request_params["max_tokens"] = self.max_tokens

                # Add provider-specific parameters
                request_params.update(self._get_extra_request_params())

                completion = await client.chat.completions.create(**request_params)
                response_content = completion.choices[0].message.content
                
                # Extract token usage if available
                usage = TokenUsage()
                if completion.usage:
                    usage = TokenUsage(
                        input_tokens=completion.usage.prompt_tokens or 0,
                        output_tokens=completion.usage.completion_tokens or 0,
                    )

                if not response_content:
                    raise EmptyResponseError(
                        f"[{self.model_name}] Received empty response"
                    )

                if self.strip_json_markers and json_schema:
                    response_content = strip_json_block(response_content)

                return response_content, usage

            except OpenAIRateLimitError as e:
                raise RateLimitError(f"[{self.model_name}] Rate limit hit") from e
            except OpenAITimeoutError as e:
                raise TimeoutError(f"[{self.model_name}] Request timed out") from e

        try:
            response, token_usage = await _do_request()
            
            # Report token usage via callback
            if self.on_token_usage:
                self.on_token_usage(self.name, self.model_name, token_usage, True)

            # Cache storage (only on success)
            if self.use_cache and cache_key is not None and response is not None:
                try:
                    db_manager = DatabaseManager.get_default()
                    if db_manager.is_initialized:
                        # Use first message content as prompt preview
                        prompt_preview = ""
                        if chat_messages:
                            first_user_msg = next(
                                (m.get("content", "") for m in chat_messages if m.get("role") == "user"),
                                ""
                            )
                            prompt_preview = first_user_msg[:200] if first_user_msg else ""
                        with db_manager.session_scope() as session:
                            cache_repo = CacheRepository(session)
                            cache_repo.put(
                                cache_key=cache_key,
                                provider_name=self.name,
                                model=self.model_name,
                                prompt_preview=prompt_preview,
                                response=response,
                            )
                        logger.debug(f"[CACHE STORE] {self.name}/{self.model_name}")
                except Exception as e:
                    # Log but don't fail if cache storage fails
                    logger.debug(f"[CACHE] Storage failed: {e}")

            return response
        except RetryError:
            logger.error(f"[{self.model_name}] All retry attempts failed")
            # Report failure via callback
            if self.on_token_usage:
                self.on_token_usage(self.name, self.model_name, TokenUsage(), False)
            return None
        except Exception as e:
            logger.error(f"[{self.model_name}] Unexpected error: {e}")
            # Report failure via callback
            if self.on_token_usage:
                self.on_token_usage(self.name, self.model_name, TokenUsage(), False)
            return None

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        """Generate initial cards for a given question."""
        active_template = prompt_template or prompts.initial

        # If it's a custom pre-formatted prompt (from ingest), it might already contain content
        # We should only format if placeholders exist and we haven't already replaced them
        content = active_template
        if "{question}" in content or "{schema}" in content:
            try:
                content = content.format(
                    question=question,
                    schema=json.dumps(json_schema, indent=2, ensure_ascii=False),
                )
            except KeyError:
                # Fallback to simple replace if format fails due to extra braces in content
                content = content.replace("{question}", question)
                content = content.replace("{schema}", json.dumps(json_schema, indent=2, ensure_ascii=False))

        chat_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates Anki cards in JSON format.",
            },
            {
                "role": "user",
                "content": content,
            },
        ]

        response_content = await self._make_request(chat_messages, json_schema)
        return response_content if response_content else ""

    async def combine_cards(
        self,
        question: str,
        combined_inputs: str,
        json_schema: Dict[str, Any],
        combine_prompt_template: Optional[str] = None,
    ) -> Optional[str]:
        """Combine multiple sets of cards into a single deck.

        Returns raw response string (may not be valid JSON).
        """
        active_template = combine_prompt_template or prompts.combine

        content = active_template
        if "{question}" in content or "{inputs}" in content:
            try:
                content = content.format(
                    question=question,
                    inputs=combined_inputs,
                )
            except KeyError:
                content = content.replace("{question}", question)
                content = content.replace("{inputs}", combined_inputs)

        chat_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates Anki cards in JSON format.",
            },
            {
                "role": "user",
                "content": content,
            },
        ]

        return await self._make_request(chat_messages, json_schema)

    async def format_json(
        self,
        raw_content: str,
        json_schema: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Format raw content into valid JSON matching the schema."""
        chat_messages = [
            {
                "role": "system",
                "content": (
                    "You are a JSON formatting assistant. Your task is to extract and format "
                    "the content into valid JSON matching the provided schema. "
                    "Output ONLY valid JSON, nothing else. No markdown, no explanations."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Format the following content into valid JSON matching this schema:\n\n"
                    f"Schema:\n{json.dumps(json_schema, indent=2, ensure_ascii=False)}\n\n"
                    f"Content to format:\n{raw_content}"
                ),
            },
        ]

        model_name = self.model_name  # Capture for closure

        def log_retry(retry_state):
            logger.warning(
                f"[{model_name}] format_json attempt {retry_state.attempt_number}/{self.json_parse_retries}: "
                f"JSON Decode Error. Retrying..."
            )

        @retry(
            stop=stop_after_attempt(self.json_parse_retries),
            wait=wait_fixed(0.5),
            retry=retry_if_exception_type((json.JSONDecodeError, RetryableError)),
            before_sleep=log_retry,
            reraise=True,
        )
        async def _parse_with_retry() -> Dict[str, Any]:
            response_content = await self._make_request(chat_messages, json_schema)
            if not response_content:
                raise RetryableError("Empty response from format request")
            return json.loads(response_content)

        try:
            return await _parse_with_retry()
        except RetryError:
            logger.error(f"[{self.model_name}] format_json failed after {self.json_parse_retries} attempts.")
            return None
        except json.JSONDecodeError:
            logger.error(f"[{self.model_name}] format_json failed after {self.json_parse_retries} attempts.")
            return None
