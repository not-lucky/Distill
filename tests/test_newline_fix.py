"""Tests for newline unescaping fix."""

import pytest
from assertpy import assert_that
from src.utils import unescape_newlines

class TestNewlineUnescaping:
    """Tests for unescape_newlines function in src/utils.py."""

    def test_unescape_simple_string(self):
        """
        Given a string with literal \n
        When unescape_newlines is called
        Then it returns a string with actual newlines
        """
        input_str = "Line 1\\nLine 2"
        result = unescape_newlines(input_str)
        assert_that(result).is_equal_to("Line 1\nLine 2")

    def test_unescape_list(self):
        """
        Given a list of strings with literal \n
        When unescape_newlines is called
        Then it returns a list with unescaped newlines
        """
        input_list = ["Line 1\\nLine 2", "Another\\nLine"]
        result = unescape_newlines(input_list)
        assert_that(result).is_equal_to(["Line 1\nLine 2", "Another\nLine"])

    def test_unescape_dict(self):
        """
        Given a dictionary with nested literal \n
        When unescape_newlines is called
        Then it returns a dictionary with all strings unescaped
        """
        input_dict = {
            "front": "Question\\nNext line",
            "back": "Answer\\nNext line",
            "metadata": {
                "note": "Nested\\nnote"
            },
            "tags": ["tag1\\n", "tag2"]
        }
        result = unescape_newlines(input_dict)

        expected = {
            "front": "Question\nNext line",
            "back": "Answer\nNext line",
            "metadata": {
                "note": "Nested\nnote"
            },
            "tags": ["tag1\n", "tag2"]
        }
        assert_that(result).is_equal_to(expected)

    def test_edge_case_trailing_backslash(self):
        """
        Given a string ending in a backslash
        When unescape_newlines is called
        Then it handles it correctly
        """
        input_str = "Ends with backslash\\"
        result = unescape_newlines(input_str)
        assert_that(result).is_equal_to("Ends with backslash\\")

    def test_nested_complex_structure(self):
        """
        Given a complex nested structure
        When unescape_newlines is called
        Then all strings are processed
        """
        input_data = [
            {"a": "b\\nc"},
            [{"d": "e\\nf"}]
        ]
        result = unescape_newlines(input_data)
        assert_that(result[0]["a"]).is_equal_to("b\nc")
        assert_that(result[1][0]["d"]).is_equal_to("e\nf")
