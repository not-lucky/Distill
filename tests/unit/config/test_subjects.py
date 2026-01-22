"""Tests for config/subjects.py."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from assertpy import assert_that

from src.config.subjects import (
    SubjectRegistry,
    SubjectConfig,
    get_subject_config,
    BUILTIN_SUBJECTS,
)
from src.models import LeetCodeProblem, CSProblem, PhysicsProblem, MCQProblem, GenericProblem


class TestSubjectRegistry:
    """Tests for SubjectRegistry class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        with patch("src.config.subjects.load_config") as mock_load:
            from src.config.loader import SubjectSettings

            mock_cfg = MagicMock()
            mock_cfg.subjects = {
                "leetcode": SubjectSettings(enabled=True),
                "cs": SubjectSettings(enabled=True),
                "physics": SubjectSettings(enabled=False),
                "custom": SubjectSettings(
                    enabled=True,
                    prompts_dir="/path/to/prompts",
                    questions_file="/path/to/questions.json",
                    deck_prefix="Custom",
                ),
            }
            mock_load.return_value = mock_cfg
            yield mock_load

    def test_get_available_subjects(self, mock_config):
        """
        Given a registry with mixed enabled/disabled subjects
        When get_available_subjects is called
        Then only enabled subjects are returned
        """
        registry = SubjectRegistry()
        available = registry.get_available_subjects()

        assert_that(available).contains("leetcode")
        assert_that(available).contains("cs")
        assert_that(available).contains("custom")
        assert_that(available).does_not_contain("physics")  # Disabled

    def test_is_valid_subject_enabled(self, mock_config):
        """
        Given enabled subjects
        When is_valid_subject is called
        Then True is returned
        """
        registry = SubjectRegistry()

        assert_that(registry.is_valid_subject("leetcode")).is_true()
        assert_that(registry.is_valid_subject("cs")).is_true()
        assert_that(registry.is_valid_subject("custom")).is_true()

    def test_is_valid_subject_disabled(self, mock_config):
        """
        Given a disabled subject
        When is_valid_subject is called
        Then False is returned
        """
        registry = SubjectRegistry()

        assert_that(registry.is_valid_subject("physics")).is_false()

    def test_is_valid_subject_unknown(self, mock_config):
        """
        Given an unknown subject name
        When is_valid_subject is called
        Then False is returned
        """
        registry = SubjectRegistry()

        assert_that(registry.is_valid_subject("nonexistent")).is_false()

    def test_is_valid_subject_builtin_not_in_config(self):
        """
        Given an empty config
        When is_valid_subject is called for builtin subjects
        Then they are still considered valid
        """
        with patch("src.config.subjects.load_config") as mock_load:
            mock_cfg = MagicMock()
            mock_cfg.subjects = {}  # Empty config
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()

            # Built-in subjects should still be valid
            assert_that(registry.is_valid_subject("leetcode")).is_true()
            assert_that(registry.is_valid_subject("cs")).is_true()
            assert_that(registry.is_valid_subject("physics")).is_true()


class TestGetBuiltinConfig:
    """Tests for getting built-in subject configurations."""

    @pytest.fixture
    def registry(self):
        """Create a registry with default config."""
        with patch("src.config.subjects.load_config") as mock_load:
            from src.config.loader import SubjectSettings

            mock_cfg = MagicMock()
            mock_cfg.subjects = {
                "leetcode": SubjectSettings(enabled=True),
                "cs": SubjectSettings(enabled=True),
                "physics": SubjectSettings(enabled=True),
            }
            mock_load.return_value = mock_cfg
            return SubjectRegistry()

    def test_get_leetcode_config(self, registry):
        """
        Given a SubjectRegistry
        When get_config is called for leetcode
        Then LeetCode configuration is returned
        """
        config = registry.get_config("leetcode", is_multiple_choice=False)

        assert_that(config.name).is_equal_to("leetcode")
        assert_that(config.target_model).is_equal_to(LeetCodeProblem)
        assert_that(config.deck_prefix).is_equal_to("LeetCode")
        assert_that(config.deck_prefix_mcq).is_equal_to("LeetCode_MCQ")
        assert_that(config.target_questions).is_not_none()

    def test_get_cs_config(self, registry):
        """
        Given a SubjectRegistry
        When get_config is called for cs
        Then CS configuration is returned
        """
        config = registry.get_config("cs", is_multiple_choice=False)

        assert_that(config.name).is_equal_to("cs")
        assert_that(config.target_model).is_equal_to(CSProblem)
        assert_that(config.deck_prefix).is_equal_to("CS")

    def test_get_physics_config(self, registry):
        """
        Given a SubjectRegistry
        When get_config is called for physics
        Then Physics configuration is returned
        """
        config = registry.get_config("physics", is_multiple_choice=False)

        assert_that(config.name).is_equal_to("physics")
        assert_that(config.target_model).is_equal_to(PhysicsProblem)
        assert_that(config.deck_prefix).is_equal_to("Physics")

    def test_get_mcq_config(self, registry):
        """
        Given a SubjectRegistry
        When get_config is called with is_multiple_choice=True
        Then MCQ model is used
        """
        config = registry.get_config("leetcode", is_multiple_choice=True)

        assert_that(config.target_model).is_equal_to(MCQProblem)
        assert_that(config.initial_prompt).is_not_none()  # MCQ prompt

    def test_get_unknown_subject_raises(self, registry):
        """
        Given a SubjectRegistry
        When get_config is called for unknown subject
        Then ValueError is raised
        """
        with pytest.raises(ValueError, match="Unknown subject"):
            registry.get_config("nonexistent")


