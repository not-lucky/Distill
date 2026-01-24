"""Cost estimation and tracking service for LLM2Deck.

Provides functionality for:
- Pre-run cost estimation based on provider pricing
- Actual cost calculation from token usage
- Budget enforcement during generation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Token pricing per 1M tokens (input, output) in USD
# Sources: Provider pricing pages as of Jan 2026
TOKEN_PRICING: Dict[str, Tuple[float, float]] = {
    "cerebras": (0.60, 0.60),
    "nvidia": (0.50, 0.50),  # varies by model
    "openrouter": (0.50, 0.50),  # varies by model
    "google_genai": (0.10, 0.40),  # Gemini 2.0 Flash
    "google_antigravity": (0.0, 0.0),  # Local proxy, free
}

# Default token estimates per question per provider (when no historical data)
DEFAULT_INPUT_TOKENS_PER_QUESTION = 2000
DEFAULT_OUTPUT_TOKENS_PER_QUESTION = 1500


@dataclass
class ProviderCostEstimate:
    """Per-provider cost estimate."""

    provider_name: str
    model: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    input_price_per_million: float
    output_price_per_million: float
    estimated_cost_usd: float


@dataclass
class CostEstimate:
    """Estimated cost for a generation run."""

    total_questions: int
    providers: List[ProviderCostEstimate] = field(default_factory=list)
    total_estimated_cost_usd: float = 0.0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    confidence: str = "medium"  # "low", "medium", "high" based on historical data

    def __post_init__(self):
        """Recalculate totals from providers if not set."""
        if self.providers and self.total_estimated_cost_usd == 0.0:
            self.total_estimated_cost_usd = sum(p.estimated_cost_usd for p in self.providers)
            self.estimated_input_tokens = sum(p.estimated_input_tokens for p in self.providers)
            self.estimated_output_tokens = sum(p.estimated_output_tokens for p in self.providers)


@dataclass
class RunCostSummary:
    """Actual cost summary for a completed run."""

    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    providers: Dict[str, Dict[str, float]] = field(default_factory=dict)
    budget_limit_usd: Optional[float] = None
    budget_exceeded: bool = False


class CostEstimator:
    """Estimates and tracks API costs for LLM2Deck generation runs.

    Uses provider pricing tables and token estimates to calculate costs.
    Supports both pre-run estimation and actual cost tracking.
    """

    def __init__(
        self,
        pricing: Optional[Dict[str, Tuple[float, float]]] = None,
        input_tokens_per_question: int = DEFAULT_INPUT_TOKENS_PER_QUESTION,
        output_tokens_per_question: int = DEFAULT_OUTPUT_TOKENS_PER_QUESTION,
    ):
        """Initialize the cost estimator.

        Args:
            pricing: Override pricing table (provider_name -> (input_per_million, output_per_million))
            input_tokens_per_question: Estimated input tokens per question
            output_tokens_per_question: Estimated output tokens per question
        """
        self.pricing = pricing or TOKEN_PRICING.copy()
        self.input_tokens_per_question = input_tokens_per_question
        self.output_tokens_per_question = output_tokens_per_question

    def get_provider_pricing(self, provider_name: str) -> Tuple[float, float]:
        """Get pricing for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Tuple of (input_price_per_million, output_price_per_million)
        """
        return self.pricing.get(provider_name, (0.0, 0.0))

    def calculate_cost(
        self,
        provider_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate actual cost from token usage.

        Args:
            provider_name: Name of the provider
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used

        Returns:
            Cost in USD
        """
        input_price, output_price = self.get_provider_pricing(provider_name)
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        return input_cost + output_cost

    def estimate_provider_cost(
        self,
        provider_name: str,
        model: str,
        question_count: int,
    ) -> ProviderCostEstimate:
        """Estimate cost for a single provider.

        Args:
            provider_name: Name of the provider
            model: Model name
            question_count: Number of questions to process

        Returns:
            ProviderCostEstimate with cost breakdown
        """
        input_tokens = self.input_tokens_per_question * question_count
        output_tokens = self.output_tokens_per_question * question_count
        input_price, output_price = self.get_provider_pricing(provider_name)

        estimated_cost = self.calculate_cost(provider_name, input_tokens, output_tokens)

        return ProviderCostEstimate(
            provider_name=provider_name,
            model=model,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            input_price_per_million=input_price,
            output_price_per_million=output_price,
            estimated_cost_usd=estimated_cost,
        )

    def estimate_run_cost(
        self,
        providers: List[Tuple[str, str]],  # List of (provider_name, model)
        question_count: int,
    ) -> CostEstimate:
        """Estimate total cost for a generation run.

        Args:
            providers: List of (provider_name, model) tuples for all providers
            question_count: Number of questions to process

        Returns:
            CostEstimate with total cost breakdown
        """
        provider_estimates = [
            self.estimate_provider_cost(name, model, question_count)
            for name, model in providers
        ]

        return CostEstimate(
            total_questions=question_count,
            providers=provider_estimates,
            confidence="medium",
        )

    def check_budget(
        self,
        budget_limit_usd: float,
        current_cost_usd: float,
        remaining_questions: int,
        providers: List[Tuple[str, str]],
    ) -> Tuple[bool, float]:
        """Check if continuing would exceed budget.

        Args:
            budget_limit_usd: Maximum allowed budget in USD
            current_cost_usd: Cost already incurred
            remaining_questions: Number of questions left to process
            providers: List of (provider_name, model) tuples

        Returns:
            Tuple of (within_budget, estimated_final_cost)
        """
        remaining_estimate = self.estimate_run_cost(providers, remaining_questions)
        estimated_final_cost = current_cost_usd + remaining_estimate.total_estimated_cost_usd
        within_budget = estimated_final_cost <= budget_limit_usd
        return within_budget, estimated_final_cost

    def format_cost_estimate(self, estimate: CostEstimate) -> str:
        """Format cost estimate for display.

        Args:
            estimate: CostEstimate to format

        Returns:
            Formatted string for terminal display
        """
        lines = [
            f"Cost Estimate ({estimate.confidence} confidence)",
            f"  Questions: {estimate.total_questions}",
            f"  Estimated Tokens: {estimate.estimated_input_tokens:,} in / {estimate.estimated_output_tokens:,} out",
            f"  Estimated Cost: ${estimate.total_estimated_cost_usd:.4f}",
            "",
            "  Per Provider:",
        ]

        for provider in estimate.providers:
            lines.append(
                f"    {provider.provider_name}/{provider.model}: "
                f"${provider.estimated_cost_usd:.4f} "
                f"({provider.estimated_input_tokens:,} in / {provider.estimated_output_tokens:,} out)"
            )

        return "\n".join(lines)
