"""Model constants and feature flags for LLM providers."""

# Models that support reasoning effort parameter
MODELS_WITH_REASONING_EFFORT = frozenset([
    "gpt-oss-120b",
])

# Default models for each provider (used as fallbacks)
DEFAULT_MODELS = {
    "cerebras": "gpt-oss-120b",
    "g4f": "claude-opus-4-5-20251101-thinking-32k",
    "google_genai": "gemini-3-flash-preview",
    "google_antigravity": "gemini-3-pro-preview",
    "openrouter": "meta-llama/llama-3.1-70b-instruct",
    "nvidia": "meta/llama-3.1-70b-instruct",
    "canopywave": "meta-llama/Llama-3.1-70B-Instruct",
    "baseten": "llama-3.1-70b",
}


def supports_reasoning_effort(model: str) -> bool:
    """Check if a model supports the reasoning_effort parameter."""
    return model in MODELS_WITH_REASONING_EFFORT
