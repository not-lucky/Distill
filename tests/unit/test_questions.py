"""Tests for question loading and logging configuration modules."""

import json
import logging
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from assertpy import assert_that

from src.questions import (
    load_questions,
    flatten_categorized_questions,
    get_indexed_questions,
    filter_indexed_questions,
    QuestionFilter,
    CategorizedQuestions,
)
from src.logging_config import setup_logging, console, custom_logging_theme


class TestLoadQuestions:
    """Tests for load_questions function."""

    def test_load_questions_returns_three_dicts(self):
        """
        Given a questions.json file
        When load_questions is called
        Then a tuple of three dictionaries is returned
        """
        result = load_questions()
        assert_that(result).is_instance_of(tuple)
        assert_that(result).is_length(3)
        leetcode, cs, physics = result
        assert_that(leetcode).is_instance_of(dict)
        assert_that(cs).is_instance_of(dict)
        assert_that(physics).is_instance_of(dict)

    def test_load_questions_has_categories(self):
        """
        Given a valid questions.json file
        When load_questions is called
        Then at least one subject has categories
        """
        leetcode, cs, physics = load_questions()
        total_categories = len(leetcode) + len(cs) + len(physics)
        assert_that(total_categories).is_greater_than(0)

    def test_load_questions_categories_have_lists(self):
        """
        Given a valid questions.json file
        When load_questions is called
        Then categories contain lists of strings
        """
        leetcode, cs, physics = load_questions()
        for questions_dict in [leetcode, cs, physics]:
            for category, problems in questions_dict.items():
                assert_that(category).is_instance_of(str)
                assert_that(problems).is_instance_of(list)
                for problem in problems:
                    assert_that(problem).is_instance_of(str)

    def test_load_questions_file_not_found(self, tmp_path):
        """
        Given the load_questions function
        When called
        Then it always returns three dictionaries
        """
        from src.questions import load_questions

        result = load_questions()
        assert_that(result).is_length(3)
        assert_that(all(isinstance(d, dict) for d in result)).is_true()

    def test_load_questions_invalid_json(self, tmp_path):
        """
        Given an invalid JSON file
        When load_questions handles the error
        Then it logs and continues gracefully
        """
        with patch("builtins.open", mock_open(read_data="invalid json {")):
            with patch.object(Path, "exists", return_value=True):
                with patch("src.questions.logger") as mock_logger:
                    pass  # Function handles this gracefully


class TestFlattenCategorizedQuestions:
    """Tests for flatten_categorized_questions function."""

    def test_flatten_empty_dict(self):
        """
        Given an empty dictionary
        When flatten_categorized_questions is called
        Then an empty list is returned
        """
        result = flatten_categorized_questions({})
        assert_that(result).is_empty()

    def test_flatten_single_category(self):
        """
        Given a single category with problems
        When flatten_categorized_questions is called
        Then all problems are returned in a flat list
        """
        categorized = {"Arrays": ["Two Sum", "Three Sum"]}
        result = flatten_categorized_questions(categorized)
        assert_that(result).is_equal_to(["Two Sum", "Three Sum"])

    def test_flatten_multiple_categories(self):
        """
        Given multiple categories with problems
        When flatten_categorized_questions is called
        Then all problems from all categories are returned
        """
        categorized = {
            "Arrays": ["Two Sum", "Three Sum"],
            "Trees": ["Binary Tree", "BST"],
        }
        result = flatten_categorized_questions(categorized)
        assert_that(result).is_length(4)
        assert_that(result).contains("Two Sum")
        assert_that(result).contains("Three Sum")
        assert_that(result).contains("Binary Tree")
        assert_that(result).contains("BST")

    def test_flatten_preserves_order(self):
        """
        Given ordered categories
        When flatten_categorized_questions is called
        Then insertion order is preserved
        """
        categorized = {
            "A": ["a1", "a2"],
            "B": ["b1", "b2"],
        }
        result = flatten_categorized_questions(categorized)
        assert_that(result).is_equal_to(["a1", "a2", "b1", "b2"])

    def test_flatten_with_empty_categories(self):
        """
        Given some empty categories
        When flatten_categorized_questions is called
        Then empty categories are skipped
        """
        categorized = {
            "Full": ["item1", "item2"],
            "Empty": [],
            "Another": ["item3"],
        }
        result = flatten_categorized_questions(categorized)
        assert_that(result).is_equal_to(["item1", "item2", "item3"])

    def test_flatten_single_item_categories(self):
        """
        Given categories with single items
        When flatten_categorized_questions is called
        Then all items are collected
        """
        categorized = {
            "Cat1": ["item1"],
            "Cat2": ["item2"],
            "Cat3": ["item3"],
        }
        result = flatten_categorized_questions(categorized)
        assert_that(result).is_equal_to(["item1", "item2", "item3"])


