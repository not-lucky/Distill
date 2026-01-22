"""Tests for services/export.py."""

import json
import pytest
from pathlib import Path

from assertpy import assert_that

from src.services.export import ExportService, ExportResult


class TestExportResult:
    """Tests for ExportResult dataclass."""

    def test_create_success_result(self):
        """
        Given success parameters
        When ExportResult is created
        Then success fields are set correctly
        """
        result = ExportResult(
            success=True,
            exported_count=5,
        )

        assert_that(result.success).is_true()
        assert_that(result.exported_count).is_equal_to(5)
        assert_that(result.error).is_none()

    def test_create_failure_result(self):
        """
        Given failure parameters
        When ExportResult is created
        Then failure fields are set correctly
        """
        result = ExportResult(
            success=False,
            exported_count=0,
            error="Source not found",
        )

        assert_that(result.success).is_false()
        assert_that(result.exported_count).is_equal_to(0)
        assert_that(result.error).is_equal_to("Source not found")


class TestExportServiceInit:
    """Tests for ExportService initialization."""

    def test_init_with_paths(self, tmp_path):
        """
        Given source and target directory paths
        When ExportService is initialized
        Then both paths are stored correctly
        """
        source = tmp_path / "source"
        target = tmp_path / "target"

        service = ExportService(source_dir=source, target_dir=target)

        assert_that(service.source_dir).is_equal_to(source)
        assert_that(service.target_dir).is_equal_to(target)