class TestGetCustomConfig:
    """Tests for getting custom subject configurations."""

    def test_get_custom_subject_config(self, tmp_path):
        """
        Given a custom subject with prompts and questions
        When get_config is called
        Then custom configuration is returned
        """
        # Create prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "initial.md").write_text("Custom initial prompt")
        (prompts_dir / "combine.md").write_text("Custom combine prompt")

        # Create questions file
        questions_file = tmp_path / "questions.json"
        questions_file.write_text(json.dumps({
            "Category1": ["Q1", "Q2"],
            "Category2": ["Q3"]
        }))

        with patch("src.config.subjects.load_config") as mock_load:
            from src.config.loader import SubjectSettings

            mock_cfg = MagicMock()
            mock_cfg.subjects = {
                "biology": SubjectSettings(
                    enabled=True,
                    prompts_dir=str(prompts_dir),
                    questions_file=str(questions_file),
                    deck_prefix="Biology",
                    deck_prefix_mcq="Biology_MCQ",
                ),
            }
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()
            config = registry.get_config("biology")

            assert_that(config.name).is_equal_to("biology")
            assert_that(config.target_model).is_equal_to(GenericProblem)
            assert_that(config.deck_prefix).is_equal_to("Biology")
            assert_that(config.deck_prefix_mcq).is_equal_to("Biology_MCQ")
            assert_that(config.target_questions).contains_key("Category1")
            assert_that(config.target_questions["Category1"]).is_length(2)

    def test_custom_subject_default_deck_prefix(self, tmp_path):
        """
        Given a custom subject without explicit deck_prefix
        When get_config is called
        Then title case name is used as prefix
        """
        questions_file = tmp_path / "questions.json"
        questions_file.write_text('{"General": ["Q1"]}')

        with patch("src.config.subjects.load_config") as mock_load:
            from src.config.loader import SubjectSettings

            mock_cfg = MagicMock()
            mock_cfg.subjects = {
                "my_subject": SubjectSettings(
                    enabled=True,
                    questions_file=str(questions_file),
                ),
            }
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()
            config = registry.get_config("my_subject")

            assert_that(config.deck_prefix).is_equal_to("My_Subject")


class TestLoadQuestionsFile:
    """Tests for _load_questions_file method."""

    def test_load_categorized_format(self, tmp_path):
        """
        Given a categorized questions JSON file
        When _load_questions_file is called
        Then categories are loaded correctly
        """
        questions_file = tmp_path / "questions.json"
        questions_file.write_text(json.dumps({
            "Arrays": ["Two Sum", "Binary Search"],
            "Strings": ["Valid Palindrome"]
        }))

        with patch("src.config.subjects.load_config") as mock_load:
            from src.config.loader import SubjectSettings

            mock_cfg = MagicMock()
            mock_cfg.subjects = {
                "test": SubjectSettings(
                    enabled=True,
                    questions_file=str(questions_file),
                ),
            }
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()
            questions = registry._load_questions_file(str(questions_file))

            assert_that(questions).contains_key("Arrays")
            assert_that(questions).contains_key("Strings")
            assert_that(questions["Arrays"]).is_equal_to(["Two Sum", "Binary Search"])

    def test_load_flat_list_format(self, tmp_path):
        """
        Given a flat list of questions
        When _load_questions_file is called
        Then questions are wrapped in General category
        """
        questions_file = tmp_path / "questions.json"
        questions_file.write_text(json.dumps(["Q1", "Q2", "Q3"]))

        with patch("src.config.subjects.load_config") as mock_load:
            mock_cfg = MagicMock()
            mock_cfg.subjects = {}
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()
            questions = registry._load_questions_file(str(questions_file))

            assert_that(questions).contains_key("General")
            assert_that(questions["General"]).is_equal_to(["Q1", "Q2", "Q3"])

    def test_load_missing_file_raises(self, tmp_path):
        """
        Given a non-existent questions file
        When _load_questions_file is called
        Then FileNotFoundError is raised
        """
        with patch("src.config.subjects.load_config") as mock_load:
            mock_cfg = MagicMock()
            mock_cfg.subjects = {}
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()

            with pytest.raises(FileNotFoundError):
                registry._load_questions_file(str(tmp_path / "missing.json"))

    def test_load_invalid_format_raises(self, tmp_path):
        """
        Given an invalid questions format
        When _load_questions_file is called
        Then ValueError is raised
        """
        questions_file = tmp_path / "invalid.json"
        questions_file.write_text('"just a string"')

        with patch("src.config.subjects.load_config") as mock_load:
            mock_cfg = MagicMock()
            mock_cfg.subjects = {}
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()

            with pytest.raises(ValueError, match="Invalid questions format"):
                registry._load_questions_file(str(questions_file))


