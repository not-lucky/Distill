"""Tests for services/merge.py."""

import json
import pytest
from pathlib import Path

from assertpy import assert_that

from src.services.merge import MergeService, MergeResult


class TestMergeResult:
    """Tests for MergeResult dataclass."""

    def test_create_success_result(self):
        """
        Given success parameters
        When MergeResult is created
        Then all success fields are set correctly
        """
        result = MergeResult(
            success=True,
            merged_count=5,
            output_path=Path("/output/file.json"),
        )

        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(5)
        assert_that(result.output_path).is_equal_to(Path("/output/file.json"))
        assert_that(result.error).is_none()

    def test_create_failure_result(self):
        """
        Given failure parameters
        When MergeResult is created
        Then all failure fields are set correctly
        """
        result = MergeResult(
            success=False,
            merged_count=0,
            error="Directory not found",
        )

        assert_that(result.success).is_false()
        assert_that(result.merged_count).is_equal_to(0)
        assert_that(result.output_path).is_none()
        assert_that(result.error).is_equal_to("Directory not found")


class TestMergeServiceInit:
    """Tests for MergeService initialization."""

    def test_init_with_path(self, tmp_path):
        """
        Given an archival directory path
        When MergeService is initialized
        Then the directory and default timestamp format are set
        """
        service = MergeService(archival_dir=tmp_path)

        assert_that(service.archival_dir).is_equal_to(tmp_path)
        assert_that(service.timestamp_format).is_equal_to("%Y%m%dT%H%M%S")

    def test_init_with_custom_timestamp_format(self, tmp_path):
        """
        Given a custom timestamp format
        When MergeService is initialized
        Then the custom format is used
        """
        service = MergeService(
            archival_dir=tmp_path,
            timestamp_format="%Y-%m-%d",
        )

        assert_that(service.timestamp_format).is_equal_to("%Y-%m-%d")


