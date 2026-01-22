"""Comprehensive tests for custom exceptions in src/exceptions.py."""

import pytest

from assertpy import assert_that

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
        """
        Given the LLM2DeckError class
        When checking inheritance
        Then it is a subclass of Exception
        """
        assert_that(issubclass(LLM2DeckError, Exception)).is_true()

    def test_can_be_raised(self):
        """
        Given a LLM2DeckError
        When raised
        Then it can be caught with pytest.raises
        """
        with pytest.raises(LLM2DeckError):
            raise LLM2DeckError("Test error")

    def test_message_preserved(self):
        """
        Given a custom message
        When LLM2DeckError is created
        Then message is preserved in str representation
        """
        error = LLM2DeckError("Custom message")
        assert_that(str(error)).is_equal_to("Custom message")

    def test_can_be_caught_as_exception(self):
        """
        Given a LLM2DeckError
        When caught as Exception
        Then it is an instance of LLM2DeckError
        """
        try:
            raise LLM2DeckError("Test")
        except Exception as e:
            assert_that(e).is_instance_of(LLM2DeckError)


class TestProviderError:
    """Tests for ProviderError exception."""

    def test_is_llm2deck_error(self):
        """
        Given the ProviderError class
        When checking inheritance
        Then it is a subclass of LLM2DeckError
        """
        assert_that(issubclass(ProviderError, LLM2DeckError)).is_true()

    def test_stores_provider_name(self):
        """
        Given a provider name
        When ProviderError is created
        Then provider_name is stored correctly
        """
        error = ProviderError("nvidia", "API timeout")
        assert_that(error.provider_name).is_equal_to("nvidia")

    def test_message_format(self):
        """
        Given a provider name and message
        When ProviderError is created
        Then message includes provider name in brackets
        """
        error = ProviderError("openrouter", "Connection failed")
        assert_that(str(error)).is_equal_to("[openrouter] Connection failed")

    def test_can_be_raised_and_caught(self):
        """
        Given a ProviderError
        When raised and caught
        Then provider_name is accessible
        """
        with pytest.raises(ProviderError) as exc_info:
            raise ProviderError("test_provider", "Test message")
        assert_that(exc_info.value.provider_name).is_equal_to("test_provider")

    def test_can_be_caught_as_llm2deck_error(self):
        """
        Given a ProviderError
        When caught as LLM2DeckError
        Then it is still a ProviderError instance
        """
        try:
            raise ProviderError("test", "message")
        except LLM2DeckError as e:
            assert_that(e).is_instance_of(ProviderError)


class TestAPIKeyError:
    """Tests for APIKeyError exception."""

    def test_is_provider_error(self):
        """
        Given the APIKeyError class
        When checking inheritance
        Then it is a subclass of ProviderError
        """
        assert_that(issubclass(APIKeyError, ProviderError)).is_true()

    def test_inherits_provider_name(self):
        """
        Given a provider name
        When APIKeyError is created
        Then provider_name is inherited from ProviderError
        """
        error = APIKeyError("cerebras", "Missing API key")
        assert_that(error.provider_name).is_equal_to("cerebras")

    def test_message_format(self):
        """
        Given a provider name and message
        When APIKeyError is created
        Then message includes provider in brackets
        """
        error = APIKeyError("nvidia", "Invalid key format")
        assert_that(str(error)).contains("[nvidia]")
        assert_that(str(error)).contains("Invalid key format")


class TestGenerationError:
    """Tests for GenerationError exception."""

    def test_is_provider_error(self):
        """
        Given the GenerationError class
        When checking inheritance
        Then it is a subclass of ProviderError
        """
        assert_that(issubclass(GenerationError, ProviderError)).is_true()

    def test_can_be_raised(self):
        """
        Given a GenerationError
        When raised
        Then it can be caught with pytest.raises
        """
        with pytest.raises(GenerationError):
            raise GenerationError("nvidia", "Card generation failed")

    def test_stores_provider_name(self):
        """
        Given a provider name
        When GenerationError is created
        Then provider_name is stored correctly
        """
        error = GenerationError("openrouter", "Timeout after 3 retries")
        assert_that(error.provider_name).is_equal_to("openrouter")


