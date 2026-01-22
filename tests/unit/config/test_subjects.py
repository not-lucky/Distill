"""Tests for config/subjects.py."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

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
        """Test getting available subjects."""
        registry = SubjectRegistry()
        available = registry.get_available_subjects()

        assert "leetcode" in available
        assert "cs" in available
        assert "custom" in available
        assert "physics" not in available  # Disabled

    def test_is_valid_subject_enabled(self, mock_config):
        """Test is_valid_subject for enabled subjects."""
        registry = SubjectRegistry()

        assert registry.is_valid_subject("leetcode") is True
        assert registry.is_valid_subject("cs") is True
        assert registry.is_valid_subject("custom") is True

    def test_is_valid_subject_disabled(self, mock_config):
        """Test is_valid_subject for disabled subjects."""
        registry = SubjectRegistry()

        assert registry.is_valid_subject("physics") is False

    def test_is_valid_subject_unknown(self, mock_config):
        """Test is_valid_subject for unknown subjects."""
        registry = SubjectRegistry()

        assert registry.is_valid_subject("nonexistent") is False

    def test_is_valid_subject_builtin_not_in_config(self):
        """Test that built-in subjects are valid even if not in config."""
        with patch("src.config.subjects.load_config") as mock_load:
            mock_cfg = MagicMock()
            mock_cfg.subjects = {}  # Empty config
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()

            # Built-in subjects should still be valid
            assert registry.is_valid_subject("leetcode") is True
            assert registry.is_valid_subject("cs") is True
            assert registry.is_valid_subject("physics") is True


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
        """Test getting LeetCode configuration."""
        config = registry.get_config("leetcode", is_multiple_choice=False)

        assert config.name == "leetcode"
        assert config.target_model == LeetCodeProblem
        assert config.deck_prefix == "LeetCode"
        assert config.deck_prefix_mcq == "LeetCode_MCQ"
        assert config.target_questions is not None

    def test_get_cs_config(self, registry):
        """Test getting CS configuration."""
        config = registry.get_config("cs", is_multiple_choice=False)

        assert config.name == "cs"
        assert config.target_model == CSProblem
        assert config.deck_prefix == "CS"

    def test_get_physics_config(self, registry):
        """Test getting Physics configuration."""
        config = registry.get_config("physics", is_multiple_choice=False)

        assert config.name == "physics"
        assert config.target_model == PhysicsProblem
        assert config.deck_prefix == "Physics"

    def test_get_mcq_config(self, registry):
        """Test getting MCQ configuration."""
        config = registry.get_config("leetcode", is_multiple_choice=True)

        assert config.target_model == MCQProblem
        assert config.initial_prompt is not None  # MCQ prompt

    def test_get_unknown_subject_raises(self, registry):
        """Test getting unknown subject raises ValueError."""
        with pytest.raises(ValueError, match="Unknown subject"):
            registry.get_config("nonexistent")


class TestGetCustomConfig:
    """Tests for getting custom subject configurations."""

    def test_get_custom_subject_config(self, tmp_path):
        """Test getting custom subject configuration."""
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

            assert config.name == "biology"
            assert config.target_model == GenericProblem
            assert config.deck_prefix == "Biology"
            assert config.deck_prefix_mcq == "Biology_MCQ"
            assert "Category1" in config.target_questions
            assert len(config.target_questions["Category1"]) == 2

    def test_custom_subject_default_deck_prefix(self, tmp_path):
        """Test custom subject uses title case name as default prefix."""
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

            assert config.deck_prefix == "My_Subject"


class TestLoadQuestionsFile:
    """Tests for _load_questions_file method."""

    def test_load_categorized_format(self, tmp_path):
        """Test loading categorized questions format."""
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

            assert "Arrays" in questions
            assert "Strings" in questions
            assert questions["Arrays"] == ["Two Sum", "Binary Search"]

    def test_load_flat_list_format(self, tmp_path):
        """Test loading flat list format (wrapped in General category)."""
        questions_file = tmp_path / "questions.json"
        questions_file.write_text(json.dumps(["Q1", "Q2", "Q3"]))

        with patch("src.config.subjects.load_config") as mock_load:
            mock_cfg = MagicMock()
            mock_cfg.subjects = {}
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()
            questions = registry._load_questions_file(str(questions_file))

            assert "General" in questions
            assert questions["General"] == ["Q1", "Q2", "Q3"]

    def test_load_missing_file_raises(self, tmp_path):
        """Test loading non-existent file raises FileNotFoundError."""
        with patch("src.config.subjects.load_config") as mock_load:
            mock_cfg = MagicMock()
            mock_cfg.subjects = {}
            mock_load.return_value = mock_cfg

            registry = SubjectRegistry()

            with pytest.raises(FileNotFoundError):
                registry._load_questions_file(str(tmp_path / "missing.json"))

    def test_load_invalid_format_raises(self, tmp_path):
        """Test loading invalid format raises ValueError."""
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
        """Test creating SubjectConfig."""
        config = SubjectConfig(
            name="test",
            target_questions={"Cat": ["Q1"]},
            initial_prompt="Initial",
            combine_prompt="Combine",
            target_model=LeetCodeProblem,
            deck_prefix="Test",
            deck_prefix_mcq="Test_MCQ",
        )

        assert config.name == "test"
        assert config.target_questions == {"Cat": ["Q1"]}
        assert config.initial_prompt == "Initial"
        assert config.combine_prompt == "Combine"
        assert config.target_model == LeetCodeProblem
        assert config.deck_prefix == "Test"
        assert config.deck_prefix_mcq == "Test_MCQ"

    def test_subject_config_none_prompts(self):
        """Test SubjectConfig with None prompts."""
        config = SubjectConfig(
            name="test",
            target_questions={},
            initial_prompt=None,
            combine_prompt=None,
            target_model=GenericProblem,
            deck_prefix="Test",
            deck_prefix_mcq="Test_MCQ",
        )

        assert config.initial_prompt is None
        assert config.combine_prompt is None


class TestGetSubjectConfigFunction:
    """Tests for get_subject_config convenience function."""

    def test_get_subject_config_leetcode(self):
        """Test getting leetcode config via convenience function."""
        with patch("src.config.subjects.load_config") as mock_load:
            from src.config.loader import SubjectSettings

            mock_cfg = MagicMock()
            mock_cfg.subjects = {
                "leetcode": SubjectSettings(enabled=True),
            }
            mock_load.return_value = mock_cfg

            config = get_subject_config("leetcode")

            assert config.name == "leetcode"
            assert config.target_model == LeetCodeProblem

    def test_get_subject_config_mcq(self):
        """Test getting MCQ config via convenience function."""
        with patch("src.config.subjects.load_config") as mock_load:
            from src.config.loader import SubjectSettings

            mock_cfg = MagicMock()
            mock_cfg.subjects = {
                "cs": SubjectSettings(enabled=True),
            }
            mock_load.return_value = mock_cfg

            config = get_subject_config("cs", is_multiple_choice=True)

            assert config.target_model == MCQProblem


class TestBuiltinSubjects:
    """Tests for BUILTIN_SUBJECTS constant."""

    def test_builtin_subjects_contains_expected(self):
        """Test that BUILTIN_SUBJECTS contains expected subjects."""
        assert "leetcode" in BUILTIN_SUBJECTS
        assert "cs" in BUILTIN_SUBJECTS
        assert "physics" in BUILTIN_SUBJECTS

    def test_builtin_subjects_is_set(self):
        """Test that BUILTIN_SUBJECTS is a set."""
        assert isinstance(BUILTIN_SUBJECTS, set)
