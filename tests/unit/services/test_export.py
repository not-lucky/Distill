"""Tests for services/export.py."""

import json
import pytest
from pathlib import Path

from src.services.export import ExportService, ExportResult


class TestExportResult:
    """Tests for ExportResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful export result."""
        result = ExportResult(
            success=True,
            exported_count=5,
        )

        assert result.success is True
        assert result.exported_count == 5
        assert result.error is None

    def test_create_failure_result(self):
        """Test creating a failed export result."""
        result = ExportResult(
            success=False,
            exported_count=0,
            error="Source not found",
        )

        assert result.success is False
        assert result.exported_count == 0
        assert result.error == "Source not found"


class TestExportServiceInit:
    """Tests for ExportService initialization."""

    def test_init_with_paths(self, tmp_path):
        """Test initialization with source and target directories."""
        source = tmp_path / "source"
        target = tmp_path / "target"

        service = ExportService(source_dir=source, target_dir=target)

        assert service.source_dir == source
        assert service.target_dir == target


class TestExportToMarkdown:
    """Tests for export_to_markdown method."""

    def test_export_nonexistent_source(self, tmp_path):
        """Test export when source directory doesn't exist."""
        source = tmp_path / "nonexistent"
        target = tmp_path / "target"

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is False
        assert result.exported_count == 0
        assert "does not exist" in result.error

    def test_export_empty_source(self, tmp_path):
        """Test export when source has no JSON files."""
        source = tmp_path / "empty"
        source.mkdir()
        target = tmp_path / "target"

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is False
        assert result.exported_count == 0
        assert "No JSON files found" in result.error

    def test_export_single_file(self, tmp_path):
        """Test exporting a single JSON file."""
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

        assert result.success is True
        assert result.exported_count == 1
        assert (target / "test_file.md").exists()

    def test_export_multiple_files(self, tmp_path):
        """Test exporting multiple JSON files."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        for i in range(3):
            data = {"cards": [{"card_type": "Test", "tags": [], "front": f"Q{i}", "back": f"A{i}"}]}
            (source / f"file{i}.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is True
        assert result.exported_count == 3
        for i in range(3):
            assert (target / f"file{i}.md").exists()

    def test_export_dry_run(self, tmp_path):
        """Test export in dry run mode."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown(dry_run=True)

        assert result.success is True
        assert result.exported_count == 1
        # Target directory should NOT be created in dry run
        assert not target.exists()

    def test_export_creates_target_directory(self, tmp_path):
        """Test that export creates target directory if needed."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "nested" / "target"

        data = {"cards": [{"front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is True
        assert target.exists()

    def test_export_recursive_search(self, tmp_path):
        """Test that export searches subdirectories."""
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

        assert result.success is True
        assert result.exported_count == 2


class TestMarkdownOutput:
    """Tests for Markdown output format."""

    def test_markdown_has_title(self, tmp_path):
        """Test that Markdown output has a title."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "Q", "back": "A"}]}
        (source / "test_deck.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "test_deck.md").read_text()
        assert "# Test Deck" in content

    def test_markdown_has_card_sections(self, tmp_path):
        """Test that each card gets a section."""
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
        assert "## Card 1" in content
        assert "## Card 2" in content

    def test_markdown_includes_card_type(self, tmp_path):
        """Test that card type is included."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"card_type": "Algorithm", "tags": [], "front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "test.md").read_text()
        assert "**Type**: Algorithm" in content

    def test_markdown_includes_tags(self, tmp_path):
        """Test that tags are included."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"card_type": "Test", "tags": ["Tag1", "Tag2"], "front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "test.md").read_text()
        assert "**Tags**: Tag1, Tag2" in content

    def test_markdown_includes_front_and_back(self, tmp_path):
        """Test that front and back content is included."""
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
        assert "### Front" in content
        assert "The Question" in content
        assert "### Back" in content
        assert "The Answer" in content

    def test_markdown_has_separators(self, tmp_path):
        """Test that cards are separated by horizontal rules."""
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
        assert "---" in content


class TestExportDataFormats:
    """Tests for different data formats."""

    def test_export_dict_with_cards_key(self, tmp_path):
        """Test exporting dict with 'cards' key."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"title": "Test", "cards": [{"front": "Q", "back": "A"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is True
        content = (target / "test.md").read_text()
        assert "Q" in content

    def test_export_list_directly(self, tmp_path):
        """Test exporting list of cards directly."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = [{"front": "Q1", "back": "A1"}, {"front": "Q2", "back": "A2"}]
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is True
        content = (target / "test.md").read_text()
        assert "Q1" in content
        assert "Q2" in content

    def test_export_handles_missing_fields(self, tmp_path):
        """Test that export handles missing optional fields."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        # Card with minimal fields
        data = {"cards": [{"front": "Q"}]}  # Missing back, card_type, tags
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is True
        content = (target / "test.md").read_text()
        assert "**Type**: N/A" in content
        assert "Q" in content

    def test_export_handles_string_tags(self, tmp_path):
        """Test that export handles tags as string instead of list."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "Q", "back": "A", "tags": "single_tag"}]}
        (source / "test.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is True
        content = (target / "test.md").read_text()
        assert "single_tag" in content


class TestExportEdgeCases:
    """Tests for edge cases in export functionality."""

    def test_export_unicode_content(self, tmp_path):
        """Test exporting files with unicode content."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "\u4e2d\u6587\u95ee\u9898", "back": "\u7b54\u6848"}]}
        (source / "unicode.json").write_text(json.dumps(data, ensure_ascii=False))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is True
        content = (target / "unicode.md").read_text(encoding="utf-8")
        assert "\u4e2d\u6587\u95ee\u9898" in content

    def test_export_handles_invalid_json_gracefully(self, tmp_path):
        """Test that invalid JSON files don't crash export."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        (source / "valid.json").write_text('{"cards": [{"front": "Q", "back": "A"}]}')
        (source / "invalid.json").write_text("not json {")

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        # Should succeed for valid file, skip invalid
        assert result.success is True
        assert result.exported_count == 1
        assert (target / "valid.md").exists()

    def test_export_filename_transformation(self, tmp_path):
        """Test that filenames are properly transformed."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": [{"front": "Q", "back": "A"}]}
        (source / "my_test_deck.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        service.export_to_markdown()

        content = (target / "my_test_deck.md").read_text()
        # Title should have underscores replaced and be title case
        assert "# My Test Deck" in content

    def test_export_empty_cards_array(self, tmp_path):
        """Test exporting file with empty cards array."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        data = {"cards": []}
        (source / "empty.json").write_text(json.dumps(data))

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is True
        # File should be created but with just title
        content = (target / "empty.md").read_text()
        assert "# Empty" in content
