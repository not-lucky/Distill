"""Unit tests for SubjectConfig and SubjectRegistry."""

import pytest
from src.config.subjects import SubjectRegistry, SubjectConfig
from src.models import LeetCodeProblem, CSProblem, PhysicsProblem, MCQProblem


class TestSubjectRegistry:
    """Tests for SubjectRegistry.get_config()."""

    def test_get_config_leetcode_standard(self):
        """Test getting LeetCode standard config."""
        config = SubjectRegistry.get_config("leetcode", is_multiple_choice=False)

        assert config.name == "leetcode"
        assert config.target_model == LeetCodeProblem
        assert config.deck_prefix == "LeetCode"
        assert config.deck_prefix_mcq == "LeetCode_MCQ"
        assert config.combine_prompt is not None
        assert "leetcode" in config.target_questions or len(config.target_questions) > 0

    def test_get_config_cs_standard(self):
        """Test getting CS standard config."""
        config = SubjectRegistry.get_config("cs", is_multiple_choice=False)

        assert config.name == "cs"
        assert config.target_model == CSProblem
        assert config.deck_prefix == "CS"
        assert config.deck_prefix_mcq == "CS_MCQ"
        assert config.initial_prompt is not None

    def test_get_config_physics_standard(self):
        """Test getting Physics standard config."""
        config = SubjectRegistry.get_config("physics", is_multiple_choice=False)

        assert config.name == "physics"
        assert config.target_model == PhysicsProblem
        assert config.deck_prefix == "Physics"
        assert config.deck_prefix_mcq == "Physics_MCQ"

    def test_get_config_leetcode_mcq(self):
        """Test getting LeetCode MCQ config."""
        config = SubjectRegistry.get_config("leetcode", is_multiple_choice=True)

        assert config.name == "leetcode"
        assert config.target_model == MCQProblem
        assert config.combine_prompt is not None  # MCQ has combine prompt

    def test_get_config_cs_mcq(self):
        """Test getting CS MCQ config."""
        config = SubjectRegistry.get_config("cs", is_multiple_choice=True)

        assert config.name == "cs"
        assert config.target_model == MCQProblem

    def test_get_config_physics_mcq(self):
        """Test getting Physics MCQ config uses special physics MCQ prompt."""
        config = SubjectRegistry.get_config("physics", is_multiple_choice=True)

        assert config.name == "physics"
        assert config.target_model == MCQProblem
        # Physics MCQ has its own initial prompt
        assert config.initial_prompt is not None

    def test_get_config_invalid_subject_defaults_to_leetcode(self):
        """Test that invalid subject names default to leetcode."""
        config = SubjectRegistry.get_config("invalid_subject")

        assert config.name == "leetcode"
        assert config.target_model == LeetCodeProblem
        assert config.deck_prefix == "LeetCode"


class TestSubjectConfig:
    """Tests for SubjectConfig dataclass."""

    def test_subject_config_has_all_required_fields(self, leetcode_config):
        """Test that SubjectConfig has all required fields."""
        assert hasattr(leetcode_config, "name")
        assert hasattr(leetcode_config, "target_questions")
        assert hasattr(leetcode_config, "initial_prompt")
        assert hasattr(leetcode_config, "combine_prompt")
        assert hasattr(leetcode_config, "target_model")
        assert hasattr(leetcode_config, "deck_prefix")
        assert hasattr(leetcode_config, "deck_prefix_mcq")

    def test_subject_config_has_deck_prefix(self, leetcode_config):
        """Test that deck_prefix is set correctly."""
        assert leetcode_config.deck_prefix == "LeetCode"
        assert isinstance(leetcode_config.deck_prefix, str)

    def test_subject_config_has_combine_prompt(self, leetcode_config):
        """Test that combine_prompt is set for subjects that need it."""
        # LeetCode standard should have a combine prompt
        assert leetcode_config.combine_prompt is not None

    def test_subject_config_target_questions_is_dict(self, leetcode_config):
        """Test that target_questions is a categorized dictionary."""
        assert isinstance(leetcode_config.target_questions, dict)
        # Should have categories as keys
        for key, value in leetcode_config.target_questions.items():
            assert isinstance(key, str)
            assert isinstance(value, list)
