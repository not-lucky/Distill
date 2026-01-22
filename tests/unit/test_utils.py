"""Tests for utility functions in src/utils.py."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch
import datetime

from src.utils import sanitize_filename, strip_json_block, save_final_deck


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_simple_string(self):
        """Test sanitizing a simple string."""
        result = sanitize_filename("Hello World")
        assert result == "hello_world"

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        result = sanitize_filename("Test@#$%^&*()!")
        assert result == "test"

    def test_spaces_converted_to_underscores(self):
        """Test that spaces are converted to underscores."""
        result = sanitize_filename("Two Sum Problem")
        assert result == "two_sum_problem"

    def test_multiple_spaces_collapsed(self):
        """Test that multiple spaces are collapsed to single underscore."""
        result = sanitize_filename("Two   Sum    Problem")
        assert result == "two_sum_problem"

    def test_hyphens_converted_to_underscores(self):
        """Test that hyphens are converted to underscores."""
        result = sanitize_filename("Two-Sum-Problem")
        assert result == "two_sum_problem"

    def test_mixed_case_to_lowercase(self):
        """Test that output is lowercase."""
        result = sanitize_filename("BinarySearch")
        assert result == "binarysearch"

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        result = sanitize_filename("Test café résumé")
        # Non-word characters are removed
        assert "test" in result

    def test_empty_string(self):
        """Test handling of empty string."""
        result = sanitize_filename("")
        assert result == ""

    def test_only_special_characters(self):
        """Test string with only special characters."""
        result = sanitize_filename("@#$%^&*()")
        assert result == ""

    def test_leading_trailing_spaces(self):
        """Test that leading/trailing spaces are stripped."""
        result = sanitize_filename("  Test  ")
        assert result == "test"

    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        result = sanitize_filename("Problem 123")
        assert result == "problem_123"


class TestStripJsonBlock:
    """Tests for strip_json_block function."""

    def test_strip_json_markdown(self):
        """Test stripping ```json markers."""
        content = '```json\n{"key": "value"}\n```'
        result = strip_json_block(content)
        assert result == '{"key": "value"}'

    def test_strip_plain_markdown(self):
        """Test stripping plain ``` markers."""
        content = '```\n{"key": "value"}\n```'
        result = strip_json_block(content)
        assert result == '{"key": "value"}'

    def test_no_markers(self):
        """Test content without markers is unchanged."""
        content = '{"key": "value"}'
        result = strip_json_block(content)
        assert result == '{"key": "value"}'

    def test_only_opening_marker(self):
        """Test content with only opening marker."""
        content = '```json\n{"key": "value"}'
        result = strip_json_block(content)
        assert result == '{"key": "value"}'

    def test_only_closing_marker(self):
        """Test content with only closing marker."""
        content = '{"key": "value"}\n```'
        result = strip_json_block(content)
        assert result == '{"key": "value"}'

    def test_whitespace_trimmed(self):
        """Test that whitespace is trimmed from result."""
        content = '```json\n  {"key": "value"}  \n```'
        result = strip_json_block(content)
        assert result == '{"key": "value"}'

    def test_complex_json(self):
        """Test with complex JSON content."""
        json_content = {
            "cards": [
                {"front": "Q1", "back": "A1"},
                {"front": "Q2", "back": "A2"}
            ]
        }
        content = f'```json\n{json.dumps(json_content)}\n```'
        result = strip_json_block(content)
        parsed = json.loads(result)
        assert parsed == json_content

    def test_empty_string(self):
        """Test with empty string."""
        result = strip_json_block("")
        assert result == ""

    def test_multiline_json(self):
        """Test with multiline JSON content."""
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
        assert parsed["key"] == "value"
        assert parsed["nested"]["inner"] == "data"


class TestSaveFinalDeck:
    """Tests for save_final_deck function."""

    def test_save_creates_file(self, tmp_path, monkeypatch):
        """Test that save_final_deck creates a JSON file."""
        monkeypatch.chdir(tmp_path)

        problems = [
            {"title": "Test", "cards": [{"front": "Q", "back": "A"}]}
        ]
        save_final_deck(problems, "test_deck")

        # Find the created file
        json_files = list(tmp_path.glob("test_deck_*.json"))
        assert len(json_files) == 1

    def test_save_with_correct_content(self, tmp_path, monkeypatch):
        """Test that saved file has correct content."""
        monkeypatch.chdir(tmp_path)

        problems = [
            {"title": "Problem 1", "cards": []},
            {"title": "Problem 2", "cards": []}
        ]
        save_final_deck(problems, "test_deck")

        json_files = list(tmp_path.glob("test_deck_*.json"))
        with open(json_files[0], "r") as f:
            loaded = json.load(f)

        assert len(loaded) == 2
        assert loaded[0]["title"] == "Problem 1"
        assert loaded[1]["title"] == "Problem 2"

    def test_save_with_timestamp_format(self, tmp_path, monkeypatch):
        """Test that filename includes timestamp."""
        monkeypatch.chdir(tmp_path)

        problems = [{"title": "Test"}]
        save_final_deck(problems, "test")

        json_files = list(tmp_path.glob("test_*.json"))
        filename = json_files[0].name

        # Should have format like test_20231201T120000.json
        assert filename.startswith("test_")
        assert filename.endswith(".json")
        # Check timestamp format YYYYMMDDTHHMMSS
        timestamp_part = filename.replace("test_", "").replace(".json", "")
        assert len(timestamp_part) == 15  # YYYYMMDDTHHMMSS
        assert "T" in timestamp_part

    def test_save_unicode_content(self, tmp_path, monkeypatch):
        """Test saving content with unicode characters."""
        monkeypatch.chdir(tmp_path)

        problems = [
            {"title": "Café résumé", "cards": [{"front": "日本語", "back": "中文"}]}
        ]
        save_final_deck(problems, "unicode_test")

        json_files = list(tmp_path.glob("unicode_test_*.json"))
        with open(json_files[0], "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded[0]["title"] == "Café résumé"
        assert loaded[0]["cards"][0]["front"] == "日本語"

    def test_save_empty_list(self, tmp_path, monkeypatch):
        """Test saving empty problems list."""
        monkeypatch.chdir(tmp_path)

        save_final_deck([], "empty_test")

        json_files = list(tmp_path.glob("empty_test_*.json"))
        with open(json_files[0], "r") as f:
            loaded = json.load(f)

        assert loaded == []

    def test_save_with_default_prefix(self, tmp_path, monkeypatch):
        """Test saving with default prefix."""
        monkeypatch.chdir(tmp_path)

        problems = [{"title": "Test"}]
        save_final_deck(problems)  # Uses default prefix

        json_files = list(tmp_path.glob("leetcode_anki_deck_*.json"))
        assert len(json_files) == 1
