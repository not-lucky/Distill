"""Tests for config/modes.py."""

import pytest

from assertpy import assert_that

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
        """
        Given filenames containing 'leetcode'
        When detect_mode_from_filename is called
        Then 'leetcode' mode is returned
        """
        assert_that(detect_mode_from_filename("leetcode_deck.json")).is_equal_to("leetcode")
        assert_that(detect_mode_from_filename("leetcode_anki_20231201.json")).is_equal_to("leetcode")
        assert_that(detect_mode_from_filename("/path/to/leetcode_cards.json")).is_equal_to("leetcode")

    def test_detect_cs(self):
        """
        Given filenames containing 'cs'
        When detect_mode_from_filename is called
        Then 'cs' mode is returned
        """
        assert_that(detect_mode_from_filename("cs_deck.json")).is_equal_to("cs")
        assert_that(detect_mode_from_filename("cs_anki_cards.json")).is_equal_to("cs")

    def test_detect_physics(self):
        """
        Given filenames containing 'physics'
        When detect_mode_from_filename is called
        Then 'physics' mode is returned
        """
        assert_that(detect_mode_from_filename("physics_deck.json")).is_equal_to("physics")
        assert_that(detect_mode_from_filename("physics_anki.json")).is_equal_to("physics")

    def test_detect_leetcode_mcq(self):
        """
        Given filenames containing 'leetcode_mcq'
        When detect_mode_from_filename is called
        Then 'leetcode_mcq' mode is returned
        """
        assert_that(detect_mode_from_filename("leetcode_mcq_deck.json")).is_equal_to("leetcode_mcq")
        assert_that(detect_mode_from_filename("leetcode_mcq.json")).is_equal_to("leetcode_mcq")

    def test_detect_cs_mcq(self):
        """
        Given filenames containing 'cs_mcq'
        When detect_mode_from_filename is called
        Then 'cs_mcq' mode is returned
        """
        assert_that(detect_mode_from_filename("cs_mcq_deck.json")).is_equal_to("cs_mcq")

    def test_detect_physics_mcq(self):
        """
        Given filenames containing 'physics_mcq'
        When detect_mode_from_filename is called
        Then 'physics_mcq' mode is returned
        """
        assert_that(detect_mode_from_filename("physics_mcq_deck.json")).is_equal_to("physics_mcq")

    def test_detect_generic_mcq(self):
        """
        Given filenames containing 'mcq' without subject prefix
        When detect_mode_from_filename is called
        Then 'mcq' mode is returned
        """
        assert_that(detect_mode_from_filename("my_mcq_cards.json")).is_equal_to("mcq")
        assert_that(detect_mode_from_filename("custom_mcq.json")).is_equal_to("mcq")

    def test_detect_default_to_leetcode(self):
        """
        Given filenames without recognizable patterns
        When detect_mode_from_filename is called
        Then 'leetcode' mode is returned as default
        """
        assert_that(detect_mode_from_filename("unknown.json")).is_equal_to("leetcode")
        assert_that(detect_mode_from_filename("random_file.json")).is_equal_to("leetcode")

    def test_detect_case_insensitive(self):
        """
        Given filenames with mixed case
        When detect_mode_from_filename is called
        Then detection is case insensitive
        """
        assert_that(detect_mode_from_filename("LEETCODE_DECK.json")).is_equal_to("leetcode")
        assert_that(detect_mode_from_filename("CS_MCQ_Cards.json")).is_equal_to("cs_mcq")

    def test_mcq_takes_precedence(self):
        """
        Given filenames with both subject and mcq
        When detect_mode_from_filename is called
        Then MCQ mode takes precedence over base mode
        """
        assert_that(detect_mode_from_filename("cs_mcq_test.json")).is_equal_to("cs_mcq")


