"""Tests for PromptLoader in src/prompts.py."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from src.prompts import PromptLoader, prompts


class TestPromptLoader:
    """Tests for PromptLoader class."""

    def test_init_with_custom_dir(self, temp_prompts_dir):
        """Test PromptLoader initialization with custom directory."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert loader.prompts_dir == temp_prompts_dir

    def test_init_with_env_var(self, temp_prompts_dir):
        """Test PromptLoader uses environment variable when set."""
        with patch.dict(os.environ, {"LLM2DECK_PROMPTS_DIR": str(temp_prompts_dir)}):
            loader = PromptLoader()
            assert loader.prompts_dir == temp_prompts_dir

    def test_default_prompts_dir(self):
        """Test default prompts directory resolution."""
        loader = PromptLoader()
        expected = Path(__file__).parent.parent / "src" / "data" / "prompts"
        # The loader should resolve to src/data/prompts
        assert "prompts" in str(loader.prompts_dir)

    def test_load_initial_prompt(self, temp_prompts_dir):
        """Test loading initial prompt template."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        content = loader.initial
        assert "Generate cards" in content
        assert "{question}" in content
        assert "{schema}" in content

    def test_load_combine_prompt(self, temp_prompts_dir):
        """Test loading combine prompt template."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        content = loader.combine
        assert "Combine cards" in content
        assert "{inputs}" in content

    def test_load_cs_prompts(self, temp_prompts_dir):
        """Test loading CS-specific prompts."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert "CS prompt" in loader.initial_cs
        assert "CS combine" in loader.combine_cs

    def test_load_mcq_prompts(self, temp_prompts_dir):
        """Test loading MCQ prompts."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert "MCQ prompt" in loader.mcq
        assert "MCQ combine" in loader.mcq_combine

    def test_load_physics_prompts(self, temp_prompts_dir):
        """Test loading physics prompts."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert "Physics prompt" in loader.physics
        assert "Physics MCQ" in loader.physics_mcq

    def test_load_missing_prompt_raises(self, temp_prompts_dir):
        """Test that loading a missing prompt file raises FileNotFoundError."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        with pytest.raises(FileNotFoundError):
            loader._load("nonexistent.md")

    def test_cached_property_caching(self, temp_prompts_dir):
        """Test that cached_property caches the loaded content."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        # Access initial twice - should be cached
        first_access = loader.initial
        second_access = loader.initial
        assert first_access is second_access

    def test_load_subject_prompts(self, temp_prompts_dir):
        """Test loading subject-specific prompts."""
        # Create a custom subject directory
        subject_dir = temp_prompts_dir / "biology"
        subject_dir.mkdir()
        (subject_dir / "initial.md").write_text("Biology initial prompt")
        (subject_dir / "combine.md").write_text("Biology combine prompt")

        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        initial, combine = loader.load_subject_prompts("biology")

        assert initial == "Biology initial prompt"
        assert combine == "Biology combine prompt"

    def test_load_subject_prompts_with_custom_dir(self, tmp_path):
        """Test loading subject prompts from a custom directory path."""
        custom_dir = tmp_path / "custom_prompts"
        custom_dir.mkdir()
        (custom_dir / "initial.md").write_text("Custom initial")
        (custom_dir / "combine.md").write_text("Custom combine")

        loader = PromptLoader()
        initial, combine = loader.load_subject_prompts("any", str(custom_dir))

        assert initial == "Custom initial"
        assert combine == "Custom combine"

    def test_load_subject_prompts_missing_files(self, temp_prompts_dir):
        """Test loading subject prompts when files don't exist returns None."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        initial, combine = loader.load_subject_prompts("nonexistent_subject")

        assert initial is None
        assert combine is None

    def test_load_subject_mcq_prompts(self, temp_prompts_dir):
        """Test loading MCQ prompts for a subject."""
        # Create a custom subject directory
        subject_dir = temp_prompts_dir / "chemistry"
        subject_dir.mkdir()
        (subject_dir / "mcq.md").write_text("Chemistry MCQ prompt")
        (subject_dir / "mcq_combine.md").write_text("Chemistry MCQ combine")

        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        initial, combine = loader.load_subject_mcq_prompts("chemistry")

        assert initial == "Chemistry MCQ prompt"
        assert combine == "Chemistry MCQ combine"

    def test_load_subject_mcq_prompts_missing(self, temp_prompts_dir):
        """Test loading MCQ prompts when files don't exist returns None."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        initial, combine = loader.load_subject_mcq_prompts("nonexistent")

        assert initial is None
        assert combine is None

    def test_try_load_returns_none_for_missing(self, temp_prompts_dir):
        """Test _try_load returns None for missing files."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        result = loader._try_load(temp_prompts_dir / "missing.md")
        assert result is None

    def test_try_load_returns_content_for_existing(self, temp_prompts_dir):
        """Test _try_load returns content for existing files."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        result = loader._try_load(temp_prompts_dir / "initial.md")
        assert result is not None
        assert "Generate cards" in result


class TestPromptsSingleton:
    """Tests for the prompts singleton instance."""

    def test_prompts_singleton_exists(self):
        """Test that the prompts singleton is available."""
        assert prompts is not None
        assert isinstance(prompts, PromptLoader)

    def test_prompts_singleton_has_prompts_dir(self):
        """Test that the prompts singleton has a prompts_dir property."""
        assert prompts.prompts_dir is not None
        assert isinstance(prompts.prompts_dir, Path)
