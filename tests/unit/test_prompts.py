"""Tests for PromptLoader in src/prompts.py."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from assertpy import assert_that

from src.prompts import PromptLoader, prompts


class TestPromptLoader:
    """Tests for PromptLoader class."""

    def test_init_with_custom_dir(self, temp_prompts_dir):
        """
        Given a custom prompts directory
        When PromptLoader is initialized
        Then the custom directory is used
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert_that(loader.prompts_dir).is_equal_to(temp_prompts_dir)

    def test_init_with_env_var(self, temp_prompts_dir):
        """
        Given LLM2DECK_PROMPTS_DIR environment variable set
        When PromptLoader is initialized without arguments
        Then the env var directory is used
        """
        with patch.dict(os.environ, {"LLM2DECK_PROMPTS_DIR": str(temp_prompts_dir)}):
            loader = PromptLoader()
            assert_that(loader.prompts_dir).is_equal_to(temp_prompts_dir)

    def test_default_prompts_dir(self):
        """
        Given no environment variable or argument
        When PromptLoader is initialized
        Then default prompts directory is resolved
        """
        loader = PromptLoader()
        expected = Path(__file__).parent.parent / "src" / "data" / "prompts"
        assert_that(str(loader.prompts_dir)).contains("prompts")

    def test_load_initial_prompt(self, temp_prompts_dir):
        """
        Given a prompts directory with initial.md
        When initial property is accessed
        Then template content is returned with placeholders
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        content = loader.initial
        assert_that(content).contains("Generate cards")
        assert_that(content).contains("{question}")
        assert_that(content).contains("{schema}")

    def test_load_combine_prompt(self, temp_prompts_dir):
        """
        Given a prompts directory with combine.md
        When combine property is accessed
        Then template content is returned with placeholders
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        content = loader.combine
        assert_that(content).contains("Combine cards")
        assert_that(content).contains("{inputs}")

    def test_load_cs_prompts(self, temp_prompts_dir):
        """
        Given a prompts directory with CS prompts
        When CS properties are accessed
        Then CS-specific content is returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert_that(loader.initial_cs).contains("CS prompt")
        assert_that(loader.combine_cs).contains("CS combine")

    def test_load_mcq_prompts(self, temp_prompts_dir):
        """
        Given a prompts directory with MCQ prompts
        When MCQ properties are accessed
        Then MCQ content is returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert_that(loader.mcq).contains("MCQ prompt")
        assert_that(loader.mcq_combine).contains("MCQ combine")

    def test_load_physics_prompts(self, temp_prompts_dir):
        """
        Given a prompts directory with physics prompts
        When physics properties are accessed
        Then physics content is returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert_that(loader.physics).contains("Physics prompt")
        assert_that(loader.physics_mcq).contains("Physics MCQ")

    def test_load_missing_prompt_raises(self, temp_prompts_dir):
        """
        Given a prompts directory
        When loading a nonexistent file
        Then FileNotFoundError is raised
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        with pytest.raises(FileNotFoundError):
            loader._load("nonexistent.md")

    def test_cached_property_caching(self, temp_prompts_dir):
        """
        Given a PromptLoader
        When accessing a property twice
        Then the same cached object is returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        first_access = loader.initial
        second_access = loader.initial
        assert_that(first_access).is_same_as(second_access)

    def test_load_subject_prompts(self, temp_prompts_dir):
        """
        Given a subject directory with prompts
        When load_subject_prompts is called
        Then subject-specific prompts are returned
        """
        subject_dir = temp_prompts_dir / "biology"
        subject_dir.mkdir()
        (subject_dir / "initial.md").write_text("Biology initial prompt")
        (subject_dir / "combine.md").write_text("Biology combine prompt")

        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        initial, combine = loader.load_subject_prompts("biology")

        assert_that(initial).is_equal_to("Biology initial prompt")
        assert_that(combine).is_equal_to("Biology combine prompt")

    def test_load_subject_prompts_with_custom_dir(self, tmp_path):
        """
        Given a custom directory path
        When load_subject_prompts is called with that path
        Then prompts from the custom directory are loaded
        """
        custom_dir = tmp_path / "custom_prompts"
        custom_dir.mkdir()
        (custom_dir / "initial.md").write_text("Custom initial")
        (custom_dir / "combine.md").write_text("Custom combine")

        loader = PromptLoader()
        initial, combine = loader.load_subject_prompts("any", str(custom_dir))

        assert_that(initial).is_equal_to("Custom initial")
        assert_that(combine).is_equal_to("Custom combine")

    def test_load_subject_prompts_missing_files(self, temp_prompts_dir):
        """
        Given a nonexistent subject
        When load_subject_prompts is called
        Then None is returned for both prompts
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        initial, combine = loader.load_subject_prompts("nonexistent_subject")

        assert_that(initial).is_none()
        assert_that(combine).is_none()

    def test_load_subject_mcq_prompts(self, temp_prompts_dir):
        """
        Given a subject with MCQ prompts
        When load_subject_mcq_prompts is called
        Then MCQ prompts are returned
        """
        subject_dir = temp_prompts_dir / "chemistry"
        subject_dir.mkdir()
        (subject_dir / "mcq.md").write_text("Chemistry MCQ prompt")
        (subject_dir / "mcq_combine.md").write_text("Chemistry MCQ combine")

        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        initial, combine = loader.load_subject_mcq_prompts("chemistry")

        assert_that(initial).is_equal_to("Chemistry MCQ prompt")
        assert_that(combine).is_equal_to("Chemistry MCQ combine")

    def test_load_subject_mcq_prompts_missing(self, temp_prompts_dir):
        """
        Given a nonexistent subject
        When load_subject_mcq_prompts is called
        Then None is returned for both prompts
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        initial, combine = loader.load_subject_mcq_prompts("nonexistent")

        assert_that(initial).is_none()
        assert_that(combine).is_none()

    def test_try_load_returns_none_for_missing(self, temp_prompts_dir):
        """
        Given a missing file path
        When _try_load is called
        Then None is returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        result = loader._try_load(temp_prompts_dir / "missing.md")
        assert_that(result).is_none()

    def test_try_load_returns_content_for_existing(self, temp_prompts_dir):
        """
        Given an existing file path
        When _try_load is called
        Then file content is returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        result = loader._try_load(temp_prompts_dir / "initial.md")
        assert_that(result).is_not_none()
        assert_that(result).contains("Generate cards")


class TestPromptsSingleton:
    """Tests for the prompts singleton instance."""

    def test_prompts_singleton_exists(self):
        """
        Given the prompts module
        When accessing the prompts singleton
        Then it is a PromptLoader instance
        """
        assert_that(prompts).is_not_none()
        assert_that(prompts).is_instance_of(PromptLoader)

    def test_prompts_singleton_has_prompts_dir(self):
        """
        Given the prompts singleton
        When accessing prompts_dir property
        Then it is a Path object
        """
        assert_that(prompts.prompts_dir).is_not_none()
        assert_that(prompts.prompts_dir).is_instance_of(Path)


class TestResolvePromptsDir:
    """Tests for _resolve_prompts_dir static method."""

    def test_resolve_from_env_var(self, tmp_path):
        """
        Given LLM2DECK_PROMPTS_DIR environment variable
        When _resolve_prompts_dir is called
        Then env var path is returned
        """
        with patch.dict(os.environ, {"LLM2DECK_PROMPTS_DIR": str(tmp_path)}):
            result = PromptLoader._resolve_prompts_dir()
            assert_that(result).is_equal_to(tmp_path)

    def test_resolve_default_when_no_env(self):
        """
        Given no environment variable
        When _resolve_prompts_dir is called
        Then default path containing 'prompts' is returned
        """
        with patch.dict(os.environ, {}, clear=False):
            if "LLM2DECK_PROMPTS_DIR" in os.environ:
                del os.environ["LLM2DECK_PROMPTS_DIR"]
            result = PromptLoader._resolve_prompts_dir()
            assert_that(str(result)).contains("prompts")

    def test_resolve_returns_path_object(self, tmp_path):
        """
        Given a configured environment
        When _resolve_prompts_dir is called
        Then a Path object is returned
        """
        with patch.dict(os.environ, {"LLM2DECK_PROMPTS_DIR": str(tmp_path)}):
            result = PromptLoader._resolve_prompts_dir()
            assert_that(result).is_instance_of(Path)


class TestPromptLoaderCachedProperties:
    """Tests for PromptLoader cached properties."""

    def test_initial_is_cached(self, temp_prompts_dir):
        """
        Given a PromptLoader
        When initial property is accessed twice
        Then same object is returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        first = loader.initial
        second = loader.initial
        assert_that(first).is_same_as(second)

    def test_combine_is_cached(self, temp_prompts_dir):
        """
        Given a PromptLoader
        When combine property is accessed twice
        Then same object is returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        first = loader.combine
        second = loader.combine
        assert_that(first).is_same_as(second)

    def test_mcq_is_cached(self, temp_prompts_dir):
        """
        Given a PromptLoader
        When mcq property is accessed twice
        Then same object is returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        first = loader.mcq
        second = loader.mcq
        assert_that(first).is_same_as(second)


