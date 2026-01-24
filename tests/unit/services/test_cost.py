"""Unit tests for cost estimation service."""

import pytest
from assertpy import assert_that

from src.services.cost import (
    CostEstimator,
    CostEstimate,
    ProviderCostEstimate,
    RunCostSummary,
    TOKEN_PRICING,
    DEFAULT_INPUT_TOKENS_PER_QUESTION,
    DEFAULT_OUTPUT_TOKENS_PER_QUESTION,
)


class TestTokenPricing:
    """Tests for TOKEN_PRICING constant."""

    def test_has_cerebras_pricing(self):
        """Token pricing includes Cerebras."""
        assert_that(TOKEN_PRICING).contains_key("cerebras")
        input_price, output_price = TOKEN_PRICING["cerebras"]
        assert_that(input_price).is_greater_than(0)
        assert_that(output_price).is_greater_than(0)

    def test_has_google_genai_pricing(self):
        """Token pricing includes Google GenAI."""
        assert_that(TOKEN_PRICING).contains_key("google_genai")

    def test_antigravity_is_free(self):
        """Google Antigravity (local proxy) is free."""
        assert_that(TOKEN_PRICING).contains_key("google_antigravity")
        input_price, output_price = TOKEN_PRICING["google_antigravity"]
        assert_that(input_price).is_equal_to(0.0)
        assert_that(output_price).is_equal_to(0.0)


class TestCostEstimatorCalculateCost:
    """Tests for CostEstimator.calculate_cost method."""

    def test_calculates_cost_for_known_provider(self):
        """Calculates correct cost for a known provider."""
        estimator = CostEstimator()
        # Cerebras: $0.60/1M tokens for both input and output
        cost = estimator.calculate_cost("cerebras", 1_000_000, 1_000_000)
        # 1M * 0.60 + 1M * 0.60 = $1.20
        assert_that(cost).is_close_to(1.20, tolerance=0.001)

    def test_calculates_zero_for_unknown_provider(self):
        """Returns zero cost for unknown provider."""
        estimator = CostEstimator()
        cost = estimator.calculate_cost("unknown_provider", 1_000_000, 1_000_000)
        assert_that(cost).is_equal_to(0.0)

    def test_calculates_zero_for_zero_tokens(self):
        """Returns zero cost for zero tokens."""
        estimator = CostEstimator()
        cost = estimator.calculate_cost("cerebras", 0, 0)
        assert_that(cost).is_equal_to(0.0)

    def test_calculates_cost_with_different_rates(self):
        """Calculates cost correctly when input/output rates differ."""
        estimator = CostEstimator()
        # Google GenAI: $0.10/1M input, $0.40/1M output
        cost = estimator.calculate_cost("google_genai", 1_000_000, 1_000_000)
        # 1M * 0.10 + 1M * 0.40 = $0.50
        assert_that(cost).is_close_to(0.50, tolerance=0.001)

    def test_uses_custom_pricing_table(self):
        """Uses custom pricing table when provided."""
        custom_pricing = {"my_provider": (1.0, 2.0)}
        estimator = CostEstimator(pricing=custom_pricing)
        cost = estimator.calculate_cost("my_provider", 1_000_000, 500_000)
        # 1M * 1.0 + 500K * 2.0 = $2.00
        assert_that(cost).is_close_to(2.0, tolerance=0.001)


class TestCostEstimatorEstimateProviderCost:
    """Tests for CostEstimator.estimate_provider_cost method."""

    def test_estimates_cost_for_single_provider(self):
        """Estimates cost for a single provider and question count."""
        estimator = CostEstimator()
        estimate = estimator.estimate_provider_cost("cerebras", "gpt-oss-120b", 10)

        assert_that(estimate.provider_name).is_equal_to("cerebras")
        assert_that(estimate.model).is_equal_to("gpt-oss-120b")
        assert_that(estimate.estimated_input_tokens).is_equal_to(
            DEFAULT_INPUT_TOKENS_PER_QUESTION * 10
        )
        assert_that(estimate.estimated_output_tokens).is_equal_to(
            DEFAULT_OUTPUT_TOKENS_PER_QUESTION * 10
        )
        assert_that(estimate.estimated_cost_usd).is_greater_than(0)

    def test_uses_custom_token_estimates(self):
        """Uses custom token estimates when provided."""
        estimator = CostEstimator(
            input_tokens_per_question=1000,
            output_tokens_per_question=500,
        )
        estimate = estimator.estimate_provider_cost("cerebras", "model", 5)

        assert_that(estimate.estimated_input_tokens).is_equal_to(5000)
        assert_that(estimate.estimated_output_tokens).is_equal_to(2500)


class TestCostEstimatorEstimateRunCost:
    """Tests for CostEstimator.estimate_run_cost method."""

    def test_estimates_cost_for_multiple_providers(self):
        """Estimates total cost across multiple providers."""
        estimator = CostEstimator()
        providers = [
            ("cerebras", "gpt-oss-120b"),
            ("google_genai", "gemini-2.0"),
        ]
        estimate = estimator.estimate_run_cost(providers, 10)

        assert_that(estimate.total_questions).is_equal_to(10)
        assert_that(estimate.providers).is_length(2)
        assert_that(estimate.total_estimated_cost_usd).is_greater_than(0)
        assert_that(estimate.estimated_input_tokens).is_greater_than(0)
        assert_that(estimate.estimated_output_tokens).is_greater_than(0)
        assert_that(estimate.confidence).is_equal_to("medium")

    def test_returns_zero_for_empty_providers(self):
        """Returns zero cost for empty provider list."""
        estimator = CostEstimator()
        estimate = estimator.estimate_run_cost([], 10)

        assert_that(estimate.total_questions).is_equal_to(10)
        assert_that(estimate.providers).is_empty()
        assert_that(estimate.total_estimated_cost_usd).is_equal_to(0.0)

    def test_returns_zero_for_zero_questions(self):
        """Returns zero cost for zero questions."""
        estimator = CostEstimator()
        estimate = estimator.estimate_run_cost([("cerebras", "model")], 0)

        assert_that(estimate.total_questions).is_equal_to(0)
        assert_that(estimate.total_estimated_cost_usd).is_equal_to(0.0)


