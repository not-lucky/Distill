"""Model constants and feature flags for LLM providers."""

# Models that support reasoning effort parameter
MODELS_WITH_REASONING_EFFORT = frozenset([
    "gpt-oss-120b",
])



def supports_reasoning_effort(model: str) -> bool:
    """Check if a model supports the reasoning_effort parameter."""
    return model in MODELS_WITH_REASONING_EFFORT