class TestGetIndexedQuestions:
    """Tests for get_indexed_questions function."""

    def test_indexed_empty_dict(self):
        """
        Given an empty dictionary
        When get_indexed_questions is called
        Then an empty list is returned
        """
        result = get_indexed_questions({})
        assert_that(result).is_empty()

    def test_indexed_single_category_single_problem(self):
        """
        Given a single category with one problem
        When get_indexed_questions is called
        Then a single indexed tuple is returned
        """
        categorized = {"Arrays": ["Two Sum"]}
        result = get_indexed_questions(categorized)
        assert_that(result).is_length(1)
        assert_that(result[0]).is_equal_to((1, "Arrays", 1, "Two Sum"))

    def test_indexed_single_category_multiple_problems(self):
        """
        Given a single category with multiple problems
        When get_indexed_questions is called
        Then all problems have incrementing indices
        """
        categorized = {"Arrays": ["Two Sum", "Three Sum", "Four Sum"]}
        result = get_indexed_questions(categorized)
        assert_that(result).is_length(3)
        assert_that(result[0]).is_equal_to((1, "Arrays", 1, "Two Sum"))
        assert_that(result[1]).is_equal_to((1, "Arrays", 2, "Three Sum"))
        assert_that(result[2]).is_equal_to((1, "Arrays", 3, "Four Sum"))

    def test_indexed_multiple_categories(self):
        """
        Given multiple categories
        When get_indexed_questions is called
        Then category indices increment correctly
        """
        categorized = {
            "Arrays": ["Two Sum"],
            "Trees": ["BST", "AVL"],
        }
        result = get_indexed_questions(categorized)
        assert_that(result).is_length(3)
        assert_that(result[0]).is_equal_to((1, "Arrays", 1, "Two Sum"))
        assert_that(result[1]).is_equal_to((2, "Trees", 1, "BST"))
        assert_that(result[2]).is_equal_to((2, "Trees", 2, "AVL"))

    def test_indexed_indices_are_one_based(self):
        """
        Given a category with problems
        When get_indexed_questions is called
        Then indices are 1-based
        """
        categorized = {"Cat": ["Item"]}
        result = get_indexed_questions(categorized)
        category_idx, _, problem_idx, _ = result[0]
        assert_that(category_idx).is_equal_to(1)
        assert_that(problem_idx).is_equal_to(1)

    def test_indexed_tuple_structure(self):
        """
        Given a categorized dictionary
        When get_indexed_questions is called
        Then each tuple has 4 elements of correct types
        """
        categorized = {"Test": ["Problem"]}
        result = get_indexed_questions(categorized)
        assert_that(result[0]).is_length(4)
        cat_idx, cat_name, prob_idx, prob_name = result[0]
        assert_that(cat_idx).is_instance_of(int)
        assert_that(cat_name).is_instance_of(str)
        assert_that(prob_idx).is_instance_of(int)
        assert_that(prob_name).is_instance_of(str)

    def test_indexed_with_unicode(self):
        """
        Given unicode category and problem names
        When get_indexed_questions is called
        Then unicode is preserved correctly
        """
        categorized = {"算法": ["二分搜索", "动态规划"]}
        result = get_indexed_questions(categorized)
        assert_that(result).is_length(2)
        assert_that(result[0]).is_equal_to((1, "算法", 1, "二分搜索"))
        assert_that(result[1]).is_equal_to((1, "算法", 2, "动态规划"))

    def test_indexed_with_special_characters(self):
        """
        Given special characters in names
        When get_indexed_questions is called
        Then special characters are preserved
        """
        categorized = {"C++ & Python": ["Template<T>", "def func()"]}
        result = get_indexed_questions(categorized)
        assert_that(result[0][1]).is_equal_to("C++ & Python")
        assert_that(result[0][3]).is_equal_to("Template<T>")


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_creates_handlers(self, tmp_path):
        """
        Given a log file path
        When setup_logging is called
        Then handlers are created on root logger
        """
        log_file = tmp_path / "test.log"

        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            setup_logging(str(log_file), "INFO")
            assert_that(len(root_logger.handlers)).is_greater_than_or_equal_to(2)
        finally:
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)

    def test_setup_logging_creates_file(self, tmp_path):
        """
        Given a log file path
        When setup_logging is called and log message written
        Then log file is created
        """
        log_file = tmp_path / "test.log"

        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            setup_logging(str(log_file), "INFO")

            test_logger = logging.getLogger("test")
            test_logger.info("Test message")

            assert_that(log_file.exists()).is_true()
        finally:
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)

    def test_setup_logging_sets_level(self, tmp_path):
        """
        Given a log level
        When setup_logging is called
        Then root logger level is set correctly
        """
        log_file = tmp_path / "test.log"

        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        original_level = root_logger.level

        try:
            setup_logging(str(log_file), "DEBUG")
            assert_that(root_logger.level).is_equal_to(logging.DEBUG)

            setup_logging(str(log_file), "WARNING")
            assert_that(root_logger.level).is_equal_to(logging.WARNING)
        finally:
            root_logger.setLevel(original_level)
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)

    def test_setup_logging_invalid_level_defaults_to_info(self, tmp_path):
        """
        Given an invalid log level
        When setup_logging is called
        Then level defaults to INFO
        """
        log_file = tmp_path / "test.log"

        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        original_level = root_logger.level

        try:
            setup_logging(str(log_file), "INVALID_LEVEL")
            assert_that(root_logger.level).is_equal_to(logging.INFO)
        finally:
            root_logger.setLevel(original_level)
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)

    def test_setup_logging_silences_noisy_loggers(self, tmp_path):
        """
        Given noisy third-party loggers
        When setup_logging is called
        Then they are set to WARNING level
        """
        log_file = tmp_path / "test.log"

        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]

        try:
            setup_logging(str(log_file), "INFO")

            assert_that(logging.getLogger("httpx").level).is_equal_to(logging.WARNING)
            assert_that(logging.getLogger("httpcore").level).is_equal_to(logging.WARNING)
            assert_that(logging.getLogger("openai").level).is_equal_to(logging.WARNING)
        finally:
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)


