"""Tests for services/merge.py."""

import json
import pytest
from pathlib import Path

from src.services.merge import MergeService, MergeResult


class TestMergeResult:
    """Tests for MergeResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful merge result."""
        result = MergeResult(
            success=True,
            merged_count=5,
            output_path=Path("/output/file.json"),
        )

        assert result.success is True
        assert result.merged_count == 5
        assert result.output_path == Path("/output/file.json")
        assert result.error is None

    def test_create_failure_result(self):
        """Test creating a failed merge result."""
        result = MergeResult(
            success=False,
            merged_count=0,
            error="Directory not found",
        )

        assert result.success is False
        assert result.merged_count == 0
        assert result.output_path is None
        assert result.error == "Directory not found"


class TestMergeServiceInit:
    """Tests for MergeService initialization."""

    def test_init_with_path(self, tmp_path):
        """Test initialization with archival directory."""
        service = MergeService(archival_dir=tmp_path)

        assert service.archival_dir == tmp_path
        assert service.timestamp_format == "%Y%m%dT%H%M%S"

    def test_init_with_custom_timestamp_format(self, tmp_path):
        """Test initialization with custom timestamp format."""
        service = MergeService(
            archival_dir=tmp_path,
            timestamp_format="%Y-%m-%d",
        )

        assert service.timestamp_format == "%Y-%m-%d"


class TestMergeSubject:
    """Tests for merge_subject method."""

    def test_merge_nonexistent_directory(self, tmp_path):
        """Test merging when subject directory doesn't exist."""
        service = MergeService(archival_dir=tmp_path)

        result = service.merge_subject("nonexistent")

        assert result.success is False
        assert result.merged_count == 0
        assert "does not exist" in result.error

    def test_merge_empty_directory(self, tmp_path):
        """Test merging when directory has no JSON files."""
        subject_dir = tmp_path / "empty_subject"
        subject_dir.mkdir()

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("empty_subject")

        assert result.success is False
        assert result.merged_count == 0
        assert "No JSON files found" in result.error

    def test_merge_single_file(self, tmp_path):
        """Test merging a single JSON file."""
        subject_dir = tmp_path / "test_subject"
        subject_dir.mkdir()

        data = {"title": "Test", "cards": [{"front": "Q", "back": "A"}]}
        json_file = subject_dir / "file1.json"
        json_file.write_text(json.dumps(data))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("test_subject")

        assert result.success is True
        assert result.merged_count == 1
        assert result.output_path is not None
        assert result.output_path.exists()

        # Cleanup
        result.output_path.unlink()

    def test_merge_multiple_files(self, tmp_path):
        """Test merging multiple JSON files."""
        subject_dir = tmp_path / "multi_subject"
        subject_dir.mkdir()

        for i in range(3):
            data = {"title": f"Test {i}", "index": i}
            json_file = subject_dir / f"file{i}.json"
            json_file.write_text(json.dumps(data))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("multi_subject")

        assert result.success is True
        assert result.merged_count == 3
        assert result.output_path.exists()

        # Verify merged content
        with open(result.output_path) as f:
            merged = json.load(f)
        assert len(merged) == 3

        # Cleanup
        result.output_path.unlink()

    def test_merge_dry_run(self, tmp_path):
        """Test merge in dry run mode."""
        subject_dir = tmp_path / "dry_run_subject"
        subject_dir.mkdir()

        data = {"title": "Test"}
        json_file = subject_dir / "file.json"
        json_file.write_text(json.dumps(data))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("dry_run_subject", dry_run=True)

        assert result.success is True
        assert result.merged_count == 1
        assert result.output_path is not None
        # File should NOT be created in dry run
        assert not result.output_path.exists()

    def test_merge_skips_non_object_json(self, tmp_path):
        """Test that non-object JSON files are skipped."""
        subject_dir = tmp_path / "mixed_subject"
        subject_dir.mkdir()

        # Object (should be included)
        (subject_dir / "object.json").write_text('{"title": "Valid"}')
        # Array (should be skipped)
        (subject_dir / "array.json").write_text('[1, 2, 3]')
        # String (should be skipped)
        (subject_dir / "string.json").write_text('"just a string"')

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("mixed_subject")

        assert result.success is True
        assert result.merged_count == 1  # Only the object

        # Cleanup
        result.output_path.unlink()

    def test_merge_handles_invalid_json(self, tmp_path):
        """Test that invalid JSON files are skipped without failing."""
        subject_dir = tmp_path / "invalid_subject"
        subject_dir.mkdir()

        # Valid
        (subject_dir / "valid.json").write_text('{"title": "Valid"}')
        # Invalid
        (subject_dir / "invalid.json").write_text("not valid json {")

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("invalid_subject")

        assert result.success is True
        assert result.merged_count == 1

        # Cleanup
        result.output_path.unlink()

    def test_merge_all_invalid_returns_failure(self, tmp_path):
        """Test that all invalid files results in failure."""
        subject_dir = tmp_path / "all_invalid"
        subject_dir.mkdir()

        (subject_dir / "invalid1.json").write_text("not json")
        (subject_dir / "invalid2.json").write_text("[1, 2, 3]")  # Array, not object

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("all_invalid")

        assert result.success is False
        assert "No valid data found" in result.error

    def test_merge_output_filename_format(self, tmp_path):
        """Test that output filename follows expected format."""
        subject_dir = tmp_path / "format_test"
        subject_dir.mkdir()

        (subject_dir / "file.json").write_text('{"data": 1}')

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("format_test")

        assert result.success is True
        # Filename should be like: format_test_anki_deck_TIMESTAMP.json
        assert "format_test_anki_deck_" in result.output_path.name
        assert result.output_path.suffix == ".json"

        # Cleanup
        result.output_path.unlink()

    def test_merge_preserves_data_structure(self, tmp_path):
        """Test that merged data preserves original structure."""
        subject_dir = tmp_path / "preserve_test"
        subject_dir.mkdir()

        data1 = {
            "title": "Problem 1",
            "cards": [{"front": "Q1", "back": "A1"}],
            "metadata": {"difficulty": "Easy"},
        }
        data2 = {
            "title": "Problem 2",
            "cards": [{"front": "Q2", "back": "A2"}],
            "metadata": {"difficulty": "Medium"},
        }

        (subject_dir / "file1.json").write_text(json.dumps(data1))
        (subject_dir / "file2.json").write_text(json.dumps(data2))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("preserve_test")

        with open(result.output_path) as f:
            merged = json.load(f)

        assert len(merged) == 2
        # Data should be preserved
        titles = {item["title"] for item in merged}
        assert "Problem 1" in titles
        assert "Problem 2" in titles

        # Cleanup
        result.output_path.unlink()