class TestSubjectConfig:
    """Tests for SubjectConfig dataclass."""

    def test_subject_config_creation(self):
        """
        Given valid parameters
        When SubjectConfig is created
        Then all fields are stored correctly
        """
        config = SubjectConfig(
            name="test",
            target_questions={"Cat": ["Q1"]},
            initial_prompt="Initial",
            combine_prompt="Combine",
            target_model=LeetCodeProblem,
            deck_prefix="Test",
            deck_prefix_mcq="Test_MCQ",
        )

        assert_that(config.name).is_equal_to("test")
        assert_that(config.target_questions).is_equal_to({"Cat": ["Q1"]})
        assert_that(config.initial_prompt).is_equal_to("Initial")
        assert_that(config.combine_prompt).is_equal_to("Combine")
        assert_that(config.target_model).is_equal_to(LeetCodeProblem)
        assert_that(config.deck_prefix).is_equal_to("Test")
        assert_that(config.deck_prefix_mcq).is_equal_to("Test_MCQ")

    def test_subject_config_none_prompts(self):
        """
        Given None for prompts
        When SubjectConfig is created
        Then None values are stored
        """
        config = SubjectConfig(
            name="test",
            target_questions={},
            initial_prompt=None,
            combine_prompt=None,
            target_model=GenericProblem,
            deck_prefix="Test",
            deck_prefix_mcq="Test_MCQ",
        )

        assert_that(config.initial_prompt).is_none()
        assert_that(config.combine_prompt).is_none()


class TestGetSubjectConfigFunction:
    """Tests for get_subject_config convenience function."""

    def test_get_subject_config_leetcode(self):
        """
        Given leetcode subject
        When get_subject_config is called
        Then leetcode configuration is returned
        """
        with patch("src.config.subjects.load_config") as mock_load:
            from src.config.loader import SubjectSettings

            mock_cfg = MagicMock()
            mock_cfg.subjects = {
                "leetcode": SubjectSettings(enabled=True),
            }
            mock_load.return_value = mock_cfg

            config = get_subject_config("leetcode")

            assert_that(config.name).is_equal_to("leetcode")
            assert_that(config.target_model).is_equal_to(LeetCodeProblem)

    def test_get_subject_config_mcq(self):
        """
        Given a subject with is_multiple_choice=True
        When get_subject_config is called
        Then MCQ model is used
        """
        with patch("src.config.subjects.load_config") as mock_load:
            from src.config.loader import SubjectSettings

            mock_cfg = MagicMock()
            mock_cfg.subjects = {
                "cs": SubjectSettings(enabled=True),
            }
            mock_load.return_value = mock_cfg

            config = get_subject_config("cs", is_multiple_choice=True)

            assert_that(config.target_model).is_equal_to(MCQProblem)


class TestBuiltinSubjects:
    """Tests for BUILTIN_SUBJECTS constant."""

    def test_builtin_subjects_contains_expected(self):
        """
        Given the BUILTIN_SUBJECTS constant
        When checking its contents
        Then all expected subjects are present
        """
        assert_that(BUILTIN_SUBJECTS).contains("leetcode")
        assert_that(BUILTIN_SUBJECTS).contains("cs")
        assert_that(BUILTIN_SUBJECTS).contains("physics")

    def test_builtin_subjects_is_set(self):
        """
        Given the BUILTIN_SUBJECTS constant
        When checking its type
        Then it is a set
        """
        assert_that(BUILTIN_SUBJECTS).is_instance_of(set)