class TestParseMode:
    """Tests for parse_mode function."""

    def test_parse_leetcode(self):
        """
        Given 'leetcode' mode string
        When parse_mode is called
        Then subject is 'leetcode' and is_mcq is False
        """
        subject, is_mcq = parse_mode("leetcode")
        assert_that(subject).is_equal_to("leetcode")
        assert_that(is_mcq).is_false()

    def test_parse_cs(self):
        """
        Given 'cs' mode string
        When parse_mode is called
        Then subject is 'cs' and is_mcq is False
        """
        subject, is_mcq = parse_mode("cs")
        assert_that(subject).is_equal_to("cs")
        assert_that(is_mcq).is_false()

    def test_parse_physics(self):
        """
        Given 'physics' mode string
        When parse_mode is called
        Then subject is 'physics' and is_mcq is False
        """
        subject, is_mcq = parse_mode("physics")
        assert_that(subject).is_equal_to("physics")
        assert_that(is_mcq).is_false()

    def test_parse_leetcode_mcq(self):
        """
        Given 'leetcode_mcq' mode string
        When parse_mode is called
        Then subject is 'leetcode' and is_mcq is True
        """
        subject, is_mcq = parse_mode("leetcode_mcq")
        assert_that(subject).is_equal_to("leetcode")
        assert_that(is_mcq).is_true()

    def test_parse_cs_mcq(self):
        """
        Given 'cs_mcq' mode string
        When parse_mode is called
        Then subject is 'cs' and is_mcq is True
        """
        subject, is_mcq = parse_mode("cs_mcq")
        assert_that(subject).is_equal_to("cs")
        assert_that(is_mcq).is_true()

    def test_parse_physics_mcq(self):
        """
        Given 'physics_mcq' mode string
        When parse_mode is called
        Then subject is 'physics' and is_mcq is True
        """
        subject, is_mcq = parse_mode("physics_mcq")
        assert_that(subject).is_equal_to("physics")
        assert_that(is_mcq).is_true()

    def test_parse_mcq_only(self):
        """
        Given 'mcq' mode string
        When parse_mode is called
        Then subject defaults to 'leetcode' and is_mcq is True
        """
        subject, is_mcq = parse_mode("mcq")
        assert_that(subject).is_equal_to("leetcode")
        assert_that(is_mcq).is_true()


class TestGetDeckPrefix:
    """Tests for get_deck_prefix function."""

    def test_get_leetcode_prefix(self):
        """
        Given 'leetcode' mode
        When get_deck_prefix is called
        Then 'LeetCode' is returned
        """
        assert_that(get_deck_prefix("leetcode")).is_equal_to("LeetCode")

    def test_get_leetcode_mcq_prefix(self):
        """
        Given 'leetcode_mcq' mode
        When get_deck_prefix is called
        Then 'LeetCode_MCQ' is returned
        """
        assert_that(get_deck_prefix("leetcode_mcq")).is_equal_to("LeetCode_MCQ")

    def test_get_cs_prefix(self):
        """
        Given 'cs' mode
        When get_deck_prefix is called
        Then 'CS' is returned
        """
        assert_that(get_deck_prefix("cs")).is_equal_to("CS")

    def test_get_cs_mcq_prefix(self):
        """
        Given 'cs_mcq' mode
        When get_deck_prefix is called
        Then 'CS_MCQ' is returned
        """
        assert_that(get_deck_prefix("cs_mcq")).is_equal_to("CS_MCQ")

    def test_get_physics_prefix(self):
        """
        Given 'physics' mode
        When get_deck_prefix is called
        Then 'Physics' is returned
        """
        assert_that(get_deck_prefix("physics")).is_equal_to("Physics")

    def test_get_physics_mcq_prefix(self):
        """
        Given 'physics_mcq' mode
        When get_deck_prefix is called
        Then 'Physics_MCQ' is returned
        """
        assert_that(get_deck_prefix("physics_mcq")).is_equal_to("Physics_MCQ")

    def test_get_mcq_prefix(self):
        """
        Given 'mcq' mode
        When get_deck_prefix is called
        Then 'LeetCode_MCQ' is returned
        """
        assert_that(get_deck_prefix("mcq")).is_equal_to("LeetCode_MCQ")

    def test_get_unknown_defaults_to_leetcode(self):
        """
        Given an unknown mode
        When get_deck_prefix is called
        Then 'LeetCode' is returned as default
        """
        assert_that(get_deck_prefix("unknown")).is_equal_to("LeetCode")


