"""Tests for config/modes.py."""

import pytest

from src.config.modes import (
    detect_mode_from_filename,
    parse_mode,
    get_deck_prefix,
    is_valid_mode,
    VALID_MODES,
    DECK_PREFIXES,
)


class TestDetectModeFromFilename:
    """Tests for detect_mode_from_filename function."""

    def test_detect_leetcode(self):
        """Test detecting leetcode mode."""
        assert detect_mode_from_filename("leetcode_deck.json") == "leetcode"
        assert detect_mode_from_filename("leetcode_anki_20231201.json") == "leetcode"
        assert detect_mode_from_filename("/path/to/leetcode_cards.json") == "leetcode"

    def test_detect_cs(self):
        """Test detecting cs mode."""
        assert detect_mode_from_filename("cs_deck.json") == "cs"
        assert detect_mode_from_filename("cs_anki_cards.json") == "cs"

    def test_detect_physics(self):
        """Test detecting physics mode."""
        assert detect_mode_from_filename("physics_deck.json") == "physics"
        assert detect_mode_from_filename("physics_anki.json") == "physics"

    def test_detect_leetcode_mcq(self):
        """Test detecting leetcode_mcq mode."""
        assert detect_mode_from_filename("leetcode_mcq_deck.json") == "leetcode_mcq"
        assert detect_mode_from_filename("leetcode_mcq.json") == "leetcode_mcq"

    def test_detect_cs_mcq(self):
        """Test detecting cs_mcq mode."""
        assert detect_mode_from_filename("cs_mcq_deck.json") == "cs_mcq"

    def test_detect_physics_mcq(self):
        """Test detecting physics_mcq mode."""
        assert detect_mode_from_filename("physics_mcq_deck.json") == "physics_mcq"

    def test_detect_generic_mcq(self):
        """Test detecting generic mcq mode."""
        assert detect_mode_from_filename("my_mcq_cards.json") == "mcq"
        assert detect_mode_from_filename("custom_mcq.json") == "mcq"

    def test_detect_default_to_leetcode(self):
        """Test that unknown patterns default to leetcode."""
        assert detect_mode_from_filename("unknown.json") == "leetcode"
        assert detect_mode_from_filename("random_file.json") == "leetcode"

    def test_detect_case_insensitive(self):
        """Test that detection is case insensitive."""
        assert detect_mode_from_filename("LEETCODE_DECK.json") == "leetcode"
        assert detect_mode_from_filename("CS_MCQ_Cards.json") == "cs_mcq"

    def test_mcq_takes_precedence(self):
        """Test that MCQ modes are detected before base modes."""
        # cs_mcq should be detected as cs_mcq, not cs
        assert detect_mode_from_filename("cs_mcq_test.json") == "cs_mcq"


class TestParseMode:
    """Tests for parse_mode function."""

    def test_parse_leetcode(self):
        """Test parsing leetcode mode."""
        subject, is_mcq = parse_mode("leetcode")
        assert subject == "leetcode"
        assert is_mcq is False

    def test_parse_cs(self):
        """Test parsing cs mode."""
        subject, is_mcq = parse_mode("cs")
        assert subject == "cs"
        assert is_mcq is False

    def test_parse_physics(self):
        """Test parsing physics mode."""
        subject, is_mcq = parse_mode("physics")
        assert subject == "physics"
        assert is_mcq is False

    def test_parse_leetcode_mcq(self):
        """Test parsing leetcode_mcq mode."""
        subject, is_mcq = parse_mode("leetcode_mcq")
        assert subject == "leetcode"
        assert is_mcq is True

    def test_parse_cs_mcq(self):
        """Test parsing cs_mcq mode."""
        subject, is_mcq = parse_mode("cs_mcq")
        assert subject == "cs"
        assert is_mcq is True

    def test_parse_physics_mcq(self):
        """Test parsing physics_mcq mode."""
        subject, is_mcq = parse_mode("physics_mcq")
        assert subject == "physics"
        assert is_mcq is True

    def test_parse_mcq_only(self):
        """Test parsing 'mcq' mode defaults to leetcode."""
        subject, is_mcq = parse_mode("mcq")
        assert subject == "leetcode"
        assert is_mcq is True


