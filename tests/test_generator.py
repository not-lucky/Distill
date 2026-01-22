"""Tests for CardGenerator in src/generator.py."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.generator import CardGenerator
from src.models import LeetCodeProblem
from src.database import DatabaseManager
from src.repositories import RunRepository

from conftest import (
    MockLLMProvider,
    FailingMockProvider,
    SAMPLE_CARD_RESPONSE,
    SAMPLE_CARD_RESPONSE_DICT,
)


class TestCardGenerator:
    """Tests for CardGenerator class."""

    @pytest.fixture
    def card_repo(self, in_memory_db):
        """Create a CardRepository with an active run."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )
        return run_repo.get_card_repository()

    @pytest.fixture
    def generator_with_mocks(self, card_repo):
        """Create a CardGenerator with mock providers."""
        providers = [
            MockLLMProvider(name="provider1", model="model1"),
            MockLLMProvider(name="provider2", model="model2"),
        ]
        combiner = MockLLMProvider(name="combiner", model="combiner-model")

        return CardGenerator(
            providers=providers,
            combiner=combiner,
            formatter=None,
            repository=card_repo,
            combine_prompt="Test combine prompt",
        )

    def test_init(self, card_repo):
        """Test CardGenerator initialization."""
        providers = [MockLLMProvider()]
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=providers,
            combiner=combiner,
            formatter=None,
            repository=card_repo,
        )

        assert generator.llm_providers == providers
        assert generator.card_combiner == combiner
        assert generator.formatter is None
        assert generator.repository == card_repo
        assert generator.dry_run is False

    def test_init_dry_run(self, card_repo):
        """Test CardGenerator in dry run mode."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
            dry_run=True,
        )

        assert generator.dry_run is True
        assert generator.repository is None

    @pytest.mark.asyncio
    async def test_process_question_success(self, generator_with_mocks):
        """Test successful question processing."""
        result = await generator_with_mocks.process_question(
            question="Binary Search",
            prompt_template="Test prompt",
            model_class=LeetCodeProblem,
            category_index=1,
            category_name="Arrays",
            problem_index=1,
        )

        assert result is not None
        assert "cards" in result
        assert result.get("category_index") == 1
        assert result.get("category_name") == "Arrays"
        assert result.get("problem_index") == 1

    @pytest.mark.asyncio
    async def test_process_question_all_providers_fail(self, card_repo):
        """Test when all providers fail."""
        providers = [
            FailingMockProvider(name="fail1", model="f1"),
            FailingMockProvider(name="fail2", model="f2"),
        ]
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=providers,
            combiner=combiner,
            formatter=None,
            repository=card_repo,
        )

        result = await generator.process_question(
            question="Test Question",
            model_class=LeetCodeProblem,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_process_question_combiner_fails(self, card_repo):
        """Test when combiner fails."""
        providers = [MockLLMProvider(name="p1", model="m1")]
        combiner = MockLLMProvider(
            name="combiner",
            model="c-model",
            fail_combine=True
        )

        generator = CardGenerator(
            providers=providers,
            combiner=combiner,
            formatter=None,
            repository=card_repo,
        )

        result = await generator.process_question(
            question="Test Question",
            model_class=LeetCodeProblem,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_process_question_with_formatter(self, card_repo):
        """Test question processing with a formatter."""
        providers = [MockLLMProvider(name="p1", model="m1")]
        combiner = MockLLMProvider(name="combiner", model="c-model")
        formatter = MockLLMProvider(
            name="formatter",
            model="f-model",
            responses={"format": SAMPLE_CARD_RESPONSE_DICT}
        )

        generator = CardGenerator(
            providers=providers,
            combiner=combiner,
            formatter=formatter,
            repository=card_repo,
        )

        result = await generator.process_question(
            question="Test",
            model_class=LeetCodeProblem,
        )

        assert result is not None
        # Formatter should have been called since combiner != formatter
        assert formatter.format_call_count == 1


class TestPostProcessCards:
    """Tests for _post_process_cards method."""

    @pytest.fixture
    def generator(self):
        """Create a minimal generator for testing."""
        return CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

    def test_strips_spaces_from_tags(self, generator):
        """Test that spaces are stripped from tags."""
        card_data = {
            "cards": [
                {"tags": ["Two Pointers", "Binary Search"]},
                {"tags": ["Sliding Window"]},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert result["cards"][0]["tags"] == ["TwoPointers", "BinarySearch"]
        assert result["cards"][1]["tags"] == ["SlidingWindow"]

    def test_strips_spaces_from_card_type(self, generator):
        """Test that spaces are stripped from card_type."""
        card_data = {
            "cards": [
                {"card_type": "Brute Force Algorithm"},
                {"card_type": "Time Complexity"},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert result["cards"][0]["card_type"] == "BruteForceAlgorithm"
        assert result["cards"][1]["card_type"] == "TimeComplexity"

    def test_adds_category_metadata(self, generator):
        """Test adding category metadata."""
        card_data = {"cards": []}

        result = generator._post_process_cards(
            card_data,
            category_index=2,
            category_name="Two Pointers",
            problem_index=3,
        )

        assert result["category_index"] == 2
        assert result["category_name"] == "Two Pointers"
        assert result["problem_index"] == 3

    def test_no_metadata_when_none(self, generator):
        """Test no metadata added when not provided."""
        card_data = {"cards": []}

        result = generator._post_process_cards(card_data)

        assert "category_index" not in result
        assert "category_name" not in result
        assert "problem_index" not in result


class TestSaveProviderResults:
    """Tests for _save_provider_results method."""

    @pytest.fixture
    def generator_with_repo(self, in_memory_db):
        """Create a generator with repository."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )
        card_repo = run_repo.get_card_repository()

        providers = [
            MockLLMProvider(name="p1", model="m1"),
            MockLLMProvider(name="p2", model="m2"),
        ]

        generator = CardGenerator(
            providers=providers,
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )
        return generator, card_repo

    def test_filters_empty_results(self, generator_with_repo):
        """Test that empty results are filtered out."""
        generator, card_repo = generator_with_repo

        problem_id = card_repo.create_initial_problem(
            question_name="Test"
        )

        provider_results = [
            SAMPLE_CARD_RESPONSE,
            "",  # Empty result
        ]

        valid = generator._save_provider_results(problem_id, provider_results)

        assert len(valid) == 1
        assert valid[0] == SAMPLE_CARD_RESPONSE

    def test_saves_all_valid_results(self, generator_with_repo):
        """Test that all valid results are saved."""
        generator, card_repo = generator_with_repo

        problem_id = card_repo.create_initial_problem(
            question_name="Test"
        )

        provider_results = [
            SAMPLE_CARD_RESPONSE,
            SAMPLE_CARD_RESPONSE,
        ]

        valid = generator._save_provider_results(problem_id, provider_results)

        assert len(valid) == 2

    def test_handles_invalid_json_gracefully(self, generator_with_repo):
        """Test handling of invalid JSON in results."""
        generator, card_repo = generator_with_repo

        problem_id = card_repo.create_initial_problem(
            question_name="Test"
        )

        provider_results = [
            "not valid json",
            SAMPLE_CARD_RESPONSE,
        ]

        valid = generator._save_provider_results(problem_id, provider_results)

        # Both should be saved (invalid JSON is still saved, just without card_count)
        assert len(valid) == 2