class TestDeprecatedModuleLevelAccess:
    """Tests for deprecated module-level constant access."""

    def test_prompts_dir_deprecated(self):
        """
        Given the prompts module
        When accessing PROMPTS_DIR constant
        Then a DeprecationWarning is triggered
        """
        import warnings
        import src.prompts as prompts_module

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = prompts_module.PROMPTS_DIR
            assert_that(w).is_length(1)
            assert_that(issubclass(w[0].category, DeprecationWarning)).is_true()
            assert_that("deprecated" in str(w[0].message).lower()).is_true()

    def test_initial_prompt_template_deprecated(self):
        """
        Given the prompts module
        When accessing INITIAL_PROMPT_TEMPLATE constant
        Then a DeprecationWarning is triggered
        """
        import warnings
        import src.prompts as prompts_module

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = prompts_module.INITIAL_PROMPT_TEMPLATE
            assert_that(w).is_length(1)
            assert_that(issubclass(w[0].category, DeprecationWarning)).is_true()

    def test_combine_prompt_template_deprecated(self):
        """
        Given the prompts module
        When accessing COMBINE_PROMPT_TEMPLATE constant
        Then a DeprecationWarning is triggered
        """
        import warnings
        import src.prompts as prompts_module

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = prompts_module.COMBINE_PROMPT_TEMPLATE
            assert_that(w).is_length(1)
            assert_that(issubclass(w[0].category, DeprecationWarning)).is_true()

    def test_unknown_attribute_raises(self):
        """
        Given the prompts module
        When accessing unknown attribute
        Then AttributeError is raised
        """
        import src.prompts as prompts_module

        with pytest.raises(AttributeError):
            _ = prompts_module.UNKNOWN_CONSTANT