class TestGetDeckPrefix:
    """Tests for get_deck_prefix function."""

    def test_get_leetcode_prefix(self):
        """Test getting LeetCode prefix."""
        assert get_deck_prefix("leetcode") == "LeetCode"

    def test_get_leetcode_mcq_prefix(self):
        """Test getting LeetCode_MCQ prefix."""
        assert get_deck_prefix("leetcode_mcq") == "LeetCode_MCQ"

    def test_get_cs_prefix(self):
        """Test getting CS prefix."""
        assert get_deck_prefix("cs") == "CS"

    def test_get_cs_mcq_prefix(self):
        """Test getting CS_MCQ prefix."""
        assert get_deck_prefix("cs_mcq") == "CS_MCQ"

    def test_get_physics_prefix(self):
        """Test getting Physics prefix."""
        assert get_deck_prefix("physics") == "Physics"

    def test_get_physics_mcq_prefix(self):
        """Test getting Physics_MCQ prefix."""
        assert get_deck_prefix("physics_mcq") == "Physics_MCQ"

    def test_get_mcq_prefix(self):
        """Test getting prefix for 'mcq' mode."""
        assert get_deck_prefix("mcq") == "LeetCode_MCQ"

    def test_get_unknown_defaults_to_leetcode(self):
        """Test that unknown mode defaults to LeetCode."""
        assert get_deck_prefix("unknown") == "LeetCode"


class TestIsValidMode:
    """Tests for is_valid_mode function."""

    def test_valid_standard_modes(self):
        """Test that standard modes are valid."""
        assert is_valid_mode("leetcode") is True
        assert is_valid_mode("cs") is True
        assert is_valid_mode("physics") is True

    def test_valid_mcq_modes(self):
        """Test that MCQ modes are valid."""
        assert is_valid_mode("leetcode_mcq") is True
        assert is_valid_mode("cs_mcq") is True
        assert is_valid_mode("physics_mcq") is True
        assert is_valid_mode("mcq") is True

    def test_invalid_modes(self):
        """Test that invalid modes return False."""
        assert is_valid_mode("invalid") is False
        assert is_valid_mode("unknown") is False
        assert is_valid_mode("") is False


class TestValidModes:
    """Tests for VALID_MODES constant."""

    def test_contains_standard_modes(self):
        """Test that VALID_MODES contains standard modes."""
        assert "leetcode" in VALID_MODES
        assert "cs" in VALID_MODES
        assert "physics" in VALID_MODES

    def test_contains_mcq_modes(self):
        """Test that VALID_MODES contains MCQ modes."""
        assert "leetcode_mcq" in VALID_MODES
        assert "cs_mcq" in VALID_MODES
        assert "physics_mcq" in VALID_MODES
        assert "mcq" in VALID_MODES

    def test_is_frozenset(self):
        """Test that VALID_MODES is a frozenset."""
        assert isinstance(VALID_MODES, frozenset)


class TestDeckPrefixes:
    """Tests for DECK_PREFIXES constant."""

    def test_contains_all_subjects(self):
        """Test that DECK_PREFIXES contains all subjects."""
        assert "leetcode" in DECK_PREFIXES
        assert "cs" in DECK_PREFIXES
        assert "physics" in DECK_PREFIXES

    def test_prefixes_are_tuples(self):
        """Test that prefix values are tuples."""
        for subject, prefixes in DECK_PREFIXES.items():
            assert isinstance(prefixes, tuple)
            assert len(prefixes) == 2

    def test_prefix_values(self):
        """Test specific prefix values."""
        assert DECK_PREFIXES["leetcode"] == ("LeetCode", "LeetCode_MCQ")
        assert DECK_PREFIXES["cs"] == ("CS", "CS_MCQ")
        assert DECK_PREFIXES["physics"] == ("Physics", "Physics_MCQ")