class TestCostEstimatorCheckBudget:
    """Tests for CostEstimator.check_budget method."""

    def test_returns_true_when_within_budget(self):
        """Returns True when estimated cost is within budget."""
        estimator = CostEstimator()
        providers = [("google_antigravity", "gemini-3")]  # Free provider
        within_budget, estimated_final = estimator.check_budget(
            budget_limit_usd=10.0,
            current_cost_usd=0.0,
            remaining_questions=100,
            providers=providers,
        )
        assert_that(within_budget).is_true()
        assert_that(estimated_final).is_equal_to(0.0)

    def test_returns_false_when_exceeds_budget(self):
        """Returns False when estimated cost exceeds budget."""
        estimator = CostEstimator(
            input_tokens_per_question=100_000,  # Large tokens
            output_tokens_per_question=100_000,
        )
        providers = [("cerebras", "model")]
        within_budget, estimated_final = estimator.check_budget(
            budget_limit_usd=0.01,  # Very small budget
            current_cost_usd=0.0,
            remaining_questions=100,
            providers=providers,
        )
        assert_that(within_budget).is_false()
        assert_that(estimated_final).is_greater_than(0.01)

    def test_includes_current_cost_in_calculation(self):
        """Includes current cost in budget calculation."""
        estimator = CostEstimator()
        providers = [("google_antigravity", "model")]  # Free
        within_budget, estimated_final = estimator.check_budget(
            budget_limit_usd=1.0,
            current_cost_usd=0.5,
            remaining_questions=10,
            providers=providers,
        )
        assert_that(within_budget).is_true()
        assert_that(estimated_final).is_equal_to(0.5)  # Only current cost


class TestCostEstimatorGetProviderPricing:
    """Tests for CostEstimator.get_provider_pricing method."""

    def test_returns_pricing_for_known_provider(self):
        """Returns correct pricing tuple for known provider."""
        estimator = CostEstimator()
        input_price, output_price = estimator.get_provider_pricing("cerebras")
        assert_that(input_price).is_equal_to(0.60)
        assert_that(output_price).is_equal_to(0.60)

    def test_returns_zero_for_unknown_provider(self):
        """Returns (0, 0) for unknown provider."""
        estimator = CostEstimator()
        input_price, output_price = estimator.get_provider_pricing("unknown")
        assert_that(input_price).is_equal_to(0.0)
        assert_that(output_price).is_equal_to(0.0)


class TestCostEstimatorFormatCostEstimate:
    """Tests for CostEstimator.format_cost_estimate method."""

    def test_formats_estimate_as_string(self):
        """Formats cost estimate as human-readable string."""
        estimator = CostEstimator()
        estimate = estimator.estimate_run_cost(
            [("cerebras", "gpt-oss-120b")],
            question_count=10,
        )
        formatted = estimator.format_cost_estimate(estimate)

        assert_that(formatted).contains("Cost Estimate")
        assert_that(formatted).contains("Questions: 10")
        assert_that(formatted).contains("cerebras")
        assert_that(formatted).contains("$")


class TestCostEstimateDataclass:
    """Tests for CostEstimate dataclass."""

    def test_calculates_totals_from_providers(self):
        """Calculates total cost from provider estimates."""
        providers = [
            ProviderCostEstimate(
                provider_name="p1",
                model="m1",
                estimated_input_tokens=1000,
                estimated_output_tokens=500,
                input_price_per_million=0.5,
                output_price_per_million=0.5,
                estimated_cost_usd=0.10,
            ),
            ProviderCostEstimate(
                provider_name="p2",
                model="m2",
                estimated_input_tokens=2000,
                estimated_output_tokens=1000,
                input_price_per_million=1.0,
                output_price_per_million=1.0,
                estimated_cost_usd=0.20,
            ),
        ]
        estimate = CostEstimate(total_questions=5, providers=providers)

        assert_that(estimate.total_estimated_cost_usd).is_close_to(0.30, tolerance=0.001)
        assert_that(estimate.estimated_input_tokens).is_equal_to(3000)
        assert_that(estimate.estimated_output_tokens).is_equal_to(1500)

    def test_uses_explicit_totals_when_provided(self):
        """Uses explicit totals when provided instead of calculating."""
        estimate = CostEstimate(
            total_questions=5,
            providers=[],
            total_estimated_cost_usd=1.50,
            estimated_input_tokens=10000,
            estimated_output_tokens=5000,
        )

        assert_that(estimate.total_estimated_cost_usd).is_equal_to(1.50)
        assert_that(estimate.estimated_input_tokens).is_equal_to(10000)


class TestRunCostSummaryDataclass:
    """Tests for RunCostSummary dataclass."""

    def test_default_values(self):
        """RunCostSummary has correct defaults."""
        summary = RunCostSummary(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cost_usd=0.05,
        )

        assert_that(summary.budget_limit_usd).is_none()
        assert_that(summary.budget_exceeded).is_false()
        assert_that(summary.providers).is_empty()

    def test_with_budget_exceeded(self):
        """RunCostSummary tracks budget exceeded."""
        summary = RunCostSummary(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cost_usd=2.0,
            budget_limit_usd=1.0,
            budget_exceeded=True,
        )

        assert_that(summary.budget_exceeded).is_true()
        assert_that(summary.budget_limit_usd).is_equal_to(1.0)
