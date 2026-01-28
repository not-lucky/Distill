"""Tests for document processing module."""

import pytest
from pathlib import Path

from src.document import (
    DocumentInfo,
    discover_documents,
    get_document_count,
    preview_deck_structure,
    _filename_to_title,
    _dirname_to_deck_name,
    SUPPORTED_EXTENSIONS,
)


class TestFilenameToTitle:
    """Tests for filename to title conversion."""

    def test_simple_filename(self):
        assert _filename_to_title("intro.md") == "Intro"

    def test_hyphenated_filename(self):
        assert _filename_to_title("jsx-intro.md") == "JsxIntro"

    def test_underscored_filename(self):
        assert _filename_to_title("use_state.md") == "UseState"

    def test_numbered_prefix(self):
        assert _filename_to_title("01-getting-started.md") == "GettingStarted"

    def test_complex_filename(self):
        assert _filename_to_title("02_advanced-hooks_tutorial.md") == "AdvancedHooksTutorial"


class TestDirnameToDeckName:
    """Tests for directory name to deck name conversion."""

    def test_simple_dirname(self):
        assert _dirname_to_deck_name("react") == "React"

    def test_hyphenated_dirname(self):
        assert _dirname_to_deck_name("react-tutorial") == "ReactTutorial"

    def test_underscored_dirname(self):
        assert _dirname_to_deck_name("my_awesome_deck") == "MyAwesomeDeck"


class TestDocumentInfo:
    """Tests for DocumentInfo dataclass."""

    def test_full_deck_path(self):
        doc = DocumentInfo(
            file_path=Path("/tmp/test.md"),
            title="UseState",
            deck_name="ReactTutorial",
            subdeck_path=["Hooks"],
            content="test content",
        )
        assert doc.full_deck_path == "ReactTutorial::Hooks::UseState"

    def test_full_deck_path_no_subdeck(self):
        doc = DocumentInfo(
            file_path=Path("/tmp/test.md"),
            title="Intro",
            deck_name="React",
            subdeck_path=[],
            content="test content",
        )
        assert doc.full_deck_path == "React::Intro"

    def test_topic_path(self):
        doc = DocumentInfo(
            file_path=Path("/tmp/test.md"),
            title="UseState",
            deck_name="ReactTutorial",
            subdeck_path=["Hooks"],
            content="test content",
        )
        # Topic path uses humanized format
        assert "React Tutorial" in doc.topic_path or "Reacttutorial" in doc.topic_path

    def test_relative_path(self):
        doc = DocumentInfo(
            file_path=Path("/tmp/docs/hooks/useState.md"),
            title="UseState",
            deck_name="Docs",
            subdeck_path=["Hooks"],
            content="test content",
        )
        assert doc.relative_path == "Hooks/useState.md"


class TestDiscoverDocuments:
    """Tests for document discovery."""

    def test_discover_single_file(self, tmp_path):
        # Create a test file
        test_file = tmp_path / "intro.md"
        test_file.write_text("# Introduction\n\nThis is a test.")

        docs = list(discover_documents(tmp_path))
        assert len(docs) == 1
        assert docs[0].title == "Intro"
        assert docs[0].content == "# Introduction\n\nThis is a test."

    def test_discover_nested_structure(self, tmp_path):
        # Create nested structure
        (tmp_path / "basics").mkdir()
        (tmp_path / "advanced").mkdir()
        (tmp_path / "basics" / "intro.md").write_text("Intro content")
        (tmp_path / "basics" / "setup.md").write_text("Setup content")
        (tmp_path / "advanced" / "hooks.md").write_text("Hooks content")

        docs = list(discover_documents(tmp_path))
        assert len(docs) == 3

        deck_paths = {doc.full_deck_path for doc in docs}
        deck_name = docs[0].deck_name  # All should have same deck name
        assert f"{deck_name}::Basics::Intro" in deck_paths
        assert f"{deck_name}::Basics::Setup" in deck_paths
        assert f"{deck_name}::Advanced::Hooks" in deck_paths

    def test_discover_filters_by_extension(self, tmp_path):
        (tmp_path / "included.md").write_text("included")
        (tmp_path / "excluded.py").write_text("excluded")
        (tmp_path / "also_included.txt").write_text("also included")

        docs = list(discover_documents(tmp_path))
        assert len(docs) == 2

    def test_discover_custom_extensions(self, tmp_path):
        (tmp_path / "included.py").write_text("included")
        (tmp_path / "excluded.md").write_text("excluded")

        docs = list(discover_documents(tmp_path, extensions={".py"}))
        assert len(docs) == 1
        assert docs[0].file_path.suffix == ".py"

    def test_discover_skips_empty_files(self, tmp_path):
        (tmp_path / "empty.md").write_text("")
        (tmp_path / "whitespace.md").write_text("   \n\n  ")
        (tmp_path / "content.md").write_text("actual content")

        docs = list(discover_documents(tmp_path))
        assert len(docs) == 1
        assert docs[0].title == "Content"

    def test_discover_skips_hidden_files(self, tmp_path):
        (tmp_path / ".hidden.md").write_text("hidden")
        (tmp_path / "visible.md").write_text("visible")

        docs = list(discover_documents(tmp_path))
        assert len(docs) == 1
        assert docs[0].title == "Visible"

    def test_discover_nonexistent_directory(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            list(discover_documents(tmp_path / "nonexistent"))

    def test_discover_file_not_directory(self, tmp_path):
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        with pytest.raises(ValueError):
            list(discover_documents(test_file))


class TestGetDocumentCount:
    """Tests for document counting."""

    def test_count_documents(self, tmp_path):
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "c.txt").write_text("c")

        assert get_document_count(tmp_path) == 3


class TestPreviewDeckStructure:
    """Tests for deck structure preview."""

    def test_preview_returns_tuples(self, tmp_path):
        (tmp_path / "intro.md").write_text("intro")
        (tmp_path / "setup.md").write_text("setup")

        preview = preview_deck_structure(tmp_path)
        assert len(preview) == 2
        assert all(isinstance(item, tuple) and len(item) == 2 for item in preview)

    def test_preview_respects_max_items(self, tmp_path):
        for i in range(10):
            (tmp_path / f"file{i}.md").write_text(f"content {i}")

        preview = preview_deck_structure(tmp_path, max_items=3)
        assert len(preview) == 3