class TestIsSameProvider:
    """Tests for _is_same_provider method."""

    @pytest.fixture
    def generator(self):
        """Create a minimal generator."""
        return CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

    def test_same_provider(self, generator):
        """Test comparing identical providers."""
        p1 = MockLLMProvider(name="test", model="model-a")
        p2 = MockLLMProvider(name="test", model="model-a")

        assert generator._is_same_provider(p1, p2) is True

    def test_different_name(self, generator):
        """Test providers with different names."""
        p1 = MockLLMProvider(name="test1", model="model-a")
        p2 = MockLLMProvider(name="test2", model="model-a")

        assert generator._is_same_provider(p1, p2) is False

    def test_different_model(self, generator):
        """Test providers with different models."""
        p1 = MockLLMProvider(name="test", model="model-a")
        p2 = MockLLMProvider(name="test", model="model-b")

        assert generator._is_same_provider(p1, p2) is False


class TestGenerateInitialCards:
    """Tests for _generate_initial_cards method."""

    @pytest.mark.asyncio
    async def test_parallel_generation(self):
        """Test that initial cards are generated in parallel."""
        providers = [
            MockLLMProvider(name="p1", model="m1"),
            MockLLMProvider(name="p2", model="m2"),
            MockLLMProvider(name="p3", model="m3"),
        ]

        generator = CardGenerator(
            providers=providers,
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

        results = await generator._generate_initial_cards(
            question="Test",
            json_schema={},
            prompt_template="Prompt",
        )

        assert len(results) == 3
        # All providers should have been called
        for provider in providers:
            assert provider.initial_call_count == 1


class TestCombineResults:
    """Tests for _combine_results method."""

    @pytest.mark.asyncio
    async def test_combine_success(self):
        """Test successful combination."""
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=[],
            combiner=combiner,
            formatter=None,
            repository=None,
        )

        result = await generator._combine_results(
            question="Test",
            valid_results=["result1", "result2"],
            json_schema={},
        )

        assert result is not None
        assert combiner.combine_call_count == 1

    @pytest.mark.asyncio
    async def test_combine_with_formatter(self):
        """Test combination with formatter."""
        combiner = MockLLMProvider(name="combiner", model="c-model")
        formatter = MockLLMProvider(
            name="formatter",
            model="f-model",
            responses={"format": SAMPLE_CARD_RESPONSE_DICT}
        )

        generator = CardGenerator(
            providers=[],
            combiner=combiner,
            formatter=formatter,
            repository=None,
        )

        result = await generator._combine_results(
            question="Test",
            valid_results=["result1"],
            json_schema={},
        )

        assert result is not None
        assert formatter.format_call_count == 1

    @pytest.mark.asyncio
    async def test_combine_returns_none_on_failure(self):
        """Test that combine returns None when combiner fails."""
        combiner = MockLLMProvider(name="combiner", model="c", fail_combine=True)

        generator = CardGenerator(
            providers=[],
            combiner=combiner,
            formatter=None,
            repository=None,
        )

        result = await generator._combine_results(
            question="Test",
            valid_results=["result1"],
            json_schema={},
        )

        assert result is None
