"""Comprehensive tests for custom exceptions in src/exceptions.py."""

import pytest

from src.exceptions import (
    LLM2DeckError,
    ProviderError,
    APIKeyError,
    GenerationError,
    CombinationError,
    JSONParseError,
    AllProvidersFailedError,
    ConfigurationError,
    SubjectError,
    DatabaseError,
    InitializationError,
)


class TestLLM2DeckError:
    """Tests for base LLM2DeckError exception."""

    def test_is_exception(self):
        """Test that LLM2DeckError is an Exception."""
        assert issubclass(LLM2DeckError, Exception)

    def test_can_be_raised(self):
        """Test that LLM2DeckError can be raised."""
        with pytest.raises(LLM2DeckError):
            raise LLM2DeckError("Test error")

    def test_message_preserved(self):
        """Test that error message is preserved."""
        error = LLM2DeckError("Custom message")
        assert str(error) == "Custom message"

    def test_can_be_caught_as_exception(self):
        """Test that LLM2DeckError can be caught as Exception."""
        try:
            raise LLM2DeckError("Test")
        except Exception as e:
            assert isinstance(e, LLM2DeckError)


class TestProviderError:
    """Tests for ProviderError exception."""

    def test_is_llm2deck_error(self):
        """Test that ProviderError is a LLM2DeckError."""
        assert issubclass(ProviderError, LLM2DeckError)

    def test_stores_provider_name(self):
        """Test that provider_name is stored."""
        error = ProviderError("nvidia", "API timeout")
        assert error.provider_name == "nvidia"

    def test_message_format(self):
        """Test that message includes provider name."""
        error = ProviderError("openrouter", "Connection failed")
        assert str(error) == "[openrouter] Connection failed"

    def test_can_be_raised_and_caught(self):
        """Test raising and catching ProviderError."""
        with pytest.raises(ProviderError) as exc_info:
            raise ProviderError("test_provider", "Test message")
        assert exc_info.value.provider_name == "test_provider"

    def test_can_be_caught_as_llm2deck_error(self):
        """Test that ProviderError can be caught as LLM2DeckError."""
        try:
            raise ProviderError("test", "message")
        except LLM2DeckError as e:
            assert isinstance(e, ProviderError)


class TestAPIKeyError:
    """Tests for APIKeyError exception."""

    def test_is_provider_error(self):
        """Test that APIKeyError is a ProviderError."""
        assert issubclass(APIKeyError, ProviderError)

    def test_inherits_provider_name(self):
        """Test that provider_name is inherited."""
        error = APIKeyError("cerebras", "Missing API key")
        assert error.provider_name == "cerebras"

    def test_message_format(self):
        """Test message format."""
        error = APIKeyError("nvidia", "Invalid key format")
        assert "[nvidia]" in str(error)
        assert "Invalid key format" in str(error)


class TestGenerationError:
    """Tests for GenerationError exception."""

    def test_is_provider_error(self):
        """Test that GenerationError is a ProviderError."""
        assert issubclass(GenerationError, ProviderError)

    def test_can_be_raised(self):
        """Test that GenerationError can be raised."""
        with pytest.raises(GenerationError):
            raise GenerationError("nvidia", "Card generation failed")

    def test_stores_provider_name(self):
        """Test that provider_name is stored."""
        error = GenerationError("openrouter", "Timeout after 3 retries")
        assert error.provider_name == "openrouter"


class TestCombinationError:
    """Tests for CombinationError exception."""

    def test_is_provider_error(self):
        """Test that CombinationError is a ProviderError."""
        assert issubclass(CombinationError, ProviderError)

    def test_can_be_raised(self):
        """Test that CombinationError can be raised."""
        with pytest.raises(CombinationError):
            raise CombinationError("test", "Combination failed")

    def test_message_format(self):
        """Test message format."""
        error = CombinationError("combiner", "No valid cards to combine")
        assert "[combiner]" in str(error)


class TestJSONParseError:
    """Tests for JSONParseError exception."""

    def test_is_provider_error(self):
        """Test that JSONParseError is a ProviderError."""
        assert issubclass(JSONParseError, ProviderError)

    def test_stores_raw_content(self):
        """Test that raw_content is stored."""
        raw = '{"incomplete": true'
        error = JSONParseError("nvidia", raw)
        assert error.raw_content == raw

    def test_stores_provider_name(self):
        """Test that provider_name is stored."""
        error = JSONParseError("openai", "invalid json")
        assert error.provider_name == "openai"

    def test_message_includes_parse_error(self):
        """Test that message includes parse error indicator."""
        error = JSONParseError("test", "{bad json}")
        assert "parse" in str(error).lower() or "JSON" in str(error)

    def test_can_access_raw_content(self):
        """Test that raw content can be accessed after catching."""
        raw_content = "```json\n{invalid}\n```"
        try:
            raise JSONParseError("provider", raw_content)
        except JSONParseError as e:
            assert e.raw_content == raw_content


