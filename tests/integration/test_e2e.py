"""End-to-end tests for LLM2Deck with all LLM calls mocked.

These tests verify complete workflows from input to output without making
actual API calls.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from assertpy import assert_that

from src.anki.generator import DeckGenerator
from src.services.merge import MergeService
from src.services.export import ExportService

from conftest import (
    MockLLMProvider,
    FailingMockProvider,
    SAMPLE_CARD_RESPONSE,
    SAMPLE_CARD_RESPONSE_DICT,
    SAMPLE_MCQ_RESPONSE,
    SAMPLE_MCQ_RESPONSE_DICT,
    SAMPLE_CS_RESPONSE,
)


class TestE2EAnkiGeneration:
    """End-to-end tests for Anki deck generation."""

    def test_json_to_anki_workflow(self, tmp_path, sample_card_data):
        """
        Given sample card data written to JSON
        When DeckGenerator processes and saves it
        Then an Anki package file is created
        """
        # Write sample data to JSON file
        json_path = tmp_path / "cards.json"
        json_path.write_text(json.dumps(sample_card_data))

        # Create Anki deck
        output_path = tmp_path / "output.apkg"

        generator = DeckGenerator(sample_card_data, deck_prefix="Test")
        generator.process()
        generator.save_package(str(output_path))

        # Verify output exists
        assert_that(output_path.exists()).is_true()
        assert_that(output_path.stat().st_size > 0).is_true()

    def test_mcq_json_to_anki_workflow(self, tmp_path, sample_mcq_card_data):
        """
        Given MCQ card data
        When DeckGenerator processes and saves it
        Then an Anki package file is created
        """
        output_path = tmp_path / "mcq_output.apkg"

        generator = DeckGenerator(sample_mcq_card_data, deck_prefix="Test_MCQ")
        generator.process()
        generator.save_package(str(output_path))

        assert_that(output_path.exists()).is_true()

    def test_multiple_problems_to_deck(self, tmp_path):
        """
        Given multiple problems with different categories
        When DeckGenerator processes them
        Then multiple deck entries are created
        """
        card_data = [
            {
                "title": "Problem 1",
                "topic": "Arrays",
                "difficulty": "Easy",
                "category_index": 1,
                "category_name": "Arrays",
                "problem_index": 1,
                "cards": [
                    {"card_type": "Concept", "tags": [], "front": "Q1", "back": "A1"}
                ]
            },
            {
                "title": "Problem 2",
                "topic": "Strings",
                "difficulty": "Medium",
                "category_index": 2,
                "category_name": "Strings",
                "problem_index": 1,
                "cards": [
                    {"card_type": "Concept", "tags": [], "front": "Q2", "back": "A2"}
                ]
            },
        ]

        output_path = tmp_path / "multi.apkg"

        generator = DeckGenerator(card_data, deck_prefix="Multi")
        generator.process()
        generator.save_package(str(output_path))

        assert_that(output_path.exists()).is_true()
        # Should have created 2 deck entries
        assert_that(generator.deck_collection).is_length(2)


class TestE2EMergeWorkflow:
    """End-to-end tests for merge workflow."""

    def test_merge_archived_files_workflow(self, tmp_path):
        """
        Given multiple archived JSON files
        When MergeService merges them
        Then all files are combined into one output file
        """
        # Create archival structure
        archival_dir = tmp_path / "archival"
        cs_dir = archival_dir / "cs"
        cs_dir.mkdir(parents=True)

        # Create multiple JSON files
        for i in range(5):
            data = {
                "title": f"Problem {i}",
                "topic": "CS",
                "difficulty": "Medium",
                "cards": [{"front": f"Q{i}", "back": f"A{i}"}]
            }
            (cs_dir / f"problem_{i}.json").write_text(json.dumps(data))

        # Merge files
        service = MergeService(archival_dir=archival_dir)
        result = service.merge_subject("cs")

        # Verify merge result
        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(5)
        assert_that(result.output_path.exists()).is_true()

        # Verify merged content
        with open(result.output_path) as f:
            merged = json.load(f)
        assert_that(merged).is_length(5)

        # Cleanup
        result.output_path.unlink()

    def test_merge_and_convert_to_anki(self, tmp_path):
        """
        Given archived JSON files
        When merged and converted to Anki
        Then an Anki package is created successfully
        """
        # Create archival structure
        archival_dir = tmp_path / "archival"
        leetcode_dir = archival_dir / "leetcode"
        leetcode_dir.mkdir(parents=True)

        # Create JSON files
        for i in range(3):
            data = {
                "title": f"LeetCode {i}",
                "topic": "Arrays",
                "difficulty": "Easy",
                "cards": [
                    {"card_type": "Algorithm", "tags": [], "front": f"Q{i}", "back": f"A{i}"}
                ]
            }
            (leetcode_dir / f"problem_{i}.json").write_text(json.dumps(data))

        # Merge
        merge_service = MergeService(archival_dir=archival_dir)
        merge_result = merge_service.merge_subject("leetcode")
        assert_that(merge_result.success).is_true()

        # Load merged data
        with open(merge_result.output_path) as f:
            merged_data = json.load(f)

        # Convert to Anki
        generator = DeckGenerator(merged_data, deck_prefix="LeetCode")
        generator.process()

        output_path = tmp_path / "merged.apkg"
        generator.save_package(str(output_path))

        assert_that(output_path.exists()).is_true()

        # Cleanup
        merge_result.output_path.unlink()


class TestE2EExportWorkflow:
    """End-to-end tests for export workflow."""

    def test_export_to_markdown_workflow(self, tmp_path):
        """
        Given JSON files in source directory
        When ExportService exports to markdown
        Then markdown files are created with correct content
        """
        source = tmp_path / "source"
        target = tmp_path / "target"
        source.mkdir()

        # Create source JSON files
        for i in range(3):
            data = {
                "cards": [
                    {"card_type": "Concept", "tags": [f"tag{i}"], "front": f"Question {i}", "back": f"Answer {i}"}
                ]
            }
            (source / f"file_{i}.json").write_text(json.dumps(data))

        # Export
        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_true()
        assert_that(result.exported_count).is_equal_to(3)

        # Verify markdown files
        for i in range(3):
            md_path = target / f"file_{i}.md"
            assert_that(md_path.exists()).is_true()
            content = md_path.read_text()
            assert_that(content).contains(f"Question {i}")
            assert_that(content).contains(f"Answer {i}")


class TestE2EErrorHandling:
    """End-to-end tests for error handling scenarios."""

    def test_handles_invalid_json_in_merge(self, tmp_path):
        """
        Given a mix of valid and invalid JSON files
        When merge is performed
        Then it succeeds with only valid files
        """
        archival = tmp_path / "archival"
        subject_dir = archival / "test"
        subject_dir.mkdir(parents=True)

        # Mix of valid and invalid
        (subject_dir / "valid.json").write_text('{"title": "Valid"}')
        (subject_dir / "invalid.json").write_text("not json")
        (subject_dir / "valid2.json").write_text('{"title": "Valid2"}')

        service = MergeService(archival_dir=archival)
        result = service.merge_subject("test")

        # Should still succeed with valid files
        assert_that(result.success).is_true()
        assert_that(result.merged_count).is_equal_to(2)

        # Cleanup
        result.output_path.unlink()

    def test_handles_empty_deck_generation(self, tmp_path):
        """
        Given empty card data
        When DeckGenerator processes it
        Then no output file is created
        """
        empty_data = []

        generator = DeckGenerator(empty_data, deck_prefix="Empty")
        generator.process()

        output_path = tmp_path / "empty.apkg"
        generator.save_package(str(output_path))

        # Should not create file for empty deck
        assert_that(output_path.exists()).is_false()

    def test_handles_merge_nonexistent_directory(self, tmp_path):
        """
        Given a non-existent archival directory
        When merge is attempted
        Then it fails with appropriate error
        """
        service = MergeService(archival_dir=tmp_path / "nonexistent")
        result = service.merge_subject("test")

        assert_that(result.success).is_false()
        assert_that(result.error).contains("does not exist")

    def test_handles_export_empty_source(self, tmp_path):
        """
        Given an empty source directory
        When export is attempted
        Then it fails with appropriate error
        """
        source = tmp_path / "empty_source"
        source.mkdir()
        target = tmp_path / "target"

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert_that(result.success).is_false()
        assert_that(result.error).contains("No JSON files")


class TestE2ECompleteWorkflow:
    """Complete workflow tests with mocked providers."""

    def test_generate_and_convert_workflow(self, tmp_path, sample_card_data):
        """
        Given generated card data
        When saved to JSON and converted to Anki
        Then an Anki package is created
        """
        # Simulate generated cards
        generated_problems = sample_card_data

        # Save to JSON (simulating save_results)
        json_path = tmp_path / "generated.json"
        with open(json_path, "w") as f:
            json.dump(generated_problems, f)

        # Load and convert to Anki
        with open(json_path) as f:
            loaded_data = json.load(f)

        generator = DeckGenerator(loaded_data, deck_prefix="LeetCode")
        generator.process()

        output_path = tmp_path / "final.apkg"
        generator.save_package(str(output_path))

        assert_that(output_path.exists()).is_true()
        assert_that(output_path.stat().st_size > 0).is_true()

    def test_workflow_with_mcq_cards(self, tmp_path, sample_mcq_card_data):
        """
        Given MCQ card data
        When saved and converted to Anki
        Then an Anki package is created
        """
        # Save MCQ data
        json_path = tmp_path / "mcq_generated.json"
        with open(json_path, "w") as f:
            json.dump(sample_mcq_card_data, f)

        # Load and convert
        with open(json_path) as f:
            loaded_data = json.load(f)

        generator = DeckGenerator(loaded_data, deck_prefix="LeetCode_MCQ")
        generator.process()

        output_path = tmp_path / "mcq_final.apkg"
        generator.save_package(str(output_path))

        assert_that(output_path.exists()).is_true()

    def test_full_pipeline_merge_and_export(self, tmp_path):
        """
        Given generated JSON files
        When merged and exported to markdown
        Then markdown files contain correct content
        """
        # Step 1: Create "generated" JSON files
        output_dir = tmp_path / "archival" / "test"
        output_dir.mkdir(parents=True)

        for i in range(3):
            data = {
                "title": f"Problem {i}",
                "topic": "Test",
                "difficulty": "Easy",
                "cards": [
                    {"card_type": "Concept", "tags": [f"tag{i}"], "front": f"Q{i}", "back": f"A{i}"}
                ]
            }
            (output_dir / f"problem_{i}.json").write_text(json.dumps(data))

        # Step 2: Merge
        merge_service = MergeService(archival_dir=tmp_path / "archival")
        merge_result = merge_service.merge_subject("test")
        assert_that(merge_result.success).is_true()

        # Step 3: Export to Markdown
        md_source = output_dir
        md_target = tmp_path / "markdown"

        export_service = ExportService(source_dir=md_source, target_dir=md_target)
        export_result = export_service.export_to_markdown()

        assert_that(export_result.success).is_true()
        assert_that(export_result.exported_count).is_equal_to(3)

        # Verify markdown files contain correct content
        for i in range(3):
            md_path = md_target / f"problem_{i}.md"
            content = md_path.read_text()
            assert_that(content).contains(f"Q{i}")
            assert_that(content).contains(f"A{i}")

        # Cleanup merged file
        merge_result.output_path.unlink()
