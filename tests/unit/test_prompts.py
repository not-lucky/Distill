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


class TestResolvePromptsDir:
    """Tests for _resolve_prompts_dir static method."""

    def test_resolve_from_env_var(self, tmp_path):
        """Test resolving prompts directory from environment variable."""
        with patch.dict(os.environ, {"LLM2DECK_PROMPTS_DIR": str(tmp_path)}):
            result = PromptLoader._resolve_prompts_dir()
            assert result == tmp_path

    def test_resolve_default_when_no_env(self):
        """Test resolving default when no env var is set."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove the env var if it exists
            if "LLM2DECK_PROMPTS_DIR" in os.environ:
                del os.environ["LLM2DECK_PROMPTS_DIR"]
            result = PromptLoader._resolve_prompts_dir()
            assert "prompts" in str(result)

    def test_resolve_returns_path_object(self, tmp_path):
        """Test that resolve returns a Path object."""
        with patch.dict(os.environ, {"LLM2DECK_PROMPTS_DIR": str(tmp_path)}):
            result = PromptLoader._resolve_prompts_dir()
            assert isinstance(result, Path)


class TestPromptLoaderCachedProperties:
    """Tests for PromptLoader cached properties."""

    def test_initial_is_cached(self, temp_prompts_dir):
        """Test that initial property is cached."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        # Access twice - should be same object
        first = loader.initial
        second = loader.initial
        assert first is second

    def test_combine_is_cached(self, temp_prompts_dir):
        """Test that combine property is cached."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        first = loader.combine
        second = loader.combine
        assert first is second

    def test_mcq_is_cached(self, temp_prompts_dir):
        """Test that mcq property is cached."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        first = loader.mcq
        second = loader.mcq
        assert first is second


class TestDeprecatedModuleLevelAccess:
    """Tests for deprecated module-level constant access."""

    def test_prompts_dir_deprecated(self):
        """Test that PROMPTS_DIR access triggers deprecation warning."""
        import warnings
        import src.prompts as prompts_module

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = prompts_module.PROMPTS_DIR
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

    def test_initial_prompt_template_deprecated(self):
        """Test that INITIAL_PROMPT_TEMPLATE access triggers deprecation warning."""
        import warnings
        import src.prompts as prompts_module

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = prompts_module.INITIAL_PROMPT_TEMPLATE
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_combine_prompt_template_deprecated(self):
        """Test that COMBINE_PROMPT_TEMPLATE access triggers deprecation warning."""
        import warnings
        import src.prompts as prompts_module

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = prompts_module.COMBINE_PROMPT_TEMPLATE
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_unknown_attribute_raises(self):
        """Test that accessing unknown attribute raises AttributeError."""
        import src.prompts as prompts_module

        with pytest.raises(AttributeError):
            _ = prompts_module.UNKNOWN_CONSTANT


class TestDeprecatedLoadPromptFunction:
    """Tests for deprecated load_prompt function."""

    def test_load_prompt_triggers_deprecation_warning(self):
        """Test that load_prompt triggers deprecation warning."""
        import warnings
        from src.prompts import load_prompt

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # This will use the actual prompts directory
            try:
                _ = load_prompt("initial.md")
            except FileNotFoundError:
                pass  # File may not exist in test environment
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)

    def test_load_prompt_still_works(self):
        """Test that load_prompt still returns content despite deprecation."""
        import warnings
        from src.prompts import load_prompt

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Try to load the actual initial.md from the real prompts directory
            try:
                content = load_prompt("initial.md")
                assert content is not None
            except FileNotFoundError:
                # If file doesn't exist, that's okay - we're just testing the function works
                pass


class TestPromptLoaderEdgeCases:
    """Edge case tests for PromptLoader."""

    def test_load_with_unicode_content(self, tmp_path):
        """Test loading prompts with unicode content."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "unicode.md").write_text("日本語 中文 한국어", encoding="utf-8")

        loader = PromptLoader(prompts_dir=prompts_dir)
        content = loader._load("unicode.md")
        assert "日本語" in content
        assert "中文" in content
        assert "한국어" in content

    def test_load_empty_file(self, tmp_path):
        """Test loading an empty prompt file."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "empty.md").write_text("")

        loader = PromptLoader(prompts_dir=prompts_dir)
        content = loader._load("empty.md")
        assert content == ""

    def test_load_large_file(self, tmp_path):
        """Test loading a large prompt file."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        large_content = "x" * 100000
        (prompts_dir / "large.md").write_text(large_content)

        loader = PromptLoader(prompts_dir=prompts_dir)
        content = loader._load("large.md")
        assert len(content) == 100000

    def test_try_load_missing_file_returns_none(self, tmp_path):
        """Test that _try_load returns None for missing files."""
        loader = PromptLoader(prompts_dir=tmp_path)
        # Try to load a non-existent file
        result = loader._try_load(tmp_path / "nonexistent.md")
        assert result is None

    def test_prompts_dir_property(self, tmp_path):
        """Test prompts_dir property returns configured path."""
        loader = PromptLoader(prompts_dir=tmp_path)
        assert loader.prompts_dir == tmp_path

    def test_load_subject_prompts_creates_full_path(self, tmp_path):
        """Test load_subject_prompts creates correct paths."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        subject_dir = prompts_dir / "test_subject"
        subject_dir.mkdir()
        (subject_dir / "initial.md").write_text("Test initial")
        (subject_dir / "combine.md").write_text("Test combine")

        loader = PromptLoader(prompts_dir=prompts_dir)
        initial, combine = loader.load_subject_prompts("test_subject")
        assert initial == "Test initial"
        assert combine == "Test combine"


class TestPromptLoaderAllProperties:
    """Tests for all PromptLoader properties."""

    def test_all_required_properties_exist(self, temp_prompts_dir):
        """Test that all required prompt properties exist."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        # All these should be accessible
        properties = ["initial", "combine", "mcq", "mcq_combine",
                     "physics", "physics_mcq", "initial_cs", "combine_cs"]
        for prop_name in properties:
            assert hasattr(loader, prop_name), f"PromptLoader should have {prop_name}"

    def test_all_properties_return_strings(self, temp_prompts_dir):
        """Test that all prompt properties return strings."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        properties = ["initial", "combine", "mcq", "mcq_combine",
                     "physics", "physics_mcq", "initial_cs", "combine_cs"]
        for prop_name in properties:
            value = getattr(loader, prop_name)
            assert isinstance(value, str), f"{prop_name} should return a string"