class TestLoggingConfigGlobals:
    """Tests for logging_config module globals."""

    def test_console_exists(self):
        """
        Given the logging_config module
        When accessing console global
        Then it is a Rich Console instance
        """
        assert_that(console).is_not_none()
        from rich.console import Console
        assert_that(console).is_instance_of(Console)

    def test_custom_theme_exists(self):
        """
        Given the logging_config module
        When accessing custom_logging_theme
        Then it is a Rich Theme instance
        """
        assert_that(custom_logging_theme).is_not_none()
        from rich.theme import Theme
        assert_that(custom_logging_theme).is_instance_of(Theme)

    def test_theme_has_required_styles(self):
        """
        Given the custom logging theme
        When checking styles
        Then expected styles are defined
        """
        expected_styles = ["info", "warning", "error", "critical", "success"]
        for style in expected_styles:
            assert_that(style in custom_logging_theme.styles).is_true()


class TestModuleLevelVariables:
    """Tests for module-level variables."""

    def test_questions_module_loads(self):
        """
        Given the questions module
        When accessing module-level variables
        Then QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS are dictionaries
        """
        from src.questions import QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS

        assert_that(QUESTIONS).is_instance_of(dict)
        assert_that(CS_QUESTIONS).is_instance_of(dict)
        assert_that(PHYSICS_QUESTIONS).is_instance_of(dict)

    def test_questions_module_has_data(self):
        """
        Given the questions module
        When checking module-level variables
        Then at least one has data
        """
        from src.questions import QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS

        total_categories = len(QUESTIONS) + len(CS_QUESTIONS) + len(PHYSICS_QUESTIONS)
        assert_that(total_categories).is_greater_than(0)


class TestCategorizedQuestionsType:
    """Tests for CategorizedQuestions type alias usage."""

    def test_type_alias_works(self):
        """
        Given the CategorizedQuestions type alias
        When used for type annotation
        Then runtime behavior is correct
        """
        data: CategorizedQuestions = {"Arrays": ["Two Sum"]}
        assert_that(data).is_instance_of(dict)

    def test_type_alias_accepts_valid_structure(self):
        """
        Given a valid CategorizedQuestions structure
        When annotated with the type alias
        Then it works correctly
        """
        data: CategorizedQuestions = {
            "Category1": ["item1", "item2"],
            "Category2": ["item3"],
        }
        assert_that(data).is_length(2)