class TestAllProvidersFailedError:
    """Tests for AllProvidersFailedError exception."""

    def test_is_llm2deck_error(self):
        """Test that AllProvidersFailedError is a LLM2DeckError."""
        assert issubclass(AllProvidersFailedError, LLM2DeckError)

    def test_stores_question(self):
        """Test that question is stored."""
        error = AllProvidersFailedError("Two Sum")
        assert error.question == "Two Sum"

    def test_message_includes_question(self):
        """Test that message includes the question."""
        error = AllProvidersFailedError("Binary Search")
        assert "Binary Search" in str(error)

    def test_message_format(self):
        """Test message format."""
        error = AllProvidersFailedError("Test Question")
        assert "All providers failed" in str(error)

    def test_can_be_caught_as_llm2deck_error(self):
        """Test catching as LLM2DeckError."""
        try:
            raise AllProvidersFailedError("Question")
        except LLM2DeckError as e:
            assert isinstance(e, AllProvidersFailedError)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_is_llm2deck_error(self):
        """Test that ConfigurationError is a LLM2DeckError."""
        assert issubclass(ConfigurationError, LLM2DeckError)

    def test_can_be_raised_with_message(self):
        """Test raising with message."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Missing config.yaml")
        assert "Missing config.yaml" in str(exc_info.value)


class TestSubjectError:
    """Tests for SubjectError exception."""

    def test_is_configuration_error(self):
        """Test that SubjectError is a ConfigurationError."""
        assert issubclass(SubjectError, ConfigurationError)

    def test_stores_subject(self):
        """Test that subject is stored."""
        error = SubjectError("biology")
        assert error.subject == "biology"

    def test_default_message(self):
        """Test default message includes subject."""
        error = SubjectError("chemistry")
        assert "Unknown subject: chemistry" in str(error)

    def test_custom_message(self):
        """Test custom message."""
        error = SubjectError("physics", "No questions file found")
        assert "No questions file found" in str(error)

    def test_subject_accessible_after_catch(self):
        """Test that subject is accessible after catching."""
        try:
            raise SubjectError("unknown")
        except SubjectError as e:
            assert e.subject == "unknown"


class TestDatabaseError:
    """Tests for DatabaseError exception."""

    def test_is_llm2deck_error(self):
        """Test that DatabaseError is a LLM2DeckError."""
        assert issubclass(DatabaseError, LLM2DeckError)

    def test_can_be_raised(self):
        """Test that DatabaseError can be raised."""
        with pytest.raises(DatabaseError):
            raise DatabaseError("Connection failed")


class TestInitializationError:
    """Tests for InitializationError exception."""

    def test_is_llm2deck_error(self):
        """Test that InitializationError is a LLM2DeckError."""
        assert issubclass(InitializationError, LLM2DeckError)

    def test_can_be_raised(self):
        """Test that InitializationError can be raised."""
        with pytest.raises(InitializationError):
            raise InitializationError("Failed to initialize providers")


class TestExceptionHierarchy:
    """Tests for exception hierarchy and inheritance."""

    def test_all_exceptions_inherit_from_llm2deck_error(self):
        """Test that all exceptions inherit from LLM2DeckError."""
        exceptions = [
            ProviderError,
            APIKeyError,
            GenerationError,
            CombinationError,
            JSONParseError,
            AllProvidersFailedError,
            ConfigurationError,
            SubjectError,
            DatabaseError,
            InitializationError,
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, LLM2DeckError), f"{exc_class.__name__} should inherit from LLM2DeckError"

    def test_provider_errors_inherit_from_provider_error(self):
        """Test that provider-related errors inherit from ProviderError."""
        provider_exceptions = [
            APIKeyError,
            GenerationError,
            CombinationError,
            JSONParseError,
        ]
        for exc_class in provider_exceptions:
            assert issubclass(exc_class, ProviderError), f"{exc_class.__name__} should inherit from ProviderError"

    def test_subject_error_inherits_from_configuration_error(self):
        """Test that SubjectError inherits from ConfigurationError."""
        assert issubclass(SubjectError, ConfigurationError)

    def test_catch_all_with_llm2deck_error(self):
        """Test catching all exceptions with LLM2DeckError."""
        exceptions_to_test = [
            ProviderError("test", "msg"),
            APIKeyError("test", "msg"),
            GenerationError("test", "msg"),
            CombinationError("test", "msg"),
            JSONParseError("test", "raw"),
            AllProvidersFailedError("question"),
            ConfigurationError("msg"),
            SubjectError("subject"),
            DatabaseError("msg"),
            InitializationError("msg"),
        ]

        for exc in exceptions_to_test:
            try:
                raise exc
            except LLM2DeckError:
                pass  # Should catch all
            except Exception:
                pytest.fail(f"{type(exc).__name__} should be caught by LLM2DeckError")


class TestExceptionPickling:
    """Tests for exception pickling/serialization."""

    def test_subject_error_is_picklable(self):
        """Test that SubjectError can be pickled."""
        import pickle
        error = SubjectError("physics", "custom message")
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        assert unpickled.subject == "physics"

    def test_all_providers_failed_is_picklable(self):
        """Test that AllProvidersFailedError can be pickled."""
        import pickle
        error = AllProvidersFailedError("Two Sum")
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        assert unpickled.question == "Two Sum"

    def test_base_error_is_picklable(self):
        """Test that LLM2DeckError can be pickled."""
        import pickle
        error = LLM2DeckError("Test message")
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        assert str(unpickled) == "Test message"

    def test_configuration_error_is_picklable(self):
        """Test that ConfigurationError can be pickled."""
        import pickle
        error = ConfigurationError("Config issue")
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        assert "Config issue" in str(unpickled)