class TestExportToMarkdown:
    """Tests for export_to_markdown method."""

    def test_export_nonexistent_source(self, tmp_path):
        """
        Given a source directory that doesn't exist
        When export_to_markdown is called
        Then a failure result with appropriate error is returned
        """
        source = tmp_path / "nonexistent"
        target = tmp_path / "target"

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_false()
        assert_that(result.exported_count).is_equal_to(0)
        assert_that(result.error).contains("does not exist")

    def test_export_empty_source(self, tmp_path):
        """
        Given a source directory with no JSON files
        When export_to_markdown is called
        Then a failure result indicating no files found is returned
        """
        source = tmp_path / "empty"
        source.mkdir()
        target = tmp_path / "target"

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_false()
        assert_that(result.exported_count).is_equal_to(0)
        assert_that(result.error).contains("No JSON files found")

    def test_export_single_file(self, tmp_path):
        """
        Given a source directory with one JSON file
        When export_to_markdown is called
        Then one markdown file is created
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {
            "cards": [
                {"card_type": "Concept", "tags": ["tag1"], "front": "Question?", "back": "Answer."}
            ]
        }
        (source / "test_file.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        assert_that(result.exported_count).is_equal_to(1)
        assert_that((target / "test_file.md").exists()).is_true()

    def test_export_multiple_files(self, tmp_path):
        """
        Given a source directory with multiple JSON files
        When export_to_markdown is called
        Then all files are exported to markdown
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        for i in range(3):
            data = {"cards": [{"card_type": "Test", "tags": [], "front": f"Q{i}", "back": f"A{i}"}]}
            (source / f"file{i}.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        assert_that(result.exported_count).is_equal_to(3)
        for i in range(3):
            assert_that((target / f"file{i}.md").exists()).is_true()

    def test_export_dry_run(self, tmp_path):
        """
        Given a source directory with files
        When export_to_markdown is called with dry_run=True
        Then success is returned but no files are created
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown(dry_run=True)

        assert_that(result.success).is_true()
        assert_that(result.exported_count).is_equal_to(1)
        # Target directory should NOT be created in dry run
        assert_that(target.exists()).is_false()

    def test_export_creates_target_directory(self, tmp_path):
        """
        Given a target directory that doesn't exist
        When export_to_markdown is called
        Then the target directory is created
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "nested" / "target"

        data = {"cards": [{"front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        assert_that(target.exists()).is_true()

    def test_export_recursive_search(self, tmp_path):
        """
        Given files in both source root and subdirectories
        When export_to_markdown is called
        Then files from all directories are exported
        """
        source = tmp_path / "source"
        source.mkdir()
        subdir = source / "subdir"
        subdir.mkdir()
        target = tmp_path / "target"

        # Files in both directories
        (source / "top.json").write_text('{"cards": [{"front": "Q1", "back": "A1"}]}')
        (subdir / "nested.json").write_text('{"cards": [{"front": "Q2", "back": "A2"}]}')

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        assert_that(result.exported_count).is_equal_to(2)


class TestMarkdownOutput:
    """Tests for Markdown output format."""

    def test_markdown_has_title(self, tmp_path):
        """
        Given a JSON file
        When exported to markdown
        Then the output has a title header
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "Q", "back": "A"}]}
        (source / "test_deck.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "test_deck.md").read_text()
        assert_that(content).contains("# Test Deck")

    def test_markdown_has_card_sections(self, tmp_path):
        """
        Given a JSON file with multiple cards
        When exported to markdown
        Then each card gets a numbered section
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {
            "cards": [
                {"card_type": "Concept", "tags": ["tag1"], "front": "Q1", "back": "A1"},
                {"card_type": "Algorithm", "tags": ["tag2"], "front": "Q2", "back": "A2"},
            ]
        }
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "test.md").read_text()
        assert_that(content).contains("## Card 1")
        assert_that(content).contains("## Card 2")

    def test_markdown_includes_card_type(self, tmp_path):
        """
        Given a card with a type
        When exported to markdown
        Then the card type is included in output
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"card_type": "Algorithm", "tags": [], "front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "test.md").read_text()
        assert_that(content).contains("**Type**: Algorithm")

    def test_markdown_includes_tags(self, tmp_path):
        """
        Given a card with tags
        When exported to markdown
        Then tags are included in output
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"card_type": "Test", "tags": ["Tag1", "Tag2"], "front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "test.md").read_text()
        assert_that(content).contains("**Tags**: Tag1, Tag2")

    def test_markdown_includes_front_and_back(self, tmp_path):
        """
        Given a card with front and back content
        When exported to markdown
        Then both sections are included
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {
            "cards": [
                {"card_type": "Test", "tags": [], "front": "The Question", "back": "The Answer"}
            ]
        }
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "test.md").read_text()
        assert_that(content).contains("### Front")
        assert_that(content).contains("The Question")
        assert_that(content).contains("### Back")
        assert_that(content).contains("The Answer")

    def test_markdown_has_separators(self, tmp_path):
        """
        Given multiple cards
        When exported to markdown
        Then cards are separated by horizontal rules
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {
            "cards": [
                {"front": "Q1", "back": "A1"},
                {"front": "Q2", "back": "A2"},
            ]
        }
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "test.md").read_text()
        assert_that(content).contains("---")


class TestExportDataFormats:
    """Tests for different data formats."""

    def test_export_dict_with_cards_key(self, tmp_path):
        """
        Given a JSON dict with 'cards' key
        When export_to_markdown is called
        Then cards are exported successfully
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"title": "Test", "cards": [{"front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        content = (target / "test.md").read_text()
        assert_that(content).contains("Q")

    def test_export_list_directly(self, tmp_path):
        """
        Given a JSON file with a list of cards directly
        When export_to_markdown is called
        Then all cards are exported
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = [{"front": "Q1", "back": "A1"}, {"front": "Q2", "back": "A2"}]
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        content = (target / "test.md").read_text()
        assert_that(content).contains("Q1")
        assert_that(content).contains("Q2")

    def test_export_handles_missing_fields(self, tmp_path):
        """
        Given a card with missing optional fields
        When export_to_markdown is called
        Then export succeeds with defaults
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        # Card with minimal fields
        data = {"cards": [{"front": "Q"}]}  # Missing back, card_type, tags
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        content = (target / "test.md").read_text()
        assert_that(content).contains("**Type**: N/A")
        assert_that(content).contains("Q")

    def test_export_handles_string_tags(self, tmp_path):
        """
        Given tags as a string instead of list
        When export_to_markdown is called
        Then the string tag is included
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "Q", "back": "A", "tags": "single_tag"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        content = (target / "test.md").read_text()
        assert_that(content).contains("single_tag")


class TestExportEdgeCases:
    """Tests for edge cases in export functionality."""

    def test_export_unicode_content(self, tmp_path):
        """
        Given JSON files with unicode content
        When export_to_markdown is called
        Then unicode is preserved correctly
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "中文问题", "back": "答案"}]}
        (source / "unicode.json").write_text(json.dumps(data, ensure_ascii=False))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        content = (target / "unicode.md").read_text(encoding="utf-8")
        assert_that(content).contains("中文问题")

    def test_export_handles_invalid_json_gracefully(self, tmp_path):
        """
        Given a mix of valid and invalid JSON files
        When export_to_markdown is called
        Then invalid files are skipped without crashing
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        (source / "valid.json").write_text('{"cards": [{"front": "Q", "back": "A"}]}')
        (source / "invalid.json").write_text("not json {")

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        # Should succeed for valid file, skip invalid
        assert_that(result.success).is_true()
        assert_that(result.exported_count).is_equal_to(1)
        assert_that((target / "valid.md").exists()).is_true()

    def test_export_filename_transformation(self, tmp_path):
        """
        Given a JSON filename with underscores
        When exported to markdown
        Then the title is properly transformed
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "Q", "back": "A"}]}
        (source / "my_test_deck.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "my_test_deck.md").read_text()
        # Title should have underscores replaced and be title case
        assert_that(content).contains("# My Test Deck")

    def test_export_empty_cards_array(self, tmp_path):
        """
        Given a JSON file with empty cards array
        When export_to_markdown is called
        Then markdown file is created with just title
        """
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": []}
        (source / "empty.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        # File should be created but with just title
        content = (target / "empty.md").read_text()
        assert_that(content).contains("# Empty")