class TestDeprecatedLoadPromptFunction:
    """Tests for deprecated load_prompt function."""

    def test_load_prompt_triggers_deprecation_warning(self):
        """
        Given the deprecated load_prompt function
        When called
        Then a DeprecationWarning is triggered
        """
        import warnings
        from src.prompts import load_prompt

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                _ = load_prompt("initial.md")
            except FileNotFoundError:
                pass
            assert_that(any(issubclass(warning.category, DeprecationWarning) for warning in w)).is_true()

    def test_load_prompt_still_works(self):
        """
        Given the deprecated load_prompt function
        When called with valid file
        Then content is still returned
        """
        import warnings
        from src.prompts import load_prompt

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                content = load_prompt("initial.md")
                assert_that(content).is_not_none()
            except FileNotFoundError:
                pass


class TestPromptLoaderEdgeCases:
    """Edge case tests for PromptLoader."""

    def test_load_with_unicode_content(self, tmp_path):
        """
        Given a prompt file with unicode content
        When loaded
        Then unicode is preserved
        """
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "unicode.md").write_text("日本語 中文 한국어", encoding="utf-8")

        loader = PromptLoader(prompts_dir=prompts_dir)
        content = loader._load("unicode.md")
        assert_that(content).contains("日本語")
        assert_that(content).contains("中文")
        assert_that(content).contains("한국어")

    def test_load_empty_file(self, tmp_path):
        """
        Given an empty prompt file
        When loaded
        Then empty string is returned
        """
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "empty.md").write_text("")

        loader = PromptLoader(prompts_dir=prompts_dir)
        content = loader._load("empty.md")
        assert_that(content).is_empty()

    def test_load_large_file(self, tmp_path):
        """
        Given a large prompt file
        When loaded
        Then full content is returned
        """
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        large_content = "x" * 100000
        (prompts_dir / "large.md").write_text(large_content)

        loader = PromptLoader(prompts_dir=prompts_dir)
        content = loader._load("large.md")
        assert_that(content).is_length(100000)

    def test_try_load_missing_file_returns_none(self, tmp_path):
        """
        Given a missing file
        When _try_load is called
        Then None is returned
        """
        loader = PromptLoader(prompts_dir=tmp_path)
        result = loader._try_load(tmp_path / "nonexistent.md")
        assert_that(result).is_none()

    def test_prompts_dir_property(self, tmp_path):
        """
        Given a configured PromptLoader
        When accessing prompts_dir property
        Then configured path is returned
        """
        loader = PromptLoader(prompts_dir=tmp_path)
        assert_that(loader.prompts_dir).is_equal_to(tmp_path)

    def test_load_subject_prompts_creates_full_path(self, tmp_path):
        """
        Given a subject with prompts
        When load_subject_prompts is called
        Then correct paths are created and loaded
        """
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        subject_dir = prompts_dir / "test_subject"
        subject_dir.mkdir()
        (subject_dir / "initial.md").write_text("Test initial")
        (subject_dir / "combine.md").write_text("Test combine")

        loader = PromptLoader(prompts_dir=prompts_dir)
        initial, combine = loader.load_subject_prompts("test_subject")
        assert_that(initial).is_equal_to("Test initial")
        assert_that(combine).is_equal_to("Test combine")


class TestPromptLoaderAllProperties:
    """Tests for all PromptLoader properties."""

    def test_all_required_properties_exist(self, temp_prompts_dir):
        """
        Given a PromptLoader
        When checking for required properties
        Then all properties exist
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        properties = ["initial", "combine", "mcq", "mcq_combine",
                     "physics", "physics_mcq", "initial_cs", "combine_cs"]
        for prop_name in properties:
            assert_that(hasattr(loader, prop_name)).described_as(
                f"PromptLoader should have {prop_name}"
            ).is_true()

    def test_all_properties_return_strings(self, temp_prompts_dir):
        """
        Given a PromptLoader
        When accessing all properties
        Then strings are returned
        """
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        properties = ["initial", "combine", "mcq", "mcq_combine",
                     "physics", "physics_mcq", "initial_cs", "combine_cs"]
        for prop_name in properties:
            value = getattr(loader, prop_name)
            assert_that(value).described_as(
                f"{prop_name} should return a string"
            ).is_instance_of(str)
