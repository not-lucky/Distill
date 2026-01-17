"""Unit tests for DeckGenerator (Anki)."""

import pytest
import json
from pathlib import Path


class TestDeckGeneratorInitialization:
    """Test DeckGenerator initialization."""

    @pytest.fixture
    def sample_json_file(self, tmp_path, sample_card_dict):
        """Create a temporary JSON file for testing."""
        json_file = tmp_path / "test_deck.json"
        with open(json_file, "w") as f:
            json.dump([sample_card_dict], f)
        return str(json_file)

    def test_deck_generator_initialization(self, sample_json_file):
        """Test that DeckGenerator initializes correctly."""
        from src.anki.generator import DeckGenerator

        generator = DeckGenerator(sample_json_file, deck_prefix="TestDeck")

        assert generator.json_file_path == sample_json_file
        assert generator.deck_prefix == "TestDeck"

    def test_deck_generator_loads_data(self, sample_json_file):
        """Test that DeckGenerator loads JSON data."""
        from src.anki.generator import DeckGenerator

        generator = DeckGenerator(sample_json_file, deck_prefix="TestDeck")

        assert len(generator.card_data) == 1
        assert "cards" in generator.card_data[0]


class TestDeckGeneratorPrefix:
    """Test DeckGenerator prefix handling."""

    @pytest.fixture
    def empty_json_file(self, tmp_path):
        """Create an empty JSON file."""
        json_file = tmp_path / "empty.json"
        with open(json_file, "w") as f:
            json.dump([], f)
        return str(json_file)

    def test_get_prefix_returns_deck_prefix(self, empty_json_file):
        """Test that _get_prefix returns the configured deck_prefix."""
        from src.anki.generator import DeckGenerator

        generator = DeckGenerator(empty_json_file, deck_prefix="LeetCode")
        assert generator._get_prefix() == "LeetCode"

        generator2 = DeckGenerator(empty_json_file, deck_prefix="CS_MCQ")
        assert generator2._get_prefix() == "CS_MCQ"

    def test_mcq_mode_detection(self, empty_json_file):
        """Test MCQ mode is detected from deck_prefix."""
        from src.anki.generator import DeckGenerator

        # Standard mode
        gen_standard = DeckGenerator(empty_json_file, deck_prefix="LeetCode")
        # MCQ detection happens in _add_card_to_deck based on 'MCQ' in prefix
        assert "MCQ" not in gen_standard.deck_prefix

        # MCQ mode
        gen_mcq = DeckGenerator(empty_json_file, deck_prefix="LeetCode_MCQ")
        assert "MCQ" in gen_mcq.deck_prefix


class TestDeckGeneratorPaths:
    """Test DeckGenerator path building."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create a generator with empty data."""
        json_file = tmp_path / "test.json"
        with open(json_file, "w") as f:
            json.dump([], f)

        from src.anki.generator import DeckGenerator
        return DeckGenerator(str(json_file), deck_prefix="LeetCode")

    def test_build_deck_path_with_category_metadata(self, generator):
        """Test deck path building with category metadata."""
        path = generator._build_deck_path(
            problem_title="Min Stack",
            topic_name="Stacks",
            category_index=1,
            category_name="Stacks",
            problem_index=5
        )

        assert path == "LeetCode::001 Stacks::005 Min Stack"

    def test_build_deck_path_without_metadata(self, generator):
        """Test deck path building without category metadata (legacy)."""
        path = generator._build_deck_path(
            problem_title="Min Stack",
            topic_name="Stacks",
            category_index=None,
            category_name=None,
            problem_index=None
        )

        assert path == "LeetCode::Stacks::Min Stack"

    def test_build_deck_path_mcq_prefix(self, tmp_path):
        """Test deck path with MCQ prefix."""
        json_file = tmp_path / "test.json"
        with open(json_file, "w") as f:
            json.dump([], f)

        from src.anki.generator import DeckGenerator
        generator = DeckGenerator(str(json_file), deck_prefix="CS_MCQ")

        path = generator._build_deck_path(
            problem_title="Binary Search",
            topic_name="Algorithms",
            category_index=2,
            category_name="Searching",
            problem_index=1
        )

        assert path == "CS_MCQ::002 Searching::001 Binary Search"