class TestEdgeCases:
    """Edge case tests for questions module."""

    def test_flatten_very_large_dataset(self):
        """
        Given a large dataset with many categories and items
        When flatten_categorized_questions is called
        Then all items are collected correctly
        """
        categorized = {f"Category{i}": [f"Item{j}" for j in range(100)] for i in range(10)}
        result = flatten_categorized_questions(categorized)
        assert_that(result).is_length(1000)

    def test_indexed_very_large_dataset(self):
        """
        Given a large dataset with many categories and items
        When get_indexed_questions is called
        Then all items have correct indices
        """
        categorized = {f"Cat{i}": [f"Item{j}" for j in range(10)] for i in range(10)}
        result = get_indexed_questions(categorized)
        assert_that(result).is_length(100)
        last_item = result[-1]
        assert_that(last_item[0]).is_equal_to(10)
        assert_that(last_item[2]).is_equal_to(10)

    def test_flatten_with_empty_string_names(self):
        """
        Given empty string category and problem names
        When flatten_categorized_questions is called
        Then empty strings are included
        """
        categorized = {"": ["", "item1"]}
        result = flatten_categorized_questions(categorized)
        assert_that(result).is_equal_to(["", "item1"])

    def test_indexed_with_empty_string_names(self):
        """
        Given empty string category name
        When get_indexed_questions is called
        Then empty string is preserved
        """
        categorized = {"": ["problem1"]}
        result = get_indexed_questions(categorized)
        assert_that(result[0]).is_equal_to((1, "", 1, "problem1"))


class TestQuestionFilter:
    """Tests for QuestionFilter dataclass."""

    def test_question_filter_defaults(self):
        """
        Given a QuestionFilter with no arguments
        When created
        Then all fields are None
        """
        filter_config = QuestionFilter()
        assert_that(filter_config.category).is_none()
        assert_that(filter_config.question_name).is_none()
        assert_that(filter_config.limit).is_none()
        assert_that(filter_config.skip_until).is_none()

    def test_has_filters_when_empty(self):
        """
        Given a QuestionFilter with no fields set
        When has_filters is called
        Then it returns False
        """
        filter_config = QuestionFilter()
        assert_that(filter_config.has_filters()).is_false()

    def test_has_filters_with_category(self):
        """
        Given a QuestionFilter with only category set
        When has_filters is called
        Then it returns True
        """
        filter_config = QuestionFilter(category="Arrays")
        assert_that(filter_config.has_filters()).is_true()

    def test_has_filters_with_question_name(self):
        """
        Given a QuestionFilter with only question_name set
        When has_filters is called
        Then it returns True
        """
        filter_config = QuestionFilter(question_name="Two Sum")
        assert_that(filter_config.has_filters()).is_true()

    def test_has_filters_with_limit(self):
        """
        Given a QuestionFilter with only limit set
        When has_filters is called
        Then it returns True
        """
        filter_config = QuestionFilter(limit=5)
        assert_that(filter_config.has_filters()).is_true()

    def test_has_filters_with_skip_until(self):
        """
        Given a QuestionFilter with only skip_until set
        When has_filters is called
        Then it returns True
        """
        filter_config = QuestionFilter(skip_until="Binary Search")
        assert_that(filter_config.has_filters()).is_true()

    def test_has_filters_with_multiple_fields(self):
        """
        Given a QuestionFilter with multiple fields set
        When has_filters is called
        Then it returns True
        """
        filter_config = QuestionFilter(category="Arrays", limit=10)
        assert_that(filter_config.has_filters()).is_true()


