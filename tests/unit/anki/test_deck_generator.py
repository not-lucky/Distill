"""Tests for anki/generator.py."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from assertpy import assert_that

from src.anki.generator import DeckGenerator, load_card_data


class TestLoadCardData:
    """Tests for load_card_data function."""

    def test_load_valid_json(self, tmp_path):
        """
        Given a valid JSON file
        When load_card_data is called
        Then the data is loaded correctly
        """
        data = [{"title": "Test", "cards": []}]
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))

        result = load_card_data(str(json_file))

        assert_that(result).is_equal_to(data)

    def test_load_nonexistent_file_raises(self, tmp_path):
        """
        Given a non-existent file path
        When load_card_data is called
        Then FileNotFoundError is raised
        """
        with pytest.raises(FileNotFoundError):
            load_card_data(str(tmp_path / "missing.json"))

    def test_load_invalid_json_raises(self, tmp_path):
        """
        Given a file with invalid JSON
        When load_card_data is called
        Then JSONDecodeError is raised
        """
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
        """
        Given card data and a deck prefix
        When DeckGenerator is initialized
        Then all fields are set correctly
        """
        generator = DeckGenerator(sample_data, deck_prefix="Test")

        assert_that(generator.card_data).is_equal_to(sample_data)
        assert_that(generator.deck_prefix).is_equal_to("Test")
        assert_that(generator.deck_collection).is_equal_to({})

    def test_init_default_prefix(self, sample_data):
        """
        Given card data without explicit prefix
        When DeckGenerator is initialized
        Then default prefix 'LeetCode' is used
        """
        generator = DeckGenerator(sample_data)

        assert_that(generator.deck_prefix).is_equal_to("LeetCode")

    def test_generate_id_consistent(self, sample_data):
        """
        Given the same text
        When _generate_id is called multiple times
        Then the same ID is returned
        """
        generator = DeckGenerator(sample_data)

        id1 = generator._generate_id("test text")
        id2 = generator._generate_id("test text")

        assert_that(id1).is_equal_to(id2)
        assert_that(id1).is_instance_of(int)

    def test_generate_id_different_for_different_text(self, sample_data):
        """
        Given different text inputs
        When _generate_id is called
        Then different IDs are returned
        """
        generator = DeckGenerator(sample_data)

        id1 = generator._generate_id("text one")
        id2 = generator._generate_id("text two")

        assert_that(id1).is_not_equal_to(id2)

    def test_get_or_create_deck_creates_new(self, sample_data):
        """
        Given a deck path that doesn't exist
        When get_or_create_deck is called
        Then a new deck is created and added to collection
        """
        generator = DeckGenerator(sample_data)

        deck = generator.get_or_create_deck("Test::Category::Problem")

        assert_that(deck).is_not_none()
        assert_that(generator.deck_collection).contains_key("Test::Category::Problem")

    def test_get_or_create_deck_returns_existing(self, sample_data):
        """
        Given an existing deck path
        When get_or_create_deck is called
        Then the same deck instance is returned
        """
        generator = DeckGenerator(sample_data)

        deck1 = generator.get_or_create_deck("Test::Deck")
        deck2 = generator.get_or_create_deck("Test::Deck")

        assert_that(deck1).is_same_as(deck2)

    def test_get_prefix(self, sample_data):
        """
        Given a generator with custom prefix
        When _get_prefix is called
        Then the custom prefix is returned
        """
        generator = DeckGenerator(sample_data, deck_prefix="Custom")

        assert_that(generator._get_prefix()).is_equal_to("Custom")

    def test_build_deck_path_with_metadata(self, sample_data):
        """
        Given problem with category metadata
        When _build_deck_path is called
        Then numbered hierarchical path is returned
        """
        generator = DeckGenerator(sample_data, deck_prefix="LeetCode")

        path = generator._build_deck_path(
            problem_title="Binary Search",
            topic_name="Arrays",
            category_index=1,
            category_name="Binary Search",
            problem_index=2,
        )

        assert_that(path).is_equal_to("LeetCode::001 Binary Search::002 Binary Search")

    def test_build_deck_path_without_metadata(self, sample_data):
        """
        Given problem without category metadata (legacy)
        When _build_deck_path is called
        Then unnumbered path is returned
        """
        generator = DeckGenerator(sample_data, deck_prefix="LeetCode")

        path = generator._build_deck_path(
            problem_title="Binary Search",
            topic_name="Arrays",
        )

        assert_that(path).is_equal_to("LeetCode::Arrays::Binary Search")

    def test_process_creates_decks(self, sample_data):
        """
        Given sample data with cards
        When process is called
        Then decks are created
        """
        generator = DeckGenerator(sample_data, deck_prefix="Test")
        generator.process()

        assert_that(generator.deck_collection).is_not_empty()

    def test_process_with_category_metadata(self):
        """
        Given data with category metadata
        When process is called
        Then numbered deck path is created
        """
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

        expected_path = "LeetCode::001 Arrays::001 Two Sum"
        assert_that(generator.deck_collection).contains_key(expected_path)

    def test_save_package_empty_collection(self, sample_data, tmp_path):
        """
        Given empty deck collection
        When save_package is called
        Then no file is created
        """
        generator = DeckGenerator(sample_data)
        # Don't call process, so deck_collection is empty

        output_path = str(tmp_path / "output.apkg")
        generator.save_package(output_path)

        assert_that((tmp_path / "output.apkg").exists()).is_false()

    def test_save_package_creates_file(self, sample_data, tmp_path):
        """
        Given populated deck collection
        When save_package is called
        Then .apkg file is created
        """
        generator = DeckGenerator(sample_data)
        generator.process()

        output_path = str(tmp_path / "output.apkg")
        generator.save_package(output_path)

        assert_that((tmp_path / "output.apkg").exists()).is_true()


class TestAddCards:
    """Tests for card adding methods."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return DeckGenerator([])

    def test_add_basic_card(self, generator):
        """
        Given a deck and card data
        When _add_basic_card is called
        Then a note is added to the deck
        """
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

        assert_that(deck.notes).is_length(1)

    def test_add_mcq_card(self):
        """
        Given an MCQ deck and MCQ card data
        When _add_mcq_card is called
        Then a note is added to the deck
        """
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

        assert_that(deck.notes).is_length(1)


