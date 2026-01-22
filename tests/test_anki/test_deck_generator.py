"""Tests for anki/generator.py."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.anki.generator import DeckGenerator, load_card_data


class TestLoadCardData:
    """Tests for load_card_data function."""

    def test_load_valid_json(self, tmp_path):
        """Test loading valid JSON file."""
        data = [{"title": "Test", "cards": []}]
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))

        result = load_card_data(str(json_file))

        assert result == data

    def test_load_nonexistent_file_raises(self, tmp_path):
        """Test loading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_card_data(str(tmp_path / "missing.json"))

    def test_load_invalid_json_raises(self, tmp_path):
        """Test loading invalid JSON raises error."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")

        with pytest.raises(json.JSONDecodeError):
            load_card_data(str(json_file))


class TestDeckGenerator:
    """Tests for DeckGenerator class."""

    @pytest.fixture
    def sample_data(self):
        """Sample card data for testing."""
        return [
            {
                "title": "Binary Search",
                "topic": "Arrays",
                "difficulty": "Medium",
                "cards": [
                    {
                        "card_type": "Algorithm",
                        "tags": ["BinarySearch", "Arrays"],
                        "front": "What is binary search?",
                        "back": "A search algorithm for sorted arrays."
                    }
                ]
            }
        ]

    def test_init(self, sample_data):
        """Test DeckGenerator initialization."""
        generator = DeckGenerator(sample_data, deck_prefix="Test")

        assert generator.card_data == sample_data
        assert generator.deck_prefix == "Test"
        assert generator.deck_collection == {}

    def test_init_default_prefix(self, sample_data):
        """Test DeckGenerator with default prefix."""
        generator = DeckGenerator(sample_data)

        assert generator.deck_prefix == "LeetCode"

    def test_generate_id_consistent(self, sample_data):
        """Test _generate_id produces consistent IDs."""
        generator = DeckGenerator(sample_data)

        id1 = generator._generate_id("test text")
        id2 = generator._generate_id("test text")

        assert id1 == id2
        assert isinstance(id1, int)

    def test_generate_id_different_for_different_text(self, sample_data):
        """Test _generate_id produces different IDs for different text."""
        generator = DeckGenerator(sample_data)

        id1 = generator._generate_id("text one")
        id2 = generator._generate_id("text two")

        assert id1 != id2

    def test_get_or_create_deck_creates_new(self, sample_data):
        """Test get_or_create_deck creates new deck."""
        generator = DeckGenerator(sample_data)

        deck = generator.get_or_create_deck("Test::Category::Problem")

        assert deck is not None
        assert "Test::Category::Problem" in generator.deck_collection

    def test_get_or_create_deck_returns_existing(self, sample_data):
        """Test get_or_create_deck returns existing deck."""
        generator = DeckGenerator(sample_data)

        deck1 = generator.get_or_create_deck("Test::Deck")
        deck2 = generator.get_or_create_deck("Test::Deck")

        assert deck1 is deck2

    def test_get_prefix(self, sample_data):
        """Test _get_prefix returns configured prefix."""
        generator = DeckGenerator(sample_data, deck_prefix="Custom")

        assert generator._get_prefix() == "Custom"

    def test_build_deck_path_with_metadata(self, sample_data):
        """Test _build_deck_path with category metadata."""
        generator = DeckGenerator(sample_data, deck_prefix="LeetCode")

        path = generator._build_deck_path(
            problem_title="Binary Search",
            topic_name="Arrays",
            category_index=1,
            category_name="Binary Search",
            problem_index=2,
        )

        assert path == "LeetCode::001 Binary Search::002 Binary Search"

    def test_build_deck_path_without_metadata(self, sample_data):
        """Test _build_deck_path without category metadata (legacy)."""
        generator = DeckGenerator(sample_data, deck_prefix="LeetCode")

        path = generator._build_deck_path(
            problem_title="Binary Search",
            topic_name="Arrays",
        )

        assert path == "LeetCode::Arrays::Binary Search"

    def test_process_creates_decks(self, sample_data):
        """Test process creates decks and notes."""
        generator = DeckGenerator(sample_data, deck_prefix="Test")
        generator.process()

        # Should have created at least one deck
        assert len(generator.deck_collection) > 0

    def test_process_with_category_metadata(self):
        """Test process with category metadata."""
        data = [
            {
                "title": "Two Sum",
                "topic": "Arrays",
                "difficulty": "Easy",
                "category_index": 1,
                "category_name": "Arrays",
                "problem_index": 1,
                "cards": [
                    {
                        "card_type": "Concept",
                        "tags": [],
                        "front": "Q",
                        "back": "A"
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="LeetCode")
        generator.process()

        # Deck should be created with numbered path
        expected_path = "LeetCode::001 Arrays::001 Two Sum"
        assert expected_path in generator.deck_collection

    def test_save_package_empty_collection(self, sample_data, tmp_path):
        """Test save_package with empty collection logs warning."""
        generator = DeckGenerator(sample_data)
        # Don't call process, so deck_collection is empty

        output_path = str(tmp_path / "output.apkg")
        generator.save_package(output_path)

        # File should not be created
        assert not (tmp_path / "output.apkg").exists()

    def test_save_package_creates_file(self, sample_data, tmp_path):
        """Test save_package creates .apkg file."""
        generator = DeckGenerator(sample_data)
        generator.process()

        output_path = str(tmp_path / "output.apkg")
        generator.save_package(output_path)

        assert (tmp_path / "output.apkg").exists()


class TestAddCards:
    """Tests for card adding methods."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return DeckGenerator([])

    def test_add_basic_card(self, generator):
        """Test adding a basic card."""
        deck = generator.get_or_create_deck("Test::Deck")

        card_data = {
            "card_type": "Concept",
            "tags": ["Tag1"],
            "front": "Question?",
            "back": "Answer."
        }

        generator._add_basic_card(
            deck,
            card_data,
            "Test Problem",
            "Topic",
            "Medium",
            ["Tag1", "topic::Topic"]
        )

        # Deck should have one note
        assert len(deck.notes) == 1

    def test_add_mcq_card(self):
        """Test adding an MCQ card."""
        generator = DeckGenerator([], deck_prefix="Test_MCQ")
        deck = generator.get_or_create_deck("Test_MCQ::Deck")

        card_data = {
            "card_type": "Concept",
            "tags": ["MCQ"],
            "question": "What is X?",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
            "explanation": "Because B."
        }

        generator._add_mcq_card(
            deck,
            card_data,
            "Test Problem",
            "Topic",
            "Medium",
            ["MCQ"]
        )

        assert len(deck.notes) == 1