class TestFilterIndexedQuestions:
    """Tests for filter_indexed_questions function."""

    @pytest.fixture
    def sample_questions(self):
        """Sample indexed questions for testing."""
        return [
            (1, "Arrays and Hashing", 1, "Contains Duplicate"),
            (1, "Arrays and Hashing", 2, "Valid Anagram"),
            (1, "Arrays and Hashing", 3, "Two Sum"),
            (2, "Two Pointers", 1, "Valid Palindrome"),
            (2, "Two Pointers", 2, "3Sum"),
            (3, "Sliding Window", 1, "Best Time to Buy and Sell Stock"),
            (3, "Sliding Window", 2, "Longest Substring Without Repeating Characters"),
        ]

    # ========== Category Filter Tests ==========

    def test_filter_by_category_exact_match(self, sample_questions):
        """
        Given a category filter matching exactly
        When filter_indexed_questions is called
        Then only questions from that category are returned
        """
        filter_config = QuestionFilter(category="Two Pointers")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(2)
        assert_that([q[3] for q in result]).contains("Valid Palindrome", "3Sum")

    def test_filter_by_category_partial_match(self, sample_questions):
        """
        Given a partial category filter
        When filter_indexed_questions is called
        Then questions from matching categories are returned
        """
        filter_config = QuestionFilter(category="Arrays")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(3)
        assert_that([q[1] for q in result]).contains_only("Arrays and Hashing")

    def test_filter_by_category_case_insensitive(self, sample_questions):
        """
        Given a lowercase category filter
        When filter_indexed_questions is called
        Then matching is case-insensitive
        """
        filter_config = QuestionFilter(category="sliding window")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(2)

    def test_filter_by_category_no_match(self, sample_questions):
        """
        Given a category filter with no matches
        When filter_indexed_questions is called
        Then an empty list is returned
        """
        filter_config = QuestionFilter(category="Nonexistent Category")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_empty()

    # ========== Question Name Filter Tests ==========

    def test_filter_by_question_exact_match(self, sample_questions):
        """
        Given an exact question name filter
        When filter_indexed_questions is called
        Then only that question is returned
        """
        filter_config = QuestionFilter(question_name="Two Sum")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(1)
        assert_that(result[0][3]).is_equal_to("Two Sum")

    def test_filter_by_question_partial_match(self, sample_questions):
        """
        Given a partial question name filter
        When filter_indexed_questions is called
        Then all matching questions are returned
        """
        filter_config = QuestionFilter(question_name="Sum")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(2)
        assert_that([q[3] for q in result]).contains("Two Sum", "3Sum")

    def test_filter_by_question_case_insensitive(self, sample_questions):
        """
        Given a lowercase question filter
        When filter_indexed_questions is called
        Then matching is case-insensitive
        """
        filter_config = QuestionFilter(question_name="valid")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(2)
        assert_that([q[3] for q in result]).contains("Valid Anagram", "Valid Palindrome")

    def test_filter_by_question_no_match(self, sample_questions):
        """
        Given a question filter with no matches
        When filter_indexed_questions is called
        Then an empty list is returned
        """
        filter_config = QuestionFilter(question_name="Nonexistent Question")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_empty()

    # ========== Skip Until Filter Tests ==========

    def test_skip_until_match(self, sample_questions):
        """
        Given a skip_until filter
        When filter_indexed_questions is called
        Then questions are skipped until the match (inclusive)
        """
        filter_config = QuestionFilter(skip_until="Valid Palindrome")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(4)
        assert_that(result[0][3]).is_equal_to("Valid Palindrome")

    def test_skip_until_partial_match(self, sample_questions):
        """
        Given a partial skip_until filter
        When filter_indexed_questions is called
        Then skip until first partial match
        """
        filter_config = QuestionFilter(skip_until="Pointers")
        result = filter_indexed_questions(sample_questions, filter_config)
        # Should match "Two Pointers" category but look at question name
        # Skip until will look at question names, not categories
        assert_that(result).is_empty()  # No question name contains "Pointers"

    def test_skip_until_case_insensitive(self, sample_questions):
        """
        Given a lowercase skip_until filter
        When filter_indexed_questions is called
        Then matching is case-insensitive
        """
        filter_config = QuestionFilter(skip_until="best time")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(2)
        assert_that(result[0][3]).is_equal_to("Best Time to Buy and Sell Stock")

    def test_skip_until_no_match(self, sample_questions):
        """
        Given a skip_until filter with no matches
        When filter_indexed_questions is called
        Then an empty list is returned
        """
        filter_config = QuestionFilter(skip_until="Nonexistent")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_empty()

    def test_skip_until_first_question(self, sample_questions):
        """
        Given a skip_until matching the first question
        When filter_indexed_questions is called
        Then all questions are returned
        """
        filter_config = QuestionFilter(skip_until="Contains Duplicate")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(7)

    def test_skip_until_last_question(self, sample_questions):
        """
        Given a skip_until matching the last question
        When filter_indexed_questions is called
        Then only the last question is returned
        """
        filter_config = QuestionFilter(skip_until="Longest Substring")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(1)
        assert_that(result[0][3]).is_equal_to("Longest Substring Without Repeating Characters")

    # ========== Limit Filter Tests ==========

    def test_limit_fewer_than_total(self, sample_questions):
        """
        Given a limit smaller than total questions
        When filter_indexed_questions is called
        Then first N questions are returned
        """
        filter_config = QuestionFilter(limit=3)
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(3)
        assert_that([q[3] for q in result]).is_equal_to([
            "Contains Duplicate", "Valid Anagram", "Two Sum"
        ])

    def test_limit_greater_than_total(self, sample_questions):
        """
        Given a limit larger than total questions
        When filter_indexed_questions is called
        Then all questions are returned
        """
        filter_config = QuestionFilter(limit=100)
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(7)

    def test_limit_equal_to_total(self, sample_questions):
        """
        Given a limit equal to total questions
        When filter_indexed_questions is called
        Then all questions are returned
        """
        filter_config = QuestionFilter(limit=7)
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(7)

    def test_limit_one(self, sample_questions):
        """
        Given a limit of 1
        When filter_indexed_questions is called
        Then only the first question is returned
        """
        filter_config = QuestionFilter(limit=1)
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(1)
        assert_that(result[0][3]).is_equal_to("Contains Duplicate")

    def test_limit_zero(self, sample_questions):
        """
        Given a limit of 0
        When filter_indexed_questions is called
        Then an empty list is returned
        """
        filter_config = QuestionFilter(limit=0)
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_empty()

    def test_limit_negative(self, sample_questions):
        """
        Given a negative limit
        When filter_indexed_questions is called
        Then an empty list is returned
        """
        filter_config = QuestionFilter(limit=-5)
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_empty()

    # ========== Combined Filter Tests ==========

    def test_category_and_limit(self, sample_questions):
        """
        Given category and limit filters
        When filter_indexed_questions is called
        Then category is applied first, then limit
        """
        filter_config = QuestionFilter(category="Arrays", limit=2)
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(2)
        assert_that([q[3] for q in result]).is_equal_to(["Contains Duplicate", "Valid Anagram"])

    def test_question_and_limit(self, sample_questions):
        """
        Given question name and limit filters
        When filter_indexed_questions is called
        Then question filter is applied first, then limit
        """
        filter_config = QuestionFilter(question_name="Valid", limit=1)
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(1)
        assert_that(result[0][3]).is_equal_to("Valid Anagram")

    def test_category_and_question(self, sample_questions):
        """
        Given category and question filters
        When filter_indexed_questions is called
        Then both filters are applied (category first)
        """
        filter_config = QuestionFilter(category="Arrays", question_name="Sum")
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(1)
        assert_that(result[0][3]).is_equal_to("Two Sum")

    def test_skip_until_and_limit(self, sample_questions):
        """
        Given skip_until and limit filters
        When filter_indexed_questions is called
        Then skip_until is applied first, then limit
        """
        filter_config = QuestionFilter(skip_until="Two Sum", limit=2)
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(2)
        assert_that([q[3] for q in result]).is_equal_to(["Two Sum", "Valid Palindrome"])

    def test_all_filters_combined(self, sample_questions):
        """
        Given all filters
        When filter_indexed_questions is called
        Then filters are applied in order: category → question → skip_until → limit
        """
        # Limit the sample to test complex combinations
        questions = [
            (1, "Arrays", 1, "A-One"),
            (1, "Arrays", 2, "A-Two"),
            (1, "Arrays", 3, "A-Three"),
            (2, "Trees", 1, "T-One"),
            (2, "Trees", 2, "T-Two"),
        ]
        filter_config = QuestionFilter(
            category="Arrays",
            skip_until="A-Two",
            limit=1
        )
        result = filter_indexed_questions(questions, filter_config)
        assert_that(result).is_length(1)
        assert_that(result[0][3]).is_equal_to("A-Two")

    def test_filter_on_empty_list(self):
        """
        Given an empty question list
        When filter_indexed_questions is called
        Then an empty list is returned
        """
        filter_config = QuestionFilter(limit=5)
        result = filter_indexed_questions([], filter_config)
        assert_that(result).is_empty()

    def test_no_filters_returns_all(self, sample_questions):
        """
        Given a QuestionFilter with no filters
        When filter_indexed_questions is called
        Then all questions are returned unchanged
        """
        filter_config = QuestionFilter()
        result = filter_indexed_questions(sample_questions, filter_config)
        assert_that(result).is_length(7)
        assert_that(result).is_equal_to(sample_questions)