class TestShuffleOptions:
    """Tests for _shuffle_options method."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return DeckGenerator([])

    def test_shuffle_preserves_correct_answer(self, generator):
        """
        Given options and correct answer
        When _shuffle_options is called
        Then the correct answer mapping is preserved
        """
        options = ["A answer", "B answer", "C answer", "D answer"]
        correct = "B"

        for _ in range(10):
            shuffled, new_correct = generator._shuffle_options(options, correct)

            new_b_index = shuffled.index("B answer")
            expected_letter = ["A", "B", "C", "D"][new_b_index]
            assert_that(new_correct).is_equal_to(expected_letter)

    def test_shuffle_with_non_4_options(self, generator):
        """
        Given fewer than 4 options
        When _shuffle_options is called
        Then options are returned unchanged
        """
        options = ["A", "B", "C"]
        correct = "A"

        shuffled, new_correct = generator._shuffle_options(options, correct)

        assert_that(shuffled).is_equal_to(options)
        assert_that(new_correct).is_equal_to(correct)

    def test_shuffle_returns_4_options(self, generator):
        """
        Given 4 options
        When _shuffle_options is called
        Then 4 options are returned
        """
        options = ["A", "B", "C", "D"]
        correct = "A"

        shuffled, _ = generator._shuffle_options(options, correct)

        assert_that(shuffled).is_length(4)


class TestMCQDetection:
    """Tests for MCQ mode detection."""

    def test_mcq_prefix_detection(self):
        """
        Given MCQ prefix in deck_prefix
        When process is called
        Then MCQ cards are added
        """
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

        assert_that(generator.deck_collection).is_not_empty()

    def test_non_mcq_prefix_uses_basic(self):
        """
        Given non-MCQ prefix
        When process is called with cards having options
        Then basic card format is used
        """
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
                        "options": ["A", "B", "C", "D"],
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="LeetCode")
        generator.process()

        assert_that(generator.deck_collection).is_not_empty()


class TestHierarchicalDeckStructure:
    """Tests for hierarchical deck creation and naming."""

    def test_deep_nested_deck_structure(self):
        """
        Given multiple problems with category metadata
        When process is called
        Then deeply nested deck hierarchies are created
        """
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

        assert_that(generator.deck_collection).is_length(3)
        assert_that(generator.deck_collection).contains_key("LeetCode::001 Algorithms::001 Problem 1")
        assert_that(generator.deck_collection).contains_key("LeetCode::001 Algorithms::002 Problem 2")
        assert_that(generator.deck_collection).contains_key("LeetCode::002 Data Structures::001 Problem 3")

    def test_multiple_cards_per_problem(self):
        """
        Given a problem with multiple cards
        When process is called
        Then one deck with multiple notes is created
        """
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

        assert_that(generator.deck_collection).is_length(1)
        deck_path = "Test::Testing::Multi-Card Problem"
        assert_that(generator.deck_collection).contains_key(deck_path)
        assert_that(generator.deck_collection[deck_path].notes).is_length(3)

    def test_special_characters_in_deck_path(self):
        """
        Given problem with special characters in title/topic
        When process is called
        Then deck path handles special characters
        """
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

        expected_path = "LeetCode::Arrays & Hashing::Two Sum (Easy)"
        assert_that(generator.deck_collection).contains_key(expected_path)

    def test_unicode_in_deck_path(self):
        """
        Given problem with unicode characters
        When process is called
        Then deck path handles unicode correctly
        """
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
        assert_that(generator.deck_collection).contains_key(expected_path)

    def test_large_category_and_problem_indices(self):
        """
        Given large category and problem indices
        When process is called
        Then indices are formatted correctly
        """
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
        assert_that(generator.deck_collection).contains_key(expected_path)

    def test_mixed_metadata_and_legacy_problems(self):
        """
        Given problems with and without category metadata
        When process is called
        Then both formats are handled correctly
        """
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

        assert_that(generator.deck_collection).contains_key("Mixed::001 Category::001 With Metadata")
        assert_that(generator.deck_collection).contains_key("Mixed::Cat2::Without Metadata")


class TestApkgFileValidity:
    """Tests for .apkg file generation and validity."""

    def test_apkg_file_is_valid_zip(self, tmp_path):
        """
        Given processed card data
        When save_package is called
        Then a valid zip file is created
        """
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

        assert_that(zipfile.is_zipfile(output_path)).is_true()

    def test_apkg_contains_required_files(self, tmp_path):
        """
        Given processed card data
        When save_package is called
        Then .apkg contains required Anki database files
        """
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
            names = zf.namelist()
            assert_that(names).contains("collection.anki2")
            assert_that(names).contains("media")

    def test_apkg_with_multiple_decks(self, tmp_path):
        """
        Given multiple problems
        When save_package is called
        Then all decks are included in .apkg
        """
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

        assert_that(generator.deck_collection).is_length(2)

        output_path = tmp_path / "multi.apkg"
        generator.save_package(str(output_path))

        assert_that(output_path.exists()).is_true()
        assert_that(zipfile.is_zipfile(output_path)).is_true()

    def test_apkg_with_many_cards(self, tmp_path):
        """
        Given a problem with many cards
        When save_package is called
        Then all cards are included
        """
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
        assert_that(deck.notes).is_length(100)

        output_path = tmp_path / "stress.apkg"
        generator.save_package(str(output_path))

        assert_that(output_path.exists()).is_true()
        assert_that(output_path.stat().st_size).is_greater_than(0)

    def test_apkg_filename_with_spaces(self, tmp_path):
        """
        Given a filename with spaces
        When save_package is called
        Then the file is created successfully
        """
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

        assert_that(output_path.exists()).is_true()


class TestFieldTypes:
    """Tests for all card field types and content."""

    def test_basic_card_all_fields(self):
        """
        Given a card with all fields populated
        When process is called
        Then all fields are stored in the note
        """
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
        assert_that(deck.notes).is_length(1)

        note = deck.notes[0]
        assert_that(note.fields).is_length(7)
        assert_that(all(f is not None for f in note.fields)).is_true()

    def test_mcq_card_all_fields(self):
        """
        Given an MCQ card with all fields populated
        When process is called
        Then all MCQ fields are stored in the note
        """
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
        assert_that(deck.notes).is_length(1)

        note = deck.notes[0]
        assert_that(note.fields).is_length(12)
        assert_that(all(f is not None for f in note.fields)).is_true()

    def test_empty_front_content(self):
        """
        Given a card with empty front content
        When process is called
        Then the card is still created
        """
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
        assert_that(deck.notes).is_length(1)

    def test_empty_back_content(self):
        """
        Given a card with empty back content
        When process is called
        Then the card is still created
        """
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
        assert_that(deck.notes).is_length(1)

    def test_very_long_content(self):
        """
        Given a card with very long content
        When process is called
        Then the card is created successfully
        """
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
        assert_that(deck.notes).is_length(1)

    def test_tags_with_special_characters(self):
        """
        Given tags with special characters
        When process is called
        Then tags are handled correctly
        """
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
        assert_that(len(note.tags)).is_greater_than(4)

    def test_difficulty_levels(self):
        """
        Given various difficulty levels
        When process is called
        Then difficulty is included in tags
        """
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
            assert_that(any(difficulty.replace(" ", "_") in tag for tag in note.tags)).is_true()

    def test_card_types_are_tagged(self):
        """
        Given various card types
        When process is called
        Then card types are added to tags
        """
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
            assert_that(note.tags).contains(f"type::{card_type}")


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_card_data(self):
        """
        Given empty card data list
        When process is called
        Then no decks are created
        """
        generator = DeckGenerator([], deck_prefix="Empty")
        generator.process()

        assert_that(generator.deck_collection).is_empty()

    def test_problem_with_no_cards(self):
        """
        Given a problem with empty cards list
        When process is called
        Then deck is created but has no notes
        """
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

        assert_that(generator.deck_collection).is_length(1)
        deck = list(generator.deck_collection.values())[0]
        assert_that(deck.notes).is_empty()

    def test_missing_title_uses_default(self):
        """
        Given a problem without title
        When process is called
        Then default title is used
        """
        data = [
            {
                "topic": "Topic",
                "difficulty": "Easy",
                "cards": [{"card_type": "Test", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Default")
        generator.process()

        assert_that(generator.deck_collection).contains_key("Default::Topic::Unknown Title")

    def test_missing_topic_uses_default(self):
        """
        Given a problem without topic
        When process is called
        Then default topic is used
        """
        data = [
            {
                "title": "Title",
                "difficulty": "Easy",
                "cards": [{"card_type": "Test", "tags": [], "front": "Q", "back": "A"}]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Default")
        generator.process()

        assert_that(generator.deck_collection).contains_key("Default::Unknown Topic::Title")

    def test_missing_difficulty_uses_default(self):
        """
        Given a problem without difficulty
        When process is called
        Then default difficulty is used in tags
        """
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
        assert_that(note.tags).contains("difficulty::Unknown")

    def test_mcq_with_less_than_4_options(self):
        """
        Given an MCQ card with fewer than 4 options
        When process is called
        Then the card is still processed
        """
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

        assert_that(generator.deck_collection).is_length(1)

    def test_mcq_with_invalid_correct_answer(self):
        """
        Given an MCQ with invalid correct answer letter
        When process is called
        Then the card is still processed
        """
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
                        "correct_answer": "Z",
                        "explanation": "Explanation"
                    }
                ]
            }
        ]

        generator = DeckGenerator(data, deck_prefix="Test_MCQ")
        generator.process()

        assert_that(generator.deck_collection).is_length(1)

    def test_deck_id_consistency_across_runs(self):
        """
        Given the same data across multiple generator instances
        When process is called
        Then deck IDs are consistent
        """
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

        assert_that(deck1.deck_id).is_equal_to(deck2.deck_id)

    def test_fallback_from_question_to_front(self):
        """
        Given a card with 'question' field but no 'front'
        When process is called
        Then 'question' is used as front content
        """
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
        # Front should contain the question content (rendered) or be non-empty
        front_field = note.fields[0]
        assert_that(front_field).is_not_empty()

    def test_whitespace_in_content_preserved(self):
        """
        Given a card with significant whitespace
        When process is called
        Then the card is created successfully
        """
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
        assert_that(deck.notes).is_length(1)


class TestSavePackageBehavior:
    """Tests for save_package method behavior."""

    def test_save_to_nested_directory(self, tmp_path):
        """
        Given a nested directory path
        When save_package is called
        Then the file is saved successfully
        """
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
        assert_that(output_path.exists()).is_true()

    def test_save_overwrites_existing(self, tmp_path):
        """
        Given an existing file
        When save_package is called
        Then the file is overwritten
        """
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

        assert_that(output_path.exists()).is_true()
        assert_that(output_path.stat().st_size).is_not_equal_to(initial_size)

    def test_empty_collection_logs_warning(self, tmp_path, caplog):
        """
        Given an empty deck collection
        When save_package is called
        Then a warning is logged
        """
        import logging

        generator = DeckGenerator([], deck_prefix="Empty")

        with caplog.at_level(logging.WARNING):
            generator.save_package(str(tmp_path / "empty.apkg"))

        assert_that(caplog.text).contains("No decks generated")
        assert_that((tmp_path / "empty.apkg").exists()).is_false()
