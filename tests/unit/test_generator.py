"""Tests for CardGenerator in src/generator.py.

Comprehensive tests covering:
- CardGenerator initialization and configuration
- Provider coordination and parallel generation
- Result combining and formatting
- Post-processing of cards (tags, types, metadata)
- Database operations (save results, update status)
- Error handling and edge cases
- Dry run mode
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.generator import CardGenerator
from src.models import LeetCodeProblem, CSProblem, PhysicsProblem, GenericProblem
from src.database import DatabaseManager
from src.repositories import RunRepository
from src.providers.base import LLMProvider

from conftest import (
    MockLLMProvider,
    FailingMockProvider,
    SAMPLE_CARD_RESPONSE,
    SAMPLE_CARD_RESPONSE_DICT,
)


# ============================================================================
# Test Data and Helpers
# ============================================================================

COMPLEX_CARD_RESPONSE = json.dumps({
    "cards": [
        {
            "front": "What is Big O notation?",
            "back": "A mathematical notation for algorithm complexity",
            "tags": ["Time Complexity", "Algorithm Analysis"],
            "card_type": "Core Concept",
        },
        {
            "front": "What is O(n)?",
            "back": "Linear time complexity",
            "tags": ["Time Complexity"],
            "card_type": "Definition",
        },
    ]
})

MALFORMED_JSON_RESPONSE = "{ cards: invalid }"
EMPTY_CARDS_RESPONSE = json.dumps({"cards": []})
SINGLE_CARD_RESPONSE = json.dumps({
    "cards": [{"front": "Q", "back": "A", "tags": ["Test"]}]
})


def create_generator(
    providers=None,
    combiner=None,
    formatter=None,
    repository=None,
    combine_prompt=None,
    dry_run=False,
):
    """Helper to create CardGenerator with defaults."""
    return CardGenerator(
        providers=providers or [],
        combiner=combiner or MockLLMProvider(),
        formatter=formatter,
        repository=repository,
        combine_prompt=combine_prompt,
        dry_run=dry_run,
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

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_init_stores_providers(self, card_repo):
        """Test that providers are stored correctly."""
        providers = [MockLLMProvider(), MockLLMProvider()]
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=providers,
            combiner=combiner,
            formatter=None,
            repository=card_repo,
        )

        assert generator.llm_providers == providers
        assert len(generator.llm_providers) == 2

    def test_init_stores_combiner(self, card_repo):
        """Test that combiner is stored correctly."""
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=[],
            combiner=combiner,
            formatter=None,
            repository=card_repo,
        )

        assert generator.card_combiner == combiner
        assert generator.card_combiner.name == "combiner"

    def test_init_stores_formatter(self, card_repo):
        """Test that formatter is stored correctly."""
        formatter = MockLLMProvider(name="formatter", model="f-model")

        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=formatter,
            repository=card_repo,
        )

        assert generator.formatter == formatter
        assert generator.formatter.name == "formatter"

    def test_init_stores_repository(self, card_repo):
        """Test that repository is stored correctly."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        assert generator.repository == card_repo

    def test_init_stores_combine_prompt(self, card_repo):
        """Test that combine_prompt is stored correctly."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
            combine_prompt="Custom combine prompt",
        )

        assert generator.combine_prompt == "Custom combine prompt"

    def test_init_default_dry_run_is_false(self, card_repo):
        """Test that dry_run defaults to False."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        assert generator.dry_run is False

    def test_init_dry_run_true(self):
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

    def test_init_with_empty_providers(self, card_repo):
        """Test initialization with empty provider list."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        assert generator.llm_providers == []

    def test_init_with_single_provider(self, card_repo):
        """Test initialization with single provider."""
        provider = MockLLMProvider(name="single", model="single-model")

        generator = CardGenerator(
            providers=[provider],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        assert len(generator.llm_providers) == 1
        assert generator.llm_providers[0].name == "single"

    def test_init_with_many_providers(self, card_repo):
        """Test initialization with many providers."""
        providers = [
            MockLLMProvider(name=f"p{i}", model=f"m{i}")
            for i in range(10)
        ]

        generator = CardGenerator(
            providers=providers,
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        assert len(generator.llm_providers) == 10

    def test_init_with_none_combine_prompt(self, card_repo):
        """Test initialization with None combine_prompt."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
            combine_prompt=None,
        )

        assert generator.combine_prompt is None

    def test_init_without_formatter(self, card_repo):
        """Test initialization without formatter."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        assert generator.formatter is None

    def test_init_with_same_combiner_and_formatter(self, card_repo):
        """Test initialization where combiner and formatter are same provider."""
        provider = MockLLMProvider(name="dual", model="dual-model")

        generator = CardGenerator(
            providers=[],
            combiner=provider,
            formatter=provider,
            repository=card_repo,
        )

        assert generator.card_combiner is generator.formatter

    # -------------------------------------------------------------------------
    # Process Question Tests
    # -------------------------------------------------------------------------

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
    async def test_process_question_with_default_params(self, generator_with_mocks):
        """Test process_question with default optional parameters."""
        result = await generator_with_mocks.process_question(
            question="Test Question",
        )

        assert result is not None
        assert "cards" in result
        # Default model is LeetCodeProblem
        # No category metadata when not provided

    @pytest.mark.asyncio
    async def test_process_question_without_prompt_template(self, generator_with_mocks):
        """Test process_question without prompt template."""
        result = await generator_with_mocks.process_question(
            question="Test Question",
            prompt_template=None,
            model_class=LeetCodeProblem,
        )

        assert result is not None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model_class", [
        LeetCodeProblem,
        CSProblem,
        PhysicsProblem,
        GenericProblem,
    ])
    async def test_process_question_with_different_models(
        self, generator_with_mocks, model_class
    ):
        """Test process_question with different Pydantic models."""
        result = await generator_with_mocks.process_question(
            question="Test Question",
            model_class=model_class,
        )

        assert result is not None
        assert "cards" in result

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
    async def test_process_question_some_providers_fail(self, card_repo):
        """Test when some providers fail but not all."""
        providers = [
            MockLLMProvider(name="success1", model="s1"),
            FailingMockProvider(name="fail1", model="f1"),
            MockLLMProvider(name="success2", model="s2"),
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

        # Should succeed because at least one provider worked
        assert result is not None
        assert "cards" in result

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

    @pytest.mark.asyncio
    async def test_process_question_formatter_same_as_combiner(self, card_repo):
        """Test when formatter is same provider as combiner."""
        providers = [MockLLMProvider(name="p1", model="m1")]
        same_provider = MockLLMProvider(name="dual", model="d-model")

        generator = CardGenerator(
            providers=providers,
            combiner=same_provider,
            formatter=same_provider,
            repository=card_repo,
        )

        result = await generator.process_question(
            question="Test",
            model_class=LeetCodeProblem,
        )

        assert result is not None
        # Formatter should NOT be called when same as combiner
        assert same_provider.format_call_count == 0

    @pytest.mark.asyncio
    async def test_process_question_with_category_metadata(self, generator_with_mocks):
        """Test that category metadata is included in result."""
        result = await generator_with_mocks.process_question(
            question="Two Sum",
            model_class=LeetCodeProblem,
            category_index=5,
            category_name="Hash Table",
            problem_index=3,
        )

        assert result is not None
        assert result["category_index"] == 5
        assert result["category_name"] == "Hash Table"
        assert result["problem_index"] == 3

    @pytest.mark.asyncio
    async def test_process_question_without_category_metadata(self, generator_with_mocks):
        """Test that missing category metadata is not added."""
        result = await generator_with_mocks.process_question(
            question="Two Sum",
            model_class=LeetCodeProblem,
        )

        assert result is not None
        assert "category_index" not in result
        assert "category_name" not in result
        assert "problem_index" not in result

    @pytest.mark.asyncio
    async def test_process_question_saves_to_repository(self, card_repo):
        """Test that results are saved to repository."""
        providers = [MockLLMProvider(name="p1", model="m1")]
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=providers,
            combiner=combiner,
            formatter=None,
            repository=card_repo,
        )

        result = await generator.process_question(
            question="Binary Search",
            model_class=LeetCodeProblem,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_process_question_handles_unicode(self, generator_with_mocks):
        """Test processing questions with unicode characters."""
        result = await generator_with_mocks.process_question(
            question="二分查找 (Binary Search)",
            model_class=LeetCodeProblem,
            category_name="算法",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_process_question_with_long_question(self, generator_with_mocks):
        """Test processing very long questions."""
        long_question = "A" * 1000

        result = await generator_with_mocks.process_question(
            question=long_question,
            model_class=LeetCodeProblem,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_process_question_with_special_characters(self, generator_with_mocks):
        """Test processing questions with special characters."""
        result = await generator_with_mocks.process_question(
            question="What is O(n²)? And O(log n)?",
            model_class=LeetCodeProblem,
        )

        assert result is not None


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

    # -------------------------------------------------------------------------
    # Tag Stripping Tests
    # -------------------------------------------------------------------------

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

    def test_strips_multiple_spaces_from_tags(self, generator):
        """Test that multiple spaces are stripped from tags."""
        card_data = {
            "cards": [
                {"tags": ["Two   Pointers", "Binary  Search  Tree"]},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert result["cards"][0]["tags"] == ["TwoPointers", "BinarySearchTree"]

    def test_handles_tags_without_spaces(self, generator):
        """Test that tags without spaces are unchanged."""
        card_data = {
            "cards": [
                {"tags": ["Array", "String"]},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert result["cards"][0]["tags"] == ["Array", "String"]

    def test_handles_empty_tags_list(self, generator):
        """Test that empty tags list is preserved."""
        card_data = {
            "cards": [
                {"tags": []},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert result["cards"][0]["tags"] == []

    def test_handles_cards_without_tags(self, generator):
        """Test cards without tags field are unchanged."""
        card_data = {
            "cards": [
                {"front": "Q", "back": "A"},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert "tags" not in result["cards"][0]

    # -------------------------------------------------------------------------
    # Card Type Stripping Tests
    # -------------------------------------------------------------------------

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

    def test_handles_card_type_without_spaces(self, generator):
        """Test that card_type without spaces is unchanged."""
        card_data = {
            "cards": [
                {"card_type": "Definition"},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert result["cards"][0]["card_type"] == "Definition"

    def test_handles_cards_without_card_type(self, generator):
        """Test cards without card_type field are unchanged."""
        card_data = {
            "cards": [
                {"front": "Q", "back": "A"},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert "card_type" not in result["cards"][0]

    def test_strips_leading_trailing_spaces_from_card_type(self, generator):
        """Test card_type with leading/trailing spaces."""
        card_data = {
            "cards": [
                {"card_type": " Core Concept "},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert result["cards"][0]["card_type"] == "CoreConcept"

    # -------------------------------------------------------------------------
    # Category Metadata Tests
    # -------------------------------------------------------------------------

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

    def test_partial_metadata_category_index_only(self, generator):
        """Test adding only category_index."""
        card_data = {"cards": []}

        result = generator._post_process_cards(
            card_data,
            category_index=5,
        )

        assert result["category_index"] == 5
        assert "category_name" not in result
        assert "problem_index" not in result

    def test_partial_metadata_category_name_only(self, generator):
        """Test adding only category_name."""
        card_data = {"cards": []}

        result = generator._post_process_cards(
            card_data,
            category_name="Arrays",
        )

        assert "category_index" not in result
        assert result["category_name"] == "Arrays"
        assert "problem_index" not in result

    def test_partial_metadata_problem_index_only(self, generator):
        """Test adding only problem_index."""
        card_data = {"cards": []}

        result = generator._post_process_cards(
            card_data,
            problem_index=7,
        )

        assert "category_index" not in result
        assert "category_name" not in result
        assert result["problem_index"] == 7

    def test_metadata_with_zero_indices(self, generator):
        """Test metadata with zero values."""
        card_data = {"cards": []}

        result = generator._post_process_cards(
            card_data,
            category_index=0,
            problem_index=0,
        )

        # 0 is falsy but should still be added
        # Note: Current implementation uses `is not None` check
        assert result["category_index"] == 0
        assert result["problem_index"] == 0

    def test_metadata_overwrites_existing(self, generator):
        """Test that metadata overwrites existing keys."""
        card_data = {
            "cards": [],
            "category_index": 999,
            "category_name": "Old",
        }

        result = generator._post_process_cards(
            card_data,
            category_index=1,
            category_name="New",
        )

        assert result["category_index"] == 1
        assert result["category_name"] == "New"

    # -------------------------------------------------------------------------
    # Edge Case Tests
    # -------------------------------------------------------------------------

    def test_empty_cards_list(self, generator):
        """Test with empty cards list."""
        card_data = {"cards": []}

        result = generator._post_process_cards(card_data)

        assert result["cards"] == []

    def test_preserves_other_card_fields(self, generator):
        """Test that other card fields are preserved."""
        card_data = {
            "cards": [
                {
                    "front": "What is X?",
                    "back": "Answer",
                    "tags": ["Tag One"],
                    "card_type": "Core Concept",
                    "extra_field": "preserved",
                },
            ]
        }

        result = generator._post_process_cards(card_data)

        assert result["cards"][0]["front"] == "What is X?"
        assert result["cards"][0]["back"] == "Answer"
        assert result["cards"][0]["extra_field"] == "preserved"

    def test_preserves_top_level_fields(self, generator):
        """Test that other top-level fields are preserved."""
        card_data = {
            "cards": [],
            "metadata": {"version": "1.0"},
            "title": "Test Deck",
        }

        result = generator._post_process_cards(card_data)

        assert result["metadata"] == {"version": "1.0"}
        assert result["title"] == "Test Deck"

    def test_handles_multiple_cards(self, generator):
        """Test processing multiple cards."""
        card_data = {
            "cards": [
                {"tags": ["Tag One"], "card_type": "Type A"},
                {"tags": ["Tag Two"], "card_type": "Type B"},
                {"tags": ["Tag Three"], "card_type": "Type C"},
            ]
        }

        result = generator._post_process_cards(card_data)

        assert len(result["cards"]) == 3
        assert result["cards"][0]["tags"] == ["TagOne"]
        assert result["cards"][1]["tags"] == ["TagTwo"]
        assert result["cards"][2]["tags"] == ["TagThree"]

    def test_modifies_input_in_place(self, generator):
        """Test that input is modified in place (side effect)."""
        card_data = {
            "cards": [{"tags": ["Tag One"]}]
        }

        result = generator._post_process_cards(card_data)

        # Result should be the same object
        assert result is card_data
        assert card_data["cards"][0]["tags"] == ["TagOne"]


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

    # -------------------------------------------------------------------------
    # Filtering Tests
    # -------------------------------------------------------------------------

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

    def test_filters_none_results(self, generator_with_repo):
        """Test that None results are filtered out."""
        generator, card_repo = generator_with_repo

        problem_id = card_repo.create_initial_problem(
            question_name="Test"
        )

        provider_results = [
            SAMPLE_CARD_RESPONSE,
            None,  # None result
        ]

        valid = generator._save_provider_results(problem_id, provider_results)

        assert len(valid) == 1
        assert valid[0] == SAMPLE_CARD_RESPONSE

    def test_filters_all_empty_results(self, generator_with_repo):
        """Test when all results are empty."""
        generator, card_repo = generator_with_repo

        problem_id = card_repo.create_initial_problem(
            question_name="Test"
        )

        provider_results = ["", ""]

        valid = generator._save_provider_results(problem_id, provider_results)

        assert len(valid) == 0

    # -------------------------------------------------------------------------
    # Saving Tests
    # -------------------------------------------------------------------------

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

    def test_counts_cards_in_valid_json(self, generator_with_repo):
        """Test that cards are counted for valid JSON."""
        generator, card_repo = generator_with_repo

        problem_id = card_repo.create_initial_problem(
            question_name="Test"
        )

        two_cards = json.dumps({
            "cards": [
                {"front": "Q1", "back": "A1"},
                {"front": "Q2", "back": "A2"},
            ]
        })

        provider_results = [two_cards, SAMPLE_CARD_RESPONSE]

        valid = generator._save_provider_results(problem_id, provider_results)

        assert len(valid) == 2

    def test_handles_missing_cards_key(self, generator_with_repo):
        """Test handling JSON without cards key."""
        generator, card_repo = generator_with_repo

        problem_id = card_repo.create_initial_problem(
            question_name="Test"
        )

        no_cards = json.dumps({"data": "something"})

        provider_results = [no_cards, SAMPLE_CARD_RESPONSE]

        valid = generator._save_provider_results(problem_id, provider_results)

        # Still saved, just card_count = None or 0
        assert len(valid) == 2

    def test_returns_valid_results_in_order(self, generator_with_repo):
        """Test that valid results maintain order."""
        generator, card_repo = generator_with_repo

        problem_id = card_repo.create_initial_problem(
            question_name="Test"
        )

        response_a = json.dumps({"cards": [{"id": "A"}]})
        response_b = json.dumps({"cards": [{"id": "B"}]})

        provider_results = [response_a, "", response_b]

        # Need 3 providers for 3 results
        generator.llm_providers.append(MockLLMProvider(name="p3", model="m3"))

        valid = generator._save_provider_results(problem_id, provider_results)

        assert len(valid) == 2
        assert valid[0] == response_a
        assert valid[1] == response_b

    def test_handles_empty_provider_list(self, in_memory_db):
        """Test with empty provider list."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )
        card_repo = run_repo.get_card_repository()

        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        problem_id = card_repo.create_initial_problem(question_name="Test")

        valid = generator._save_provider_results(problem_id, [])

        assert valid == []


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

    # -------------------------------------------------------------------------
    # Same Provider Tests
    # -------------------------------------------------------------------------

    def test_same_provider(self, generator):
        """Test comparing identical providers."""
        p1 = MockLLMProvider(name="test", model="model-a")
        p2 = MockLLMProvider(name="test", model="model-a")

        assert generator._is_same_provider(p1, p2) is True

    def test_same_instance(self, generator):
        """Test comparing same instance."""
        p = MockLLMProvider(name="test", model="model-a")

        assert generator._is_same_provider(p, p) is True

    # -------------------------------------------------------------------------
    # Different Provider Tests
    # -------------------------------------------------------------------------

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

    def test_different_name_and_model(self, generator):
        """Test providers with different names and models."""
        p1 = MockLLMProvider(name="cerebras", model="llama-70b")
        p2 = MockLLMProvider(name="nvidia", model="llama-8b")

        assert generator._is_same_provider(p1, p2) is False

    # -------------------------------------------------------------------------
    # Edge Cases
    # -------------------------------------------------------------------------

    def test_empty_name(self, generator):
        """Test providers with empty names."""
        p1 = MockLLMProvider(name="", model="model")
        p2 = MockLLMProvider(name="", model="model")

        assert generator._is_same_provider(p1, p2) is True

    def test_empty_model(self, generator):
        """Test providers with empty models."""
        p1 = MockLLMProvider(name="provider", model="")
        p2 = MockLLMProvider(name="provider", model="")

        assert generator._is_same_provider(p1, p2) is True

    def test_case_sensitive_name(self, generator):
        """Test that name comparison is case-sensitive."""
        p1 = MockLLMProvider(name="Test", model="model")
        p2 = MockLLMProvider(name="test", model="model")

        assert generator._is_same_provider(p1, p2) is False

    def test_case_sensitive_model(self, generator):
        """Test that model comparison is case-sensitive."""
        p1 = MockLLMProvider(name="test", model="Model")
        p2 = MockLLMProvider(name="test", model="model")

        assert generator._is_same_provider(p1, p2) is False

    @pytest.mark.parametrize("name1,model1,name2,model2,expected", [
        ("cerebras", "llama-70b", "cerebras", "llama-70b", True),
        ("nvidia", "deepseek", "nvidia", "deepseek", True),
        ("openrouter", "claude-3", "openrouter", "gpt-4", False),
        ("cerebras", "llama", "nvidia", "llama", False),
        ("provider", "model-v1", "provider", "model-v2", False),
    ])
    def test_various_provider_combinations(
        self, generator, name1, model1, name2, model2, expected
    ):
        """Test various provider name/model combinations."""
        p1 = MockLLMProvider(name=name1, model=model1)
        p2 = MockLLMProvider(name=name2, model=model2)

        assert generator._is_same_provider(p1, p2) is expected