class TestShuffleOptions:
    """Tests for _shuffle_options method."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return DeckGenerator([])

    def test_shuffle_preserves_correct_answer(self, generator):
        """Test that shuffling preserves the correct answer mapping."""
        options = ["A answer", "B answer", "C answer", "D answer"]
        correct = "B"

        # Run multiple times to test randomness
        for _ in range(10):
            shuffled, new_correct = generator._shuffle_options(options, correct)

            # Find where the original B answer ended up
            original_b_index = options.index("B answer")
            new_b_index = shuffled.index("B answer")

            # The new correct answer should point to where B answer is now
            expected_letter = ["A", "B", "C", "D"][new_b_index]
            assert new_correct == expected_letter

    def test_shuffle_with_non_4_options(self, generator):
        """Test shuffling with non-4 options returns unchanged."""
        options = ["A", "B", "C"]  # Only 3 options
        correct = "A"

        shuffled, new_correct = generator._shuffle_options(options, correct)

        assert shuffled == options
        assert new_correct == correct

    def test_shuffle_returns_4_options(self, generator):
        """Test that shuffle always returns 4 options."""
        options = ["A", "B", "C", "D"]
        correct = "A"

        shuffled, _ = generator._shuffle_options(options, correct)

        assert len(shuffled) == 4


class TestMCQDetection:
    """Tests for MCQ mode detection."""

    def test_mcq_prefix_detection(self):
        """Test that MCQ mode is detected from prefix."""
        data = [
            {
                "title": "Test",
                "topic": "Topic",
                "difficulty": "Easy",
                "cards": [
                    {
                        "card_type": "MCQ",
                        "tags": [],
                        "question": "Q?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "Exp"
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="LeetCode_MCQ")
        generator.process()

        # MCQ should be detected and MCQ card added
        assert len(generator.deck_collection) > 0

    def test_non_mcq_prefix_uses_basic(self):
        """Test that non-MCQ prefix uses basic cards even with options."""
        data = [
            {
                "title": "Test",
                "topic": "Topic",
                "difficulty": "Easy",
                "cards": [
                    {
                        "card_type": "Concept",
                        "tags": [],
                        "front": "Q",
                        "back": "A",
                        "options": ["A", "B", "C", "D"],  # Has options but not MCQ mode
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="LeetCode")  # Not MCQ
        generator.process()

        # Should use basic card format
        assert len(generator.deck_collection) > 0
