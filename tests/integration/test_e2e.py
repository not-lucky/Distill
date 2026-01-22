"""End-to-end tests for LLM2Deck with all LLM calls mocked.

These tests verify complete workflows from input to output without making
actual API calls.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
        """Test converting JSON cards to Anki package."""
        # Write sample data to JSON file
        json_path = tmp_path / "cards.json"
        json_path.write_text(json.dumps(sample_card_data))

        # Create Anki deck
        output_path = tmp_path / "output.apkg"

        generator = DeckGenerator(sample_card_data, deck_prefix="Test")
        generator.process()
        generator.save_package(str(output_path))

        # Verify output exists
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_mcq_json_to_anki_workflow(self, tmp_path, sample_mcq_card_data):
        """Test converting MCQ JSON cards to Anki package."""
        output_path = tmp_path / "mcq_output.apkg"

        generator = DeckGenerator(sample_mcq_card_data, deck_prefix="Test_MCQ")
        generator.process()
        generator.save_package(str(output_path))

        assert output_path.exists()

    def test_multiple_problems_to_deck(self, tmp_path):
        """Test converting multiple problems to a single deck."""
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

        assert output_path.exists()
        # Should have created 2 deck entries
        assert len(generator.deck_collection) == 2


class TestE2EMergeWorkflow:
    """End-to-end tests for merge workflow."""

    def test_merge_archived_files_workflow(self, tmp_path):
        """Test merging multiple archived JSON files."""
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
        assert result.success is True
        assert result.merged_count == 5
        assert result.output_path.exists()

        # Verify merged content
        with open(result.output_path) as f:
            merged = json.load(f)
        assert len(merged) == 5

        # Cleanup
        result.output_path.unlink()

    def test_merge_and_convert_to_anki(self, tmp_path):
        """Test full workflow: merge JSON files and convert to Anki."""
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
        assert merge_result.success

        # Load merged data
        with open(merge_result.output_path) as f:
            merged_data = json.load(f)

        # Convert to Anki
        generator = DeckGenerator(merged_data, deck_prefix="LeetCode")
        generator.process()

        output_path = tmp_path / "merged.apkg"
        generator.save_package(str(output_path))

        assert output_path.exists()

        # Cleanup
        merge_result.output_path.unlink()


class TestE2EExportWorkflow:
    """End-to-end tests for export workflow."""

    def test_export_to_markdown_workflow(self, tmp_path):
        """Test exporting JSON files to Markdown."""
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

        assert result.success is True
        assert result.exported_count == 3

        # Verify markdown files
        for i in range(3):
            md_path = target / f"file_{i}.md"
            assert md_path.exists()
            content = md_path.read_text()
            assert f"Question {i}" in content
            assert f"Answer {i}" in content


class TestE2EErrorHandling:
    """End-to-end tests for error handling scenarios."""

    def test_handles_invalid_json_in_merge(self, tmp_path):
        """Test that merge handles invalid JSON files gracefully."""
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
        assert result.success is True
        assert result.merged_count == 2

        # Cleanup
        result.output_path.unlink()

    def test_handles_empty_deck_generation(self, tmp_path):
        """Test handling of empty card data."""
        empty_data = []

        generator = DeckGenerator(empty_data, deck_prefix="Empty")
        generator.process()

        output_path = tmp_path / "empty.apkg"
        generator.save_package(str(output_path))

        # Should not create file for empty deck
        assert not output_path.exists()

    def test_handles_merge_nonexistent_directory(self, tmp_path):
        """Test handling of non-existent archival directory."""
        service = MergeService(archival_dir=tmp_path / "nonexistent")
        result = service.merge_subject("test")

        assert result.success is False
        assert "does not exist" in result.error

    def test_handles_export_empty_source(self, tmp_path):
        """Test handling of empty source directory."""
        source = tmp_path / "empty_source"
        source.mkdir()
        target = tmp_path / "target"

        service = ExportService(source_dir=source, target_dir=target)
        result = service.export_to_markdown()

        assert result.success is False
        assert "No JSON files" in result.error


class TestE2ECompleteWorkflow:
    """Complete workflow tests with mocked providers."""

    def test_generate_and_convert_workflow(self, tmp_path, sample_card_data):
        """Test generating cards and converting to Anki."""
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

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_workflow_with_mcq_cards(self, tmp_path, sample_mcq_card_data):
        """Test workflow with MCQ card type."""
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

        assert output_path.exists()

    def test_full_pipeline_merge_and_export(self, tmp_path):
        """Test complete pipeline: generate, merge, export to markdown."""
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
        assert merge_result.success

        # Step 3: Export to Markdown
        md_source = output_dir
        md_target = tmp_path / "markdown"

        export_service = ExportService(source_dir=md_source, target_dir=md_target)
        export_result = export_service.export_to_markdown()

        assert export_result.success
        assert export_result.exported_count == 3

        # Verify markdown files contain correct content
        for i in range(3):
            md_path = md_target / f"problem_{i}.md"
            content = md_path.read_text()
            assert f"Q{i}" in content
            assert f"A{i}" in content

        # Cleanup merged file
        merge_result.output_path.unlink()