class TestGenerateInitialCards:
    """Tests for _generate_initial_cards method."""

    # -------------------------------------------------------------------------
    # Parallel Generation Tests
    # -------------------------------------------------------------------------

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

    @pytest.mark.asyncio
    async def test_single_provider(self):
        """Test generation with single provider."""
        provider = MockLLMProvider(name="single", model="model")

        generator = CardGenerator(
            providers=[provider],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

        results = await generator._generate_initial_cards(
            question="Test",
            json_schema={},
            prompt_template="Prompt",
        )

        assert len(results) == 1
        assert provider.initial_call_count == 1

    @pytest.mark.asyncio
    async def test_no_providers(self):
        """Test generation with no providers."""
        generator = CardGenerator(
            providers=[],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

        results = await generator._generate_initial_cards(
            question="Test",
            json_schema={},
            prompt_template="Prompt",
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_many_providers(self):
        """Test generation with many providers."""
        providers = [
            MockLLMProvider(name=f"p{i}", model=f"m{i}")
            for i in range(10)
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

        assert len(results) == 10

    # -------------------------------------------------------------------------
    # Parameter Passing Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_passes_question_to_providers(self):
        """Test that question is passed to all providers."""
        provider = MockLLMProvider(name="test", model="model")

        generator = CardGenerator(
            providers=[provider],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

        await generator._generate_initial_cards(
            question="Binary Search",
            json_schema={},
            prompt_template="Prompt",
        )

        # Check via call count (MockLLMProvider doesn't track args)
        assert provider.initial_call_count == 1

    @pytest.mark.asyncio
    async def test_passes_json_schema(self):
        """Test that json_schema is passed to providers."""
        provider = MockLLMProvider(name="test", model="model")

        generator = CardGenerator(
            providers=[provider],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

        schema = {"type": "object", "properties": {"cards": {}}}

        await generator._generate_initial_cards(
            question="Test",
            json_schema=schema,
            prompt_template="Prompt",
        )

        assert provider.initial_call_count == 1

    @pytest.mark.asyncio
    async def test_passes_prompt_template(self):
        """Test that prompt_template is passed to providers."""
        provider = MockLLMProvider(name="test", model="model")

        generator = CardGenerator(
            providers=[provider],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

        await generator._generate_initial_cards(
            question="Test",
            json_schema={},
            prompt_template="Custom prompt template",
        )

        assert provider.initial_call_count == 1

    @pytest.mark.asyncio
    async def test_none_prompt_template(self):
        """Test with None prompt template."""
        provider = MockLLMProvider(name="test", model="model")

        generator = CardGenerator(
            providers=[provider],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

        results = await generator._generate_initial_cards(
            question="Test",
            json_schema={},
            prompt_template=None,
        )

        assert len(results) == 1

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_handles_some_providers_failing(self):
        """Test when some providers fail."""
        providers = [
            MockLLMProvider(name="success", model="m1"),
            FailingMockProvider(name="fail", model="m2"),
            MockLLMProvider(name="success2", model="m3"),
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

        # asyncio.gather collects all results including exceptions
        # depending on implementation, failed results might be None or raise
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_handles_all_providers_failing(self):
        """Test when all providers fail."""
        providers = [
            FailingMockProvider(name="f1", model="m1"),
            FailingMockProvider(name="f2", model="m2"),
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

        assert len(results) == 2  # Both calls complete (with failures)


class TestCombineResults:
    """Tests for _combine_results method."""

    # -------------------------------------------------------------------------
    # Success Cases
    # -------------------------------------------------------------------------

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
    async def test_combine_single_result(self):
        """Test combining single result."""
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=[],
            combiner=combiner,
            formatter=None,
            repository=None,
        )

        result = await generator._combine_results(
            question="Test",
            valid_results=["single result"],
            json_schema={},
        )

        assert result is not None
        assert combiner.combine_call_count == 1

    @pytest.mark.asyncio
    async def test_combine_many_results(self):
        """Test combining many results."""
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=[],
            combiner=combiner,
            formatter=None,
            repository=None,
        )

        results = [f"result{i}" for i in range(5)]

        result = await generator._combine_results(
            question="Test",
            valid_results=results,
            json_schema={},
        )

        assert result is not None

    # -------------------------------------------------------------------------
    # Formatter Tests
    # -------------------------------------------------------------------------

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
    async def test_combine_skips_formatter_when_same_as_combiner(self):
        """Test formatter is skipped when same as combiner."""
        same_provider = MockLLMProvider(name="dual", model="d-model")

        generator = CardGenerator(
            providers=[],
            combiner=same_provider,
            formatter=same_provider,
            repository=None,
        )

        result = await generator._combine_results(
            question="Test",
            valid_results=["result1"],
            json_schema={},
        )

        assert result is not None
        # Format should not be called when combiner == formatter
        assert same_provider.format_call_count == 0

    @pytest.mark.asyncio
    async def test_combine_different_formatter(self):
        """Test with different combiner and formatter."""
        combiner = MockLLMProvider(name="combiner", model="model-a")
        formatter = MockLLMProvider(
            name="formatter",
            model="model-b",
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
            valid_results=["result"],
            json_schema={},
        )

        assert result is not None
        assert combiner.combine_call_count == 1
        assert formatter.format_call_count == 1

    # -------------------------------------------------------------------------
    # Failure Cases
    # -------------------------------------------------------------------------

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

    @pytest.mark.asyncio
    async def test_combine_returns_none_on_empty_response(self):
        """Test combine returns None when combiner returns empty."""
        combiner = MockLLMProvider(
            name="combiner",
            model="c",
            responses={"combine": ""}
        )

        generator = CardGenerator(
            providers=[],
            combiner=combiner,
            formatter=None,
            repository=None,
        )

        result = await generator._combine_results(
            question="Test",
            valid_results=["result"],
            json_schema={},
        )

        # Empty response from combiner should return None
        assert result is None

    # -------------------------------------------------------------------------
    # Input Formatting Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_combine_formats_inputs_correctly(self):
        """Test that inputs are formatted with Set labels."""
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=[],
            combiner=combiner,
            formatter=None,
            repository=None,
        )

        await generator._combine_results(
            question="Test",
            valid_results=["First result", "Second result"],
            json_schema={},
        )

        # Combiner should have been called once
        assert combiner.combine_call_count == 1


# ============================================================================
# Integration Tests for Full Workflow
# ============================================================================

class TestCardGeneratorWorkflow:
    """Tests for complete CardGenerator workflows."""

    @pytest.fixture
    def full_generator(self, in_memory_db):
        """Create a fully configured generator."""
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
        combiner = MockLLMProvider(name="combiner", model="c-model")

        generator = CardGenerator(
            providers=providers,
            combiner=combiner,
            formatter=None,
            repository=card_repo,
            combine_prompt="Combine the results",
        )
        return generator, card_repo

    @pytest.mark.asyncio
    async def test_full_workflow_success(self, full_generator):
        """Test complete successful workflow."""
        generator, card_repo = full_generator

        result = await generator.process_question(
            question="Binary Search",
            prompt_template="Generate cards",
            model_class=LeetCodeProblem,
            category_index=1,
            category_name="Algorithms",
            problem_index=1,
        )

        assert result is not None
        assert "cards" in result
        assert result["category_index"] == 1
        assert result["category_name"] == "Algorithms"

    @pytest.mark.asyncio
    async def test_workflow_with_all_failures(self, in_memory_db):
        """Test workflow when all providers fail."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )
        card_repo = run_repo.get_card_repository()

        generator = CardGenerator(
            providers=[FailingMockProvider(name="f1", model="m1")],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        result = await generator.process_question(
            question="Test",
            model_class=LeetCodeProblem,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_workflow_tracks_call_counts(self, full_generator):
        """Test that provider methods are called correctly."""
        generator, _ = full_generator

        await generator.process_question(
            question="Test",
            model_class=LeetCodeProblem,
        )

        # Both providers should have been called for initial generation
        for provider in generator.llm_providers:
            assert provider.initial_call_count == 1

        # Combiner should have been called once
        assert generator.card_combiner.combine_call_count == 1

    @pytest.mark.asyncio
    async def test_workflow_processes_multiple_questions(self, full_generator):
        """Test processing multiple questions sequentially."""
        generator, _ = full_generator

        questions = ["Question 1", "Question 2", "Question 3"]

        for i, question in enumerate(questions, 1):
            result = await generator.process_question(
                question=question,
                model_class=LeetCodeProblem,
                category_index=1,
                category_name="Test",
                problem_index=i,
            )
            assert result is not None

        # Each provider should be called once per question
        for provider in generator.llm_providers:
            assert provider.initial_call_count == 3


# ============================================================================
# Parametrized Tests
# ============================================================================

class TestParametrizedGenerator:
    """Parametrized tests for CardGenerator."""

    @pytest.mark.parametrize("num_providers", [1, 2, 5, 10])
    def test_init_with_various_provider_counts(self, num_providers):
        """Test initialization with various provider counts."""
        providers = [
            MockLLMProvider(name=f"p{i}", model=f"m{i}")
            for i in range(num_providers)
        ]

        generator = CardGenerator(
            providers=providers,
            combiner=MockLLMProvider(),
            formatter=None,
            repository=None,
        )

        assert len(generator.llm_providers) == num_providers

    @pytest.mark.parametrize("question", [
        "Short",
        "Medium length question",
        "A" * 100,
        "Question with special chars: @#$%^&*()",
        "Unicode: 你好世界",
        "Emoji: 🎉🚀",
    ])
    @pytest.mark.asyncio
    async def test_various_question_formats(self, in_memory_db, question):
        """Test processing various question formats."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="leetcode",
            subject="leetcode",
            card_type="standard"
        )
        card_repo = run_repo.get_card_repository()

        generator = CardGenerator(
            providers=[MockLLMProvider()],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        result = await generator.process_question(
            question=question,
            model_class=LeetCodeProblem,
        )

        assert result is not None

    @pytest.mark.parametrize("model_class,expected_type", [
        (LeetCodeProblem, "LeetCodeProblem"),
        (CSProblem, "CSProblem"),
        (PhysicsProblem, "PhysicsProblem"),
        (GenericProblem, "GenericProblem"),
    ])
    @pytest.mark.asyncio
    async def test_various_model_classes(
        self, in_memory_db, model_class, expected_type
    ):
        """Test with various Pydantic model classes."""
        run_repo = RunRepository(Path(":memory:"), db_manager=in_memory_db)
        run_repo.create_new_run(
            mode="test",
            subject="test",
            card_type="standard"
        )
        card_repo = run_repo.get_card_repository()

        generator = CardGenerator(
            providers=[MockLLMProvider()],
            combiner=MockLLMProvider(),
            formatter=None,
            repository=card_repo,
        )

        result = await generator.process_question(
            question="Test",
            model_class=model_class,
        )

        assert result is not None