class TestMergeSubject:
    """Tests for merge_subject method."""

    def test_merge_nonexistent_directory(self, tmp_path):
        """
        Given a subject directory that doesn't exist
        When merge_subject is called
        Then a failure result with appropriate error is returned
        """
        service = MergeService(archival_dir=tmp_path)

        result = service.merge_subject("nonexistent")

        assert_that(result.success).is_false()
        assert_that(result.merged_count).is_equal_to(0)
        assert_that(result.error).contains("does not exist")

    def test_merge_empty_directory(self, tmp_path):
        """
        Given a subject directory with no JSON files
        When merge_subject is called
        Then a failure result indicating no files found is returned
        """
        subject_dir = tmp_path / "empty_subject"
        subject_dir.mkdir()

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("empty_subject")

        assert_that(result.success).is_false()
        assert_that(result.merged_count).is_equal_to(0)
        assert_that(result.error).contains("No JSON files found")

    def test_merge_single_file(self, tmp_path):
        """
        Given a subject directory with one JSON file
        When merge_subject is called
        Then a success result with count of 1 is returned
        """
        subject_dir = tmp_path / "test_subject"
        subject_dir.mkdir()

        data = {"title": "Test", "cards": [{"front": "Q", "back": "A"}]}
        json_file = subject_dir / "file1.json"
        json_file.write_text(json.dumps(data))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("test_subject")

        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(1)
        assert_that(result.output_path).is_not_none()
        assert_that(result.output_path.exists()).is_true()

        # Cleanup
        result.output_path.unlink()

    def test_merge_multiple_files(self, tmp_path):
        """
        Given a subject directory with multiple JSON files
        When merge_subject is called
        Then all files are merged into one output
        """
        subject_dir = tmp_path / "multi_subject"
        subject_dir.mkdir()

        for i in range(3):
            data = {"title": f"Test {i}", "index": i}
            json_file = subject_dir / f"file{i}.json"
            json_file.write_text(json.dumps(data))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("multi_subject")

        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(3)
        assert_that(result.output_path.exists()).is_true()

        # Verify merged content
        with open(result.output_path) as f:
            merged = json.load(f)
        assert_that(merged).is_length(3)

        # Cleanup
        result.output_path.unlink()

    def test_merge_dry_run(self, tmp_path):
        """
        Given a subject directory with files
        When merge_subject is called with dry_run=True
        Then success is returned but no file is created
        """
        subject_dir = tmp_path / "dry_run_subject"
        subject_dir.mkdir()

        data = {"title": "Test"}
        json_file = subject_dir / "file.json"
        json_file.write_text(json.dumps(data))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("dry_run_subject", dry_run=True)

        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(1)
        assert_that(result.output_path).is_not_none()
        # File should NOT be created in dry run
        assert_that(result.output_path.exists()).is_false()

    def test_merge_skips_non_object_json(self, tmp_path):
        """
        Given JSON files with mixed types (objects and non-objects)
        When merge_subject is called
        Then only object JSON files are included
        """
        subject_dir = tmp_path / "mixed_subject"
        subject_dir.mkdir()

        # Object (should be included)
        (subject_dir / "object.json").write_text('{"title": "Valid"}')
        # Array (should be skipped)
        (subject_dir / "array.json").write_text("[1, 2, 3]")
        # String (should be skipped)
        (subject_dir / "string.json").write_text('"just a string"')

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("mixed_subject")

        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(1)  # Only the object

        # Cleanup
        result.output_path.unlink()

    def test_merge_handles_invalid_json(self, tmp_path):
        """
        Given a mix of valid and invalid JSON files
        When merge_subject is called
        Then invalid files are skipped and valid ones are merged
        """
        subject_dir = tmp_path / "invalid_subject"
        subject_dir.mkdir()

        # Valid
        (subject_dir / "valid.json").write_text('{"title": "Valid"}')
        # Invalid
        (subject_dir / "invalid.json").write_text("not valid json {")

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("invalid_subject")

        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(1)

        # Cleanup
        result.output_path.unlink()

    def test_merge_all_invalid_returns_failure(self, tmp_path):
        """
        Given only invalid or non-object JSON files
        When merge_subject is called
        Then a failure result is returned
        """
        subject_dir = tmp_path / "all_invalid"
        subject_dir.mkdir()

        (subject_dir / "invalid1.json").write_text("not json")
        (subject_dir / "invalid2.json").write_text("[1, 2, 3]")  # Array, not object

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("all_invalid")

        assert_that(result.success).is_false()
        assert_that(result.error).contains("No valid data found")

    def test_merge_output_filename_format(self, tmp_path):
        """
        Given a subject directory with files
        When merge_subject is called
        Then output filename follows expected format
        """
        subject_dir = tmp_path / "format_test"
        subject_dir.mkdir()

        (subject_dir / "file.json").write_text('{"data": 1}')

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("format_test")

        assert_that(result.success).is_true()
        # Filename should be like: format_test_anki_deck_TIMESTAMP.json
        assert_that(result.output_path.name).contains("format_test_anki_deck_")
        assert_that(result.output_path.suffix).is_equal_to(".json")

        # Cleanup
        result.output_path.unlink()

    def test_merge_preserves_data_structure(self, tmp_path):
        """
        Given JSON files with nested structures
        When merge_subject is called
        Then data structure is preserved in merged output
        """
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

        assert_that(merged).is_length(2)
        # Data should be preserved
        titles = {item["title"] for item in merged}
        assert_that(titles).contains("Problem 1")
        assert_that(titles).contains("Problem 2")

        # Cleanup
        result.output_path.unlink()


class TestMergeEdgeCases:
    """Tests for edge cases in merge functionality."""

    def test_merge_unicode_content(self, tmp_path):
        """
        Given JSON files with unicode content
        When merge_subject is called
        Then unicode is preserved correctly
        """
        subject_dir = tmp_path / "unicode_test"
        subject_dir.mkdir()

        data = {"title": "Unicode Test", "content": "中文 日本語 한국어"}
        (subject_dir / "unicode.json").write_text(json.dumps(data, ensure_ascii=False))

        service = MergeService(archival_dir=tmp_path)
        result = service.merge_subject("unicode_test")

        assert_that(result.success).is_true()

        with open(result.output_path, encoding="utf-8") as f:
            merged = json.load(f)
        assert_that(merged[0]["content"]).contains("中文")

        # Cleanup
        result.output_path.unlink()

    def test_merge_large_files(self, tmp_path):
        """
        Given a large JSON file with many entries
        When merge_subject is called
        Then file is merged successfully
        """
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

        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(1)

        # Cleanup
        result.output_path.unlink()

    def test_merge_nested_directories_not_included(self, tmp_path):
        """
        Given files in both top-level and nested directories
        When merge_subject is called
        Then only top-level files are included
        """
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

        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(1)  # Only top-level file

        # Cleanup
        result.output_path.unlink()
