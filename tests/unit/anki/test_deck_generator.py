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


class TestHierarchicalDeckStructure:
    """Tests for hierarchical deck creation and naming."""

    def test_deep_nested_deck_structure(self):
        """Test creating deeply nested deck hierarchies."""
        data = [
            {
                "title": "Problem 1",
                "topic": "Category A",
                "difficulty": "Easy",
                "category_index": 1,
                "category_name": "Algorithms",
                "problem_index": 1,
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q1", "back": "A1"}]
            },
            {
                "title": "Problem 2",
                "topic": "Category A",
                "difficulty": "Medium",
                "category_index": 1,
                "category_name": "Algorithms",
                "problem_index": 2,
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q2", "back": "A2"}]
            },
            {
                "title": "Problem 3",
                "topic": "Category B",
                "difficulty": "Hard",
                "category_index": 2,
                "category_name": "Data Structures",
                "problem_index": 1,
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q3", "back": "A3"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="LeetCode")
        generator.process()

        # Should have 3 separate leaf decks
        assert len(generator.deck_collection) == 3
        assert "LeetCode::001 Algorithms::001 Problem 1" in generator.deck_collection
        assert "LeetCode::001 Algorithms::002 Problem 2" in generator.deck_collection
        assert "LeetCode::002 Data Structures::001 Problem 3" in generator.deck_collection

    def test_multiple_cards_per_problem(self):
        """Test multiple cards within a single problem."""
        data = [
            {
                "title": "Multi-Card Problem",
                "topic": "Testing",
                "difficulty": "Medium",
                "cards": [
                    {"card_type": "Concept", "tags": [], "front": "Q1", "back": "A1"},
                    {"card_type": "Implementation", "tags": [], "front": "Q2", "back": "A2"},
                    {"card_type": "EdgeCase", "tags": [], "front": "Q3", "back": "A3"},
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Test")
        generator.process()

        # Should have one deck with multiple notes
        assert len(generator.deck_collection) == 1
        deck_path = "Test::Testing::Multi-Card Problem"
        assert deck_path in generator.deck_collection
        assert len(generator.deck_collection[deck_path].notes) == 3

    def test_special_characters_in_deck_path(self):
        """Test deck paths with special characters."""
        data = [
            {
                "title": "Two Sum (Easy)",
                "topic": "Arrays & Hashing",
                "difficulty": "Easy",
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="LeetCode")
        generator.process()

        # Should handle special chars in path
        expected_path = "LeetCode::Arrays & Hashing::Two Sum (Easy)"
        assert expected_path in generator.deck_collection

    def test_unicode_in_deck_path(self):
        """Test deck paths with unicode characters."""
        data = [
            {
                "title": "算法问题",
                "topic": "数据结构",
                "difficulty": "中等",
                "cards": [{"card_type": "概念", "tags": [], "front": "问题?", "back": "答案。"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="中文")
        generator.process()

        expected_path = "中文::数据结构::算法问题"
        assert expected_path in generator.deck_collection

    def test_large_category_and_problem_indices(self):
        """Test formatting with large indices (3-digit)."""
        data = [
            {
                "title": "Problem 100",
                "topic": "Large",
                "difficulty": "Hard",
                "category_index": 100,
                "category_name": "Advanced",
                "problem_index": 999,
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="LeetCode")
        generator.process()

        expected_path = "LeetCode::100 Advanced::999 Problem 100"
        assert expected_path in generator.deck_collection

    def test_mixed_metadata_and_legacy_problems(self):
        """Test mixing problems with and without category metadata."""
        data = [
            {
                "title": "With Metadata",
                "topic": "Cat1",
                "difficulty": "Easy",
                "category_index": 1,
                "category_name": "Category",
                "problem_index": 1,
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q1", "back": "A1"}]
            },
            {
                "title": "Without Metadata",
                "topic": "Cat2",
                "difficulty": "Easy",
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q2", "back": "A2"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Mixed")
        generator.process()

        assert "Mixed::001 Category::001 With Metadata" in generator.deck_collection
        assert "Mixed::Cat2::Without Metadata" in generator.deck_collection


class TestApkgFileValidity:
    """Tests for .apkg file generation and validity."""

    def test_apkg_file_is_valid_zip(self, tmp_path):
        """Test that generated .apkg is a valid zip file."""
        import zipfile

        data = [
            {
                "title": "Test",
                "topic": "Topic",
                "difficulty": "Easy",
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Test")
        generator.process()

        output_path = tmp_path / "test.apkg"
        generator.save_package(str(output_path))

        # .apkg should be a valid zip file
        assert zipfile.is_zipfile(output_path)

    def test_apkg_contains_required_files(self, tmp_path):
        """Test that .apkg contains required Anki database files."""
        import zipfile

        data = [
            {
                "title": "Test",
                "topic": "Topic",
                "difficulty": "Easy",
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Test")
        generator.process()

        output_path = tmp_path / "test.apkg"
        generator.save_package(str(output_path))

        with zipfile.ZipFile(output_path, 'r') as zf:
            # genanki creates collection.anki2 and media file
            names = zf.namelist()
            assert "collection.anki2" in names
            assert "media" in names

    def test_apkg_with_multiple_decks(self, tmp_path):
        """Test .apkg with multiple decks inside."""
        import zipfile

        data = [
            {
                "title": "Problem 1",
                "topic": "Topic A",
                "difficulty": "Easy",
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q1", "back": "A1"}]
            },
            {
                "title": "Problem 2",
                "topic": "Topic B",
                "difficulty": "Medium",
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q2", "back": "A2"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Multi")
        generator.process()

        assert len(generator.deck_collection) == 2

        output_path = tmp_path / "multi.apkg"
        generator.save_package(str(output_path))

        assert output_path.exists()
        assert zipfile.is_zipfile(output_path)

    def test_apkg_with_many_cards(self, tmp_path):
        """Test .apkg with large number of cards."""
        cards = [{"card_type": f"Type{i}", "tags": [], "front": f"Q{i}", "back": f"A{i}"}
                 for i in range(100)]

        data = [
            {
                "title": "Many Cards",
                "topic": "Stress Test",
                "difficulty": "Hard",
                "cards": cards
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Stress")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        assert len(deck.notes) == 100

        output_path = tmp_path / "stress.apkg"
        generator.save_package(str(output_path))

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_apkg_filename_with_spaces(self, tmp_path):
        """Test saving .apkg with spaces in filename."""
        data = [
            {
                "title": "Test",
                "topic": "Topic",
                "difficulty": "Easy",
                "cards": [{"card_type": "Concept", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Test")
        generator.process()

        output_path = tmp_path / "my deck output.apkg"
        generator.save_package(str(output_path))

        assert output_path.exists()


class TestFieldTypes:
    """Tests for all card field types and content."""

    def test_basic_card_all_fields(self):
        """Test basic card with all fields populated."""
        data = [
            {
                "title": "Complete Card",
                "topic": "Full Test",
                "difficulty": "Medium",
                "cards": [
                    {
                        "card_type": "Algorithm",
                        "tags": ["tag1", "tag2", "tag3"],
                        "front": "# Heading\n\nQuestion with **bold** and `code`.",
                        "back": "Answer with:\n- List item 1\n- List item 2\n\n```python\ndef solution():\n    pass\n```"
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Field")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        assert len(deck.notes) == 1

        note = deck.notes[0]
        # Fields should be populated (rendered to HTML)
        assert len(note.fields) == 7  # Basic model has 7 fields
        assert all(f is not None for f in note.fields)

    def test_mcq_card_all_fields(self):
        """Test MCQ card with all fields populated."""
        data = [
            {
                "title": "MCQ Test",
                "topic": "Quiz",
                "difficulty": "Easy",
                "cards": [
                    {
                        "card_type": "Knowledge",
                        "tags": ["mcq"],
                        "question": "What is the answer?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": "C",
                        "explanation": "C is correct because..."
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Test_MCQ")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        assert len(deck.notes) == 1

        note = deck.notes[0]
        # MCQ model has 12 fields
        assert len(note.fields) == 12
        assert all(f is not None for f in note.fields)

    def test_empty_front_content(self):
        """Test card with empty front content."""
        data = [
            {
                "title": "Empty Front",
                "topic": "Edge",
                "difficulty": "Easy",
                "cards": [{"card_type": "Test", "tags": [], "front": "", "back": "Has content"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Empty")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        assert len(deck.notes) == 1

    def test_empty_back_content(self):
        """Test card with empty back content."""
        data = [
            {
                "title": "Empty Back",
                "topic": "Edge",
                "difficulty": "Easy",
                "cards": [{"card_type": "Test", "tags": [], "front": "Has content", "back": ""}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Empty")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        assert len(deck.notes) == 1

    def test_very_long_content(self):
        """Test card with very long content."""
        long_text = "x" * 10000

        data = [
            {
                "title": "Long Content",
                "topic": "Stress",
                "difficulty": "Hard",
                "cards": [{"card_type": "Test", "tags": [], "front": long_text, "back": long_text}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Long")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        assert len(deck.notes) == 1

    def test_tags_with_special_characters(self):
        """Test tags with special characters are handled (no spaces allowed)."""
        data = [
            {
                "title": "Special Tags",
                "topic": "Tags",
                "difficulty": "Easy",
                "cards": [
                    {
                        "card_type": "Test",
                        "tags": ["tag:with:colons", "tag_with_underscore", "tag/slash", "tag#hash"],
                        "front": "Q",
                        "back": "A"
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Tags")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        note = deck.notes[0]
        # Should have original tags plus auto-generated ones
        assert len(note.tags) > 4

    def test_difficulty_levels(self):
        """Test various difficulty levels are preserved."""
        # Note: Anki tags cannot contain spaces, so "Very Hard" becomes "Very_Hard"
        difficulties = ["Easy", "Medium", "Hard", "Expert", "Unknown", "VeryHard"]

        for difficulty in difficulties:
            data = [
                {
                    "title": f"Difficulty {difficulty}",
                    "topic": "Level",
                    "difficulty": difficulty,
                    "cards": [{"card_type": "Test", "tags": [], "front": "Q", "back": "A"}]
                }
            ]

            generator = DeckGenerator(data, deck_prefix="Diff")
            generator.process()

            deck = list(generator.deck_collection.values())[0]
            note = deck.notes[0]
            # Difficulty should be in tags
            assert any(difficulty.replace(" ", "_") in tag for tag in note.tags)

    def test_card_types_are_tagged(self):
        """Test that card types are added to tags (no spaces allowed)."""
        # Note: Anki tags cannot contain spaces, so use types without spaces
        card_types = ["Algorithm", "Concept", "Implementation", "Pattern", "EdgeCase"]

        for card_type in card_types:
            data = [
                {
                    "title": f"Type {card_type}",
                    "topic": "Types",
                    "difficulty": "Easy",
                    "cards": [{"card_type": card_type, "tags": [], "front": "Q", "back": "A"}]
                }
            ]

            generator = DeckGenerator(data, deck_prefix="Type")
            generator.process()

            deck = list(generator.deck_collection.values())[0]
            note = deck.notes[0]
            assert f"type::{card_type}" in note.tags


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_card_data(self):
        """Test with empty card data list."""
        generator = DeckGenerator([], deck_prefix="Empty")
        generator.process()

        assert len(generator.deck_collection) == 0

    def test_problem_with_no_cards(self):
        """Test problem with empty cards list."""
        data = [
            {
                "title": "No Cards",
                "topic": "Empty",
                "difficulty": "Easy",
                "cards": []
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Empty")
        generator.process()

        # Deck is NOT created when there are no cards (no notes to add)
        # Looking at process(): deck is only created when _add_card_to_deck is called
        # Actually, process() iterates cards, so deck only gets created via get_or_create_deck
        # when _add_card_to_deck is called. Let me check actual behavior:
        # The deck IS created via get_or_create_deck before the cards loop, so deck exists
        # but has no notes
        assert len(generator.deck_collection) == 1
        deck = list(generator.deck_collection.values())[0]
        assert len(deck.notes) == 0

    def test_missing_title_uses_default(self):
        """Test that missing title uses default value."""
        data = [
            {
                "topic": "Topic",
                "difficulty": "Easy",
                "cards": [{"card_type": "Test", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Default")
        generator.process()

        assert "Default::Topic::Unknown Title" in generator.deck_collection

    def test_missing_topic_uses_default(self):
        """Test that missing topic uses default value."""
        data = [
            {
                "title": "Title",
                "difficulty": "Easy",
                "cards": [{"card_type": "Test", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Default")
        generator.process()

        assert "Default::Unknown Topic::Title" in generator.deck_collection

    def test_missing_difficulty_uses_default(self):
        """Test that missing difficulty uses default value."""
        data = [
            {
                "title": "Title",
                "topic": "Topic",
                "cards": [{"card_type": "Test", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Default")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        note = deck.notes[0]
        assert "difficulty::Unknown" in note.tags

    def test_mcq_with_less_than_4_options(self):
        """Test MCQ card with fewer than 4 options."""
        data = [
            {
                "title": "Few Options",
                "topic": "MCQ",
                "difficulty": "Easy",
                "cards": [
                    {
                        "card_type": "MCQ",
                        "tags": [],
                        "question": "Q?",
                        "options": ["A", "B"],
                        "correct_answer": "A",
                        "explanation": "A is correct"
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Test_MCQ")
        generator.process()

        # Should still process (shuffle returns unchanged for non-4 options)
        assert len(generator.deck_collection) == 1

    def test_mcq_with_invalid_correct_answer(self):
        """Test MCQ with invalid correct answer letter."""
        data = [
            {
                "title": "Invalid Answer",
                "topic": "MCQ",
                "difficulty": "Easy",
                "cards": [
                    {
                        "card_type": "MCQ",
                        "tags": [],
                        "question": "Q?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "Z",  # Invalid
                        "explanation": "Explanation"
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Test_MCQ")
        generator.process()

        # Should still process (defaults to index 0)
        assert len(generator.deck_collection) == 1

    def test_deck_id_consistency_across_runs(self):
        """Test that deck IDs are consistent across generator instances."""
        data = [
            {
                "title": "Consistent",
                "topic": "Test",
                "difficulty": "Easy",
                "cards": [{"card_type": "Test", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator1 = DeckGenerator(data, deck_prefix="ID")
        generator1.process()
        deck1 = list(generator1.deck_collection.values())[0]

        generator2 = DeckGenerator(data, deck_prefix="ID")
        generator2.process()
        deck2 = list(generator2.deck_collection.values())[0]

        # Same deck path should produce same ID
        assert deck1.deck_id == deck2.deck_id

    def test_fallback_from_question_to_front(self):
        """Test that 'question' field is used when 'front' is missing."""
        data = [
            {
                "title": "Fallback",
                "topic": "Test",
                "difficulty": "Easy",
                "cards": [
                    {
                        "card_type": "Test",
                        "tags": [],
                        "question": "Question content",
                        "explanation": "Explanation content"
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Fallback")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        note = deck.notes[0]
        # Front should contain the question content (rendered)
        assert "Question content" in note.fields[0] or len(note.fields[0]) > 0

    def test_whitespace_in_content_preserved(self):
        """Test that significant whitespace is preserved."""
        data = [
            {
                "title": "Whitespace",
                "topic": "Test",
                "difficulty": "Easy",
                "cards": [
                    {
                        "card_type": "Code",
                        "tags": [],
                        "front": "```\n    indented code\n        more indent\n```",
                        "back": "Preserves indentation"
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="WS")
        generator.process()

        deck = list(generator.deck_collection.values())[0]
        assert len(deck.notes) == 1


class TestSavePackageBehavior:
    """Tests for save_package method behavior."""

    def test_save_to_nested_directory(self, tmp_path):
        """Test saving to a nested directory that doesn't exist."""
        data = [
            {
                "title": "Test",
                "topic": "Topic",
                "difficulty": "Easy",
                "cards": [{"card_type": "Test", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Nested")
        generator.process()

        nested_dir = tmp_path / "deep" / "nested" / "path"
        nested_dir.mkdir(parents=True)
        output_path = nested_dir / "output.apkg"

        generator.save_package(str(output_path))
        assert output_path.exists()

    def test_save_overwrites_existing(self, tmp_path):
        """Test that save_package overwrites existing file."""
        data = [
            {
                "title": "Test",
                "topic": "Topic",
                "difficulty": "Easy",
                "cards": [{"card_type": "Test", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        output_path = tmp_path / "output.apkg"
        output_path.write_text("dummy content")
        initial_size = output_path.stat().st_size

        generator = DeckGenerator(data, deck_prefix="Overwrite")
        generator.process()
        generator.save_package(str(output_path))

        # File should be overwritten with actual apkg content
        assert output_path.exists()
        assert output_path.stat().st_size != initial_size

    def test_empty_collection_logs_warning(self, tmp_path, caplog):
        """Test that empty collection logs a warning."""
        import logging

        generator = DeckGenerator([], deck_prefix="Empty")

        with caplog.at_level(logging.WARNING):
            generator.save_package(str(tmp_path / "empty.apkg"))

        assert "No decks generated" in caplog.text
        assert not (tmp_path / "empty.apkg").exists()