class TestCombinationError:
    """Tests for CombinationError exception."""

    def test_is_provider_error(self):
        """
        Given the CombinationError class
        When checking inheritance
        Then it is a subclass of ProviderError
        """
        assert_that(issubclass(CombinationError, ProviderError)).is_true()

    def test_can_be_raised(self):
        """
        Given a CombinationError
        When raised
        Then it can be caught with pytest.raises
        """
        with pytest.raises(CombinationError):
            raise CombinationError("test", "Combination failed")

    def test_message_format(self):
        """
        Given a provider name and message
        When CombinationError is created
        Then message includes provider in brackets
        """
        error = CombinationError("combiner", "No valid cards to combine")
        assert_that(str(error)).contains("[combiner]")


class TestJSONParseError:
    """Tests for JSONParseError exception."""

    def test_is_provider_error(self):
        """
        Given the JSONParseError class
        When checking inheritance
        Then it is a subclass of ProviderError
        """
        assert_that(issubclass(JSONParseError, ProviderError)).is_true()

    def test_stores_raw_content(self):
        """
        Given raw JSON content
        When JSONParseError is created
        Then raw_content is stored correctly
        """
        raw = '{"incomplete": true'
        error = JSONParseError("nvidia", raw)
        assert_that(error.raw_content).is_equal_to(raw)

    def test_stores_provider_name(self):
        """
        Given a provider name
        When JSONParseError is created
        Then provider_name is stored correctly
        """
        error = JSONParseError("openai", "invalid json")
        assert_that(error.provider_name).is_equal_to("openai")

    def test_message_includes_parse_error(self):
        """
        Given invalid JSON content
        When JSONParseError is created
        Then message indicates parsing issue
        """
        error = JSONParseError("test", "{bad json}")
        message = str(error).lower()
        assert_that(message.count("parse") > 0 or "json" in str(error)).is_true()

    def test_can_access_raw_content(self):
        """
        Given a JSONParseError with raw content
        When caught
        Then raw content is accessible
        """
        raw_content = "```json\n{invalid}\n```"
        try:
            raise JSONParseError("provider", raw_content)
        except JSONParseError as e:
            assert_that(e.raw_content).is_equal_to(raw_content)


class TestAllProvidersFailedError:
    """Tests for AllProvidersFailedError exception."""

    def test_is_llm2deck_error(self):
        """
        Given the AllProvidersFailedError class
        When checking inheritance
        Then it is a subclass of LLM2DeckError
        """
        assert_that(issubclass(AllProvidersFailedError, LLM2DeckError)).is_true()

    def test_stores_question(self):
        """
        Given a question
        When AllProvidersFailedError is created
        Then question is stored correctly
        """
        error = AllProvidersFailedError("Two Sum")
        assert_that(error.question).is_equal_to("Two Sum")

    def test_message_includes_question(self):
        """
        Given a question
        When AllProvidersFailedError is created
        Then message includes the question
        """
        error = AllProvidersFailedError("Binary Search")
        assert_that(str(error)).contains("Binary Search")

    def test_message_format(self):
        """
        Given a question
        When AllProvidersFailedError is created
        Then message indicates all providers failed
        """
        error = AllProvidersFailedError("Test Question")
        assert_that(str(error)).contains("All providers failed")

    def test_can_be_caught_as_llm2deck_error(self):
        """
        Given an AllProvidersFailedError
        When caught as LLM2DeckError
        Then it is still an AllProvidersFailedError instance
        """
        try:
            raise AllProvidersFailedError("Question")
        except LLM2DeckError as e:
            assert_that(e).is_instance_of(AllProvidersFailedError)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_is_llm2deck_error(self):
        """
        Given the ConfigurationError class
        When checking inheritance
        Then it is a subclass of LLM2DeckError
        """
        assert_that(issubclass(ConfigurationError, LLM2DeckError)).is_true()

    def test_can_be_raised_with_message(self):
        """
        Given a message
        When ConfigurationError is raised and caught
        Then message is preserved
        """
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Missing config.yaml")
        assert_that(str(exc_info.value)).contains("Missing config.yaml")