class TestMergeEdgeCases:
    """Tests for edge cases in merge functionality."""

    def test_merge_unicode_content(self, tmp_path):
        """Test merging files with unicode content."""
        subject_dir = tmp_path / "unicode_test"
        subject_dir.mkdir()

        data = {"title": "Unicode Test", "content": "\u4e2d\u6587 \u65e5\u672c\u8a9e \ud55c\uad6d\uc5b4"}
        (subject_dir / "unicode.json").write_text(json.dumps(data, ensure_ascii=False))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("unicode_test")

        assert result.success is True

        with open(result.output_path, encoding="utf-8") as f:
            merged = json.load(f)
        assert "\u4e2d\u6587" in merged[0]["content"]

        # Cleanup
        result.output_path.unlink()

    def test_merge_large_files(self, tmp_path):
        """Test merging larger JSON files."""
        subject_dir = tmp_path / "large_test"
        subject_dir.mkdir()

        # Create file with many entries
        data = {
            "title": "Large Problem",
            "cards": [{"front": f"Q{i}", "back": f"A{i}"} for i in range(100)],
        }
        (subject_dir / "large.json").write_text(json.dumps(data))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("large_test")

        assert result.success is True
        assert result.merged_count == 1

        # Cleanup
        result.output_path.unlink()

    def test_merge_nested_directories_not_included(self, tmp_path):
        """Test that files in nested directories are not included."""
        subject_dir = tmp_path / "nested_test"
        subject_dir.mkdir()
        nested_dir = subject_dir / "nested"
        nested_dir.mkdir()

        # File in subject dir (should be included)
        (subject_dir / "top.json").write_text('{"level": "top"}')
        # File in nested dir (should NOT be included with glob("*.json"))
        (nested_dir / "nested.json").write_text('{"level": "nested"}')

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("nested_test")

        assert result.success is True
        assert result.merged_count == 1  # Only top-level file

        # Cleanup
        result.output_path.unlink()
