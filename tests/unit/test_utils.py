"""Tests for utility functions in src/utils.py.

Assertpy Conversion Pattern Guide
=================================
This file demonstrates the assertpy fluent assertion style and BDD docstrings
used throughout the test suite.

Assertion Conversion Examples:
    # Equality
    assert result == expected          -> assert_that(result).is_equal_to(expected)
    assert result != expected          -> assert_that(result).is_not_equal_to(expected)

    # String containment
    assert "foo" in result             -> assert_that(result).contains("foo")
    assert result.startswith("x")      -> assert_that(result).starts_with("x")
    assert result.endswith("x")        -> assert_that(result).ends_with("x")

    # Length/size
    assert len(items) == 5             -> assert_that(items).is_length(5)
    assert len(items) > 0              -> assert_that(items).is_not_empty()

    # Boolean/None
    assert result is True              -> assert_that(result).is_true()
    assert result is None              -> assert_that(result).is_none()
    assert result is not None          -> assert_that(result).is_not_none()

    # Collections
    assert item in collection          -> assert_that(collection).contains(item)
    assert len(collection) == 0        -> assert_that(collection).is_empty()

    # Type checking
    assert isinstance(obj, Type)       -> assert_that(obj).is_instance_of(Type)

    # Exception checking (keep pytest.raises, assertpy integrates well)

BDD Docstring Format:
    \"\"\"
    Given <precondition/context>
    When <action is taken>
    Then <expected result>
    \"\"\"
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch
import datetime

from assertpy import assert_that

from src.utils import sanitize_filename, strip_json_block, save_final_deck


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_simple_string(self):
        """
        Given a simple string with spaces
        When sanitize_filename is called
        Then it returns lowercase with underscores
        """
        result = sanitize_filename("Hello World")
        assert_that(result).is_equal_to("hello_world")

    def test_special_characters_removed(self):
        """
        Given a string with special characters
        When sanitize_filename is called
        Then special characters are removed
        """
        result = sanitize_filename("Test@#$%^&*()!")
        assert_that(result).is_equal_to("test")

    def test_spaces_converted_to_underscores(self):
        """
        Given a string with spaces between words
        When sanitize_filename is called
        Then spaces become underscores
        """
        result = sanitize_filename("Two Sum Problem")
        assert_that(result).is_equal_to("two_sum_problem")

    def test_multiple_spaces_collapsed(self):
        """
        Given a string with multiple consecutive spaces
        When sanitize_filename is called
        Then multiple spaces collapse to single underscore
        """
        result = sanitize_filename("Two   Sum    Problem")
        assert_that(result).is_equal_to("two_sum_problem")

    def test_hyphens_converted_to_underscores(self):
        """
        Given a string with hyphens
        When sanitize_filename is called
        Then hyphens become underscores
        """
        result = sanitize_filename("Two-Sum-Problem")
        assert_that(result).is_equal_to("two_sum_problem")

    def test_mixed_case_to_lowercase(self):
        """
        Given a string with mixed case
        When sanitize_filename is called
        Then output is all lowercase
        """
        result = sanitize_filename("BinarySearch")
        assert_that(result).is_equal_to("binarysearch")

    def test_unicode_characters(self):
        """
        Given a string with unicode characters
        When sanitize_filename is called
        Then non-word characters are removed
        """
        result = sanitize_filename("Test café résumé")
        assert_that(result).contains("test")

    def test_empty_string(self):
        """
        Given an empty string
        When sanitize_filename is called
        Then empty string is returned
        """
        result = sanitize_filename("")
        assert_that(result).is_empty()

    def test_only_special_characters(self):
        """
        Given a string with only special characters
        When sanitize_filename is called
        Then empty string is returned
        """
        result = sanitize_filename("@#$%^&*()")
        assert_that(result).is_empty()

    def test_leading_trailing_spaces(self):
        """
        Given a string with leading/trailing spaces
        When sanitize_filename is called
        Then spaces are stripped
        """
        result = sanitize_filename("  Test  ")
        assert_that(result).is_equal_to("test")

    def test_numbers_preserved(self):
        """
        Given a string containing numbers
        When sanitize_filename is called
        Then numbers are preserved
        """
        result = sanitize_filename("Problem 123")
        assert_that(result).is_equal_to("problem_123")


class TestStripJsonBlock:
    """Tests for strip_json_block function."""

    def test_strip_json_markdown(self):
        """
        Given JSON wrapped in ```json markers
        When strip_json_block is called
        Then markers are removed
        """
        content = '```json\n{"key": "value"}\n```'
        result = strip_json_block(content)
        assert_that(result).is_equal_to('{"key": "value"}')

    def test_strip_plain_markdown(self):
        """
        Given JSON wrapped in plain ``` markers
        When strip_json_block is called
        Then markers are removed
        """
        content = '```\n{"key": "value"}\n```'
        result = strip_json_block(content)
        assert_that(result).is_equal_to('{"key": "value"}')

    def test_no_markers(self):
        """
        Given JSON without any markers
        When strip_json_block is called
        Then content is unchanged
        """
        content = '{"key": "value"}'
        result = strip_json_block(content)
        assert_that(result).is_equal_to('{"key": "value"}')

    def test_only_opening_marker(self):
        """
        Given JSON with only opening marker
        When strip_json_block is called
        Then opening marker is stripped
        """
        content = '```json\n{"key": "value"}'
        result = strip_json_block(content)
        assert_that(result).is_equal_to('{"key": "value"}')

    def test_only_closing_marker(self):
        """
        Given JSON with only closing marker
        When strip_json_block is called
        Then closing marker is stripped
        """
        content = '{"key": "value"}\n```'
        result = strip_json_block(content)
        assert_that(result).is_equal_to('{"key": "value"}')

    def test_whitespace_trimmed(self):
        """
        Given JSON with surrounding whitespace
        When strip_json_block is called
        Then whitespace is trimmed
        """
        content = '```json\n  {"key": "value"}  \n```'
        result = strip_json_block(content)
        assert_that(result).is_equal_to('{"key": "value"}')

    def test_complex_json(self):
        """
        Given complex nested JSON structure
        When strip_json_block is called and parsed
        Then content is preserved exactly
        """
        json_content = {
            "cards": [
                {"front": "Q1", "back": "A1"},
                {"front": "Q2", "back": "A2"}
            ]
        }
        content = f'```json\n{json.dumps(json_content)}\n```'
        result = strip_json_block(content)
        parsed = json.loads(result)
        assert_that(parsed).is_equal_to(json_content)

    def test_empty_string(self):
        """
        Given an empty string
        When strip_json_block is called
        Then empty string is returned
        """
        result = strip_json_block("")
        assert_that(result).is_empty()

    def test_multiline_json(self):
        """
        Given multiline formatted JSON
        When strip_json_block is called
        Then all content is preserved
        """
        content = '''```json
{
    "key": "value",
    "nested": {
        "inner": "data"
    }
}
```'''
        result = strip_json_block(content)
        parsed = json.loads(result)
        assert_that(parsed["key"]).is_equal_to("value")
        assert_that(parsed["nested"]["inner"]).is_equal_to("data")


class TestSaveFinalDeck:
    """Tests for save_final_deck function."""

    def test_save_creates_file(self, tmp_path, monkeypatch):
        """
        Given a list of problems
        When save_final_deck is called
        Then a JSON file is created
        """
        monkeypatch.chdir(tmp_path)

        problems = [
            {"title": "Test", "cards": [{"front": "Q", "back": "A"}]}
        ]
        save_final_deck(problems, "test_deck")

        json_files = list(tmp_path.glob("test_deck_*.json"))
        assert_that(json_files).is_length(1)

    def test_save_with_correct_content(self, tmp_path, monkeypatch):
        """
        Given multiple problems
        When save_final_deck is called
        Then file contains all problems
        """
        monkeypatch.chdir(tmp_path)

        problems = [
            {"title": "Problem 1", "cards": []},
            {"title": "Problem 2", "cards": []}
        ]
        save_final_deck(problems, "test_deck")

        json_files = list(tmp_path.glob("test_deck_*.json"))
        with open(json_files[0], "r") as f:
            loaded = json.load(f)

        assert_that(loaded).is_length(2)
        assert_that(loaded[0]["title"]).is_equal_to("Problem 1")
        assert_that(loaded[1]["title"]).is_equal_to("Problem 2")

    def test_save_with_timestamp_format(self, tmp_path, monkeypatch):
        """
        Given problems to save
        When save_final_deck is called
        Then filename includes properly formatted timestamp
        """
        monkeypatch.chdir(tmp_path)

        problems = [{"title": "Test"}]
        save_final_deck(problems, "test")

        json_files = list(tmp_path.glob("test_*.json"))
        filename = json_files[0].name

        assert_that(filename).starts_with("test_")
        assert_that(filename).ends_with(".json")
        # Check timestamp format YYYYMMDDTHHMMSS
        timestamp_part = filename.replace("test_", "").replace(".json", "")
        assert_that(timestamp_part).is_length(15)  # YYYYMMDDTHHMMSS
        assert_that(timestamp_part).contains("T")

    def test_save_unicode_content(self, tmp_path, monkeypatch):
        """
        Given problems with unicode characters
        When save_final_deck is called
        Then unicode is preserved in saved file
        """
        monkeypatch.chdir(tmp_path)

        problems = [
            {"title": "Café résumé", "cards": [{"front": "日本語", "back": "中文"}]}
        ]
        save_final_deck(problems, "unicode_test")

        json_files = list(tmp_path.glob("unicode_test_*.json"))
        with open(json_files[0], "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert_that(loaded[0]["title"]).is_equal_to("Café résumé")
        assert_that(loaded[0]["cards"][0]["front"]).is_equal_to("日本語")

    def test_save_empty_list(self, tmp_path, monkeypatch):
        """
        Given an empty problems list
        When save_final_deck is called
        Then empty array is saved
        """
        monkeypatch.chdir(tmp_path)

        save_final_deck([], "empty_test")

        json_files = list(tmp_path.glob("empty_test_*.json"))
        with open(json_files[0], "r") as f:
            loaded = json.load(f)

        assert_that(loaded).is_empty()

    def test_save_with_default_prefix(self, tmp_path, monkeypatch):
        """
        Given problems with no prefix specified
        When save_final_deck is called
        Then default prefix is used
        """
        monkeypatch.chdir(tmp_path)

        problems = [{"title": "Test"}]
        save_final_deck(problems)  # Uses default prefix

        json_files = list(tmp_path.glob("leetcode_anki_deck_*.json"))
        assert_that(json_files).is_length(1)
