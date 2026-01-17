"""Custom exceptions for LLM2Deck."""


class LLM2DeckError(Exception):
    """Base exception for LLM2Deck."""

    pass


class ProviderError(LLM2DeckError):
    """Base exception for provider errors."""

    def __init__(self, provider_name: str, message: str):
        self.provider_name = provider_name
        super().__init__(f"[{provider_name}] {message}")


class APIKeyError(ProviderError):
    """Raised when API key is missing or invalid."""

    pass


class GenerationError(ProviderError):
    """Raised when card generation fails after all retries."""

    pass


class CombinationError(ProviderError):
    """Raised when card combination fails after all retries."""

    pass


class JSONParseError(ProviderError):
    """Raised when JSON parsing fails after retries."""

    def __init__(self, provider_name: str, raw_content: str):
        self.raw_content = raw_content
        super().__init__(provider_name, "Failed to parse JSON response")


class ConfigurationError(LLM2DeckError):
    """Raised for configuration issues."""

    pass


class SubjectError(ConfigurationError):
    """Raised when subject configuration is invalid."""

    def __init__(self, subject: str, message: str = None):
        self.subject = subject
        msg = message or f"Unknown subject: {subject}"
        super().__init__(msg)


class DatabaseError(LLM2DeckError):
    """Raised for database operation failures."""

    pass