class TestIsValidMode:
    """Tests for is_valid_mode function."""

    def test_valid_standard_modes(self):
        """
        Given standard mode strings
        When is_valid_mode is called
        Then True is returned
        """
        assert_that(is_valid_mode("leetcode")).is_true()
        assert_that(is_valid_mode("cs")).is_true()
        assert_that(is_valid_mode("physics")).is_true()

    def test_valid_mcq_modes(self):
        """
        Given MCQ mode strings
        When is_valid_mode is called
        Then True is returned
        """
        assert_that(is_valid_mode("leetcode_mcq")).is_true()
        assert_that(is_valid_mode("cs_mcq")).is_true()
        assert_that(is_valid_mode("physics_mcq")).is_true()
        assert_that(is_valid_mode("mcq")).is_true()

    def test_invalid_modes(self):
        """
        Given invalid mode strings
        When is_valid_mode is called
        Then False is returned
        """
        assert_that(is_valid_mode("invalid")).is_false()
        assert_that(is_valid_mode("unknown")).is_false()
        assert_that(is_valid_mode("")).is_false()


class TestValidModes:
    """Tests for VALID_MODES constant."""

    def test_contains_standard_modes(self):
        """
        Given the VALID_MODES constant
        When checking for standard modes
        Then all standard modes are present
        """
        assert_that("leetcode" in VALID_MODES).is_true()
        assert_that("cs" in VALID_MODES).is_true()
        assert_that("physics" in VALID_MODES).is_true()

    def test_contains_mcq_modes(self):
        """
        Given the VALID_MODES constant
        When checking for MCQ modes
        Then all MCQ modes are present
        """
        assert_that("leetcode_mcq" in VALID_MODES).is_true()
        assert_that("cs_mcq" in VALID_MODES).is_true()
        assert_that("physics_mcq" in VALID_MODES).is_true()
        assert_that("mcq" in VALID_MODES).is_true()

    def test_is_frozenset(self):
        """
        Given the VALID_MODES constant
        When checking its type
        Then it is a frozenset
        """
        assert_that(VALID_MODES).is_instance_of(frozenset)


class TestDeckPrefixes:
    """Tests for DECK_PREFIXES constant."""

    def test_contains_all_subjects(self):
        """
        Given the DECK_PREFIXES constant
        When checking for subjects
        Then all subjects are present
        """
        assert_that("leetcode" in DECK_PREFIXES).is_true()
        assert_that("cs" in DECK_PREFIXES).is_true()
        assert_that("physics" in DECK_PREFIXES).is_true()

    def test_prefixes_are_tuples(self):
        """
        Given the DECK_PREFIXES constant
        When checking value types
        Then all values are 2-element tuples
        """
        for subject, prefixes in DECK_PREFIXES.items():
            assert_that(prefixes).is_instance_of(tuple)
            assert_that(prefixes).is_length(2)

    def test_prefix_values(self):
        """
        Given the DECK_PREFIXES constant
        When checking specific prefix values
        Then correct tuple values are returned
        """
        assert_that(DECK_PREFIXES["leetcode"]).is_equal_to(("LeetCode", "LeetCode_MCQ"))
        assert_that(DECK_PREFIXES["cs"]).is_equal_to(("CS", "CS_MCQ"))
        assert_that(DECK_PREFIXES["physics"]).is_equal_to(("Physics", "Physics_MCQ"))
