"""Unit tests for DeckGenerator (Anki)."""

import pytest
import json
from pathlib import Path


class TestLoadCardData:
    """Test load_card_data function."""

    def test_load_card_data_success(self, tmp_path, sample_card_dict):
        """Test that load_card_data loads JSON correctly."""
        from src.anki.generator import load_card_data

        json_file = tmp_path / "test_deck.json"
        with open(json_file, "w") as f:
            json.dump([sample_card_dict], f)

        data = load_card_data(str(json_file))

        assert len(data) == 1
        assert "cards" in data[0]

    def test_load_card_data_file_not_found(self, tmp_path):
        """Test that load_card_data raises on missing file."""
        from src.anki.generator import load_card_data

        with pytest.raises(FileNotFoundError):
            load_card_data(str(tmp_path / "nonexistent.json"))

    def test_load_card_data_invalid_json(self, tmp_path):
        """Test that load_card_data raises on invalid JSON."""
        from src.anki.generator import load_card_data

        json_file = tmp_path / "invalid.json"
        with open(json_file, "w") as f:
            f.write("not valid json")

        with pytest.raises(json.JSONDecodeError):
            load_card_data(str(json_file))


class TestDeckGeneratorInitialization:
    """Test DeckGenerator initialization."""

    def test_deck_generator_initialization(self, sample_card_dict):
        """Test that DeckGenerator initializes correctly."""
        from src.anki.generator import DeckGenerator

        card_data = [sample_card_dict]
        generator = DeckGenerator(card_data, deck_prefix="TestDeck")

        assert generator.card_data == card_data
        assert generator.deck_prefix == "TestDeck"

    def test_deck_generator_with_empty_data(self):
        """Test that DeckGenerator handles empty data."""
        from src.anki.generator import DeckGenerator

        generator = DeckGenerator([], deck_prefix="TestDeck")

        assert len(generator.card_data) == 0


class TestDeckGeneratorPrefix:
    """Test DeckGenerator prefix handling."""

    def test_get_prefix_returns_deck_prefix(self):
        """Test that _get_prefix returns the configured deck_prefix."""
        from src.anki.generator import DeckGenerator

        generator = DeckGenerator([], deck_prefix="LeetCode")
        assert generator._get_prefix() == "LeetCode"

        generator2 = DeckGenerator([], deck_prefix="CS_MCQ")
        assert generator2._get_prefix() == "CS_MCQ"

    def test_mcq_mode_detection(self):
        """Test MCQ mode is detected from deck_prefix."""
        from src.anki.generator import DeckGenerator

        # Standard mode
        gen_standard = DeckGenerator([], deck_prefix="LeetCode")
        # MCQ detection happens in _add_card_to_deck based on 'MCQ' in prefix
        assert "MCQ" not in gen_standard.deck_prefix

        # MCQ mode
        gen_mcq = DeckGenerator([], deck_prefix="LeetCode_MCQ")
        assert "MCQ" in gen_mcq.deck_prefix


class TestDeckGeneratorPaths:
    """Test DeckGenerator path building."""

    @pytest.fixture
    def generator(self):
        """Create a generator with empty data."""
        from src.anki.generator import DeckGenerator
        return DeckGenerator([], deck_prefix="LeetCode")

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

    def test_build_deck_path_mcq_prefix(self):
        """Test deck path with MCQ prefix."""
        from src.anki.generator import DeckGenerator
        generator = DeckGenerator([], deck_prefix="CS_MCQ")

        path = generator._build_deck_path(
            problem_title="Binary Search",
            topic_name="Algorithms",
            category_index=2,
            category_name="Searching",
            problem_index=1
        )

        assert path == "CS_MCQ::002 Searching::001 Binary Search"