class TestSubjectError:
    """Tests for SubjectError exception."""

    def test_is_configuration_error(self):
        """
        Given the SubjectError class
        When checking inheritance
        Then it is a subclass of ConfigurationError
        """
        assert_that(issubclass(SubjectError, ConfigurationError)).is_true()

    def test_stores_subject(self):
        """
        Given a subject name
        When SubjectError is created
        Then subject is stored correctly
        """
        error = SubjectError("biology")
        assert_that(error.subject).is_equal_to("biology")

    def test_default_message(self):
        """
        Given a subject name
        When SubjectError is created without custom message
        Then default message includes subject
        """
        error = SubjectError("chemistry")
        assert_that(str(error)).contains("Unknown subject: chemistry")

    def test_custom_message(self):
        """
        Given a subject and custom message
        When SubjectError is created
        Then custom message is used
        """
        error = SubjectError("physics", "No questions file found")
        assert_that(str(error)).contains("No questions file found")

    def test_subject_accessible_after_catch(self):
        """
        Given a SubjectError
        When caught
        Then subject is accessible
        """
        try:
            raise SubjectError("unknown")
        except SubjectError as e:
            assert_that(e.subject).is_equal_to("unknown")


class TestDatabaseError:
    """Tests for DatabaseError exception."""

    def test_is_llm2deck_error(self):
        """
        Given the DatabaseError class
        When checking inheritance
        Then it is a subclass of LLM2DeckError
        """
        assert_that(issubclass(DatabaseError, LLM2DeckError)).is_true()

    def test_can_be_raised(self):
        """
        Given a DatabaseError
        When raised
        Then it can be caught with pytest.raises
        """
        with pytest.raises(DatabaseError):
            raise DatabaseError("Connection failed")


class TestInitializationError:
    """Tests for InitializationError exception."""

    def test_is_llm2deck_error(self):
        """
        Given the InitializationError class
        When checking inheritance
        Then it is a subclass of LLM2DeckError
        """
        assert_that(issubclass(InitializationError, LLM2DeckError)).is_true()

    def test_can_be_raised(self):
        """
        Given an InitializationError
        When raised
        Then it can be caught with pytest.raises
        """
        with pytest.raises(InitializationError):
            raise InitializationError("Failed to initialize providers")


class TestExceptionHierarchy:
    """Tests for exception hierarchy and inheritance."""

    def test_all_exceptions_inherit_from_llm2deck_error(self):
        """
        Given all custom exception classes
        When checking inheritance
        Then all inherit from LLM2DeckError
        """
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
            assert_that(issubclass(exc_class, LLM2DeckError)).described_as(
                f"{exc_class.__name__} should inherit from LLM2DeckError"
            ).is_true()

    def test_provider_errors_inherit_from_provider_error(self):
        """
        Given provider-related exception classes
        When checking inheritance
        Then all inherit from ProviderError
        """
        provider_exceptions = [
            APIKeyError,
            GenerationError,
            CombinationError,
            JSONParseError,
        ]
        for exc_class in provider_exceptions:
            assert_that(issubclass(exc_class, ProviderError)).described_as(
                f"{exc_class.__name__} should inherit from ProviderError"
            ).is_true()

    def test_subject_error_inherits_from_configuration_error(self):
        """
        Given the SubjectError class
        When checking inheritance
        Then it inherits from ConfigurationError
        """
        assert_that(issubclass(SubjectError, ConfigurationError)).is_true()

    def test_catch_all_with_llm2deck_error(self):
        """
        Given various custom exceptions
        When caught with LLM2DeckError
        Then all are caught successfully
        """
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
        """
        Given a SubjectError with attributes
        When pickled and unpickled
        Then attributes are preserved
        """
        import pickle
        error = SubjectError("physics", "custom message")
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        assert_that(unpickled.subject).is_equal_to("physics")

    def test_all_providers_failed_is_picklable(self):
        """
        Given an AllProvidersFailedError with question
        When pickled and unpickled
        Then question is preserved
        """
        import pickle
        error = AllProvidersFailedError("Two Sum")
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        assert_that(unpickled.question).is_equal_to("Two Sum")

    def test_base_error_is_picklable(self):
        """
        Given a LLM2DeckError with message
        When pickled and unpickled
        Then message is preserved
        """
        import pickle
        error = LLM2DeckError("Test message")
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        assert_that(str(unpickled)).is_equal_to("Test message")

    def test_configuration_error_is_picklable(self):
        """
        Given a ConfigurationError with message
        When pickled and unpickled
        Then message is preserved
        """
        import pickle
        error = ConfigurationError("Config issue")
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        assert_that(str(unpickled)).contains("Config issue")
