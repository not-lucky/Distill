"""Tests for CLI in src/cli.py."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import warnings

from src.cli import (
    normalize_legacy_args,
    create_parser,
    handle_generate,
    handle_convert,
    handle_merge,
    handle_export_md,
    main,
)


class TestNormalizeLegacyArgs:
    """Tests for normalize_legacy_args function."""

    def test_empty_args(self):
        """Test empty argument list."""
        result = normalize_legacy_args([])
        assert result == []

    def test_new_style_generate(self):
        """Test new-style generate command passes through."""
        args = ["generate", "leetcode", "standard"]
        result = normalize_legacy_args(args)
        assert result == args

    def test_new_style_convert(self):
        """Test new-style convert command passes through."""
        args = ["convert", "file.json"]
        result = normalize_legacy_args(args)
        assert result == args

    def test_new_style_merge(self):
        """Test new-style merge command passes through."""
        args = ["merge", "cs"]
        result = normalize_legacy_args(args)
        assert result == args

    def test_new_style_export_md(self):
        """Test new-style export-md command passes through."""
        args = ["export-md", "--source", "./dir"]
        result = normalize_legacy_args(args)
        assert result == args

    def test_help_flag(self):
        """Test help flag passes through."""
        for flag in ["-h", "--help"]:
            result = normalize_legacy_args([flag])
            assert result == [flag]

    def test_legacy_subject_only(self):
        """Test legacy style with subject only."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = normalize_legacy_args(["leetcode"])
            assert result == ["generate", "leetcode"]
            assert len(w) == 1
            assert "deprecated" in str(w[0].message).lower()

    def test_legacy_subject_with_mcq(self):
        """Test legacy style with subject and mcq."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["cs", "mcq"])
            assert result == ["generate", "cs", "mcq"]

    def test_legacy_with_label_equals(self):
        """Test legacy style with --label=value format."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["physics", "--label=test"])
            assert result == ["generate", "physics", "--label", "test"]


class TestCreateParser:
    """Tests for create_parser function."""

    @pytest.fixture
    def parser(self):
        """Create the argument parser."""
        with patch("src.cli.SubjectRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.get_available_subjects.return_value = ["leetcode", "cs", "physics"]
            MockRegistry.return_value = mock_registry
            return create_parser()

    def test_generate_command_default_subject(self, parser):
        """Test generate command with default subject."""
        args = parser.parse_args(["generate"])
        assert args.command == "generate"
        assert args.subject == "leetcode"
        assert args.card_type == "standard"

    def test_generate_command_with_subject(self, parser):
        """Test generate command with explicit subject."""
        args = parser.parse_args(["generate", "cs"])
        assert args.subject == "cs"
        assert args.card_type == "standard"

    def test_generate_command_mcq(self, parser):
        """Test generate command with MCQ card type."""
        args = parser.parse_args(["generate", "physics", "mcq"])
        assert args.subject == "physics"
        assert args.card_type == "mcq"

    def test_generate_command_with_label(self, parser):
        """Test generate command with label."""
        args = parser.parse_args(["generate", "leetcode", "--label", "test run"])
        assert args.label == "test run"

    def test_generate_command_dry_run(self, parser):
        """Test generate command with dry-run flag."""
        args = parser.parse_args(["generate", "--dry-run"])
        assert args.dry_run is True

    def test_convert_command(self, parser):
        """Test convert command."""
        args = parser.parse_args(["convert", "deck.json"])
        assert args.command == "convert"
        assert args.json_file == "deck.json"

    def test_convert_command_with_mode(self, parser):
        """Test convert command with explicit mode."""
        args = parser.parse_args(["convert", "deck.json", "--mode", "cs_mcq"])
        assert args.mode == "cs_mcq"

    def test_convert_command_with_output(self, parser):
        """Test convert command with output path."""
        args = parser.parse_args(["convert", "deck.json", "-o", "output.apkg"])
        assert args.output == "output.apkg"

    def test_merge_command(self, parser):
        """Test merge command."""
        args = parser.parse_args(["merge", "cs"])
        assert args.command == "merge"
        assert args.subject == "cs"

    def test_export_md_command(self, parser):
        """Test export-md command."""
        args = parser.parse_args(["export-md"])
        assert args.command == "export-md"
        assert args.source is None
        assert args.target is None

    def test_export_md_command_with_paths(self, parser):
        """Test export-md command with paths."""
        args = parser.parse_args(["export-md", "--source", "./in", "--target", "./out"])
        assert args.source == "./in"
        assert args.target == "./out"


class TestHandleGenerate:
    """Tests for handle_generate function."""

    @pytest.mark.asyncio
    async def test_handle_generate_success(self):
        """Test successful generate handling."""
        args = MagicMock()
        args.subject = "leetcode"
        args.card_type = "standard"
        args.label = None
        args.dry_run = False

        with patch("src.cli.SubjectRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.is_valid_subject.return_value = True
            mock_registry.get_config.return_value = MagicMock()
            MockRegistry.return_value = mock_registry

            with patch("src.orchestrator.Orchestrator") as MockOrch:
                mock_orch = AsyncMock()
                mock_orch.initialize = AsyncMock(return_value=True)
                mock_orch.run = AsyncMock(return_value=[{"title": "Test"}])
                mock_orch.save_results = MagicMock(return_value="output.json")
                MockOrch.return_value = mock_orch

                result = await handle_generate(args)

                assert result == 0

    @pytest.mark.asyncio
    async def test_handle_generate_invalid_subject(self):
        """Test handling of invalid subject."""
        args = MagicMock()
        args.subject = "invalid"
        args.card_type = "standard"

        with patch("src.cli.SubjectRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.is_valid_subject.return_value = False
            mock_registry.get_available_subjects.return_value = ["leetcode", "cs"]
            MockRegistry.return_value = mock_registry

            result = await handle_generate(args)

            assert result == 1

    @pytest.mark.asyncio
    async def test_handle_generate_init_fails(self):
        """Test handling when orchestrator init fails."""
        args = MagicMock()
        args.subject = "leetcode"
        args.card_type = "standard"
        args.label = None
        args.dry_run = False

        with patch("src.cli.SubjectRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.is_valid_subject.return_value = True
            mock_registry.get_config.return_value = MagicMock()
            MockRegistry.return_value = mock_registry

            with patch("src.orchestrator.Orchestrator") as MockOrch:
                mock_orch = AsyncMock()
                mock_orch.initialize = AsyncMock(return_value=False)
                MockOrch.return_value = mock_orch

                result = await handle_generate(args)

                assert result == 1


class TestHandleConvert:
    """Tests for handle_convert function."""

    def test_handle_convert_file_not_found(self, tmp_path):
        """Test handling of non-existent file."""
        args = MagicMock()
        args.json_file = str(tmp_path / "nonexistent.json")
        args.mode = None
        args.output = None
        args.dry_run = False

        result = handle_convert(args)

        assert result == 1

    def test_handle_convert_success(self, tmp_path):
        """Test successful conversion."""
        # Create input file
        input_file = tmp_path / "leetcode_deck.json"
        input_file.write_text('[{"title": "Test", "cards": []}]')

        args = MagicMock()
        args.json_file = str(input_file)
        args.mode = "leetcode"
        args.output = str(tmp_path / "output.apkg")
        args.dry_run = False

        # Patch where imports occur (inside handle_convert function)
        with patch("src.anki.generator.load_card_data") as mock_load:
            mock_load.return_value = [{"title": "Test", "cards": []}]

            with patch("src.anki.generator.DeckGenerator") as MockGenerator:
                mock_gen = MagicMock()
                MockGenerator.return_value = mock_gen

                result = handle_convert(args)

                assert result == 0

    def test_handle_convert_dry_run(self, tmp_path):
        """Test conversion in dry run mode."""
        input_file = tmp_path / "test.json"
        input_file.write_text('[{"title": "Test", "cards": [{"front": "Q", "back": "A"}]}]')

        args = MagicMock()
        args.json_file = str(input_file)
        args.mode = "leetcode"
        args.output = None
        args.dry_run = True

        result = handle_convert(args)

        assert result == 0


class TestHandleMerge:
    """Tests for handle_merge function."""

    def test_handle_merge_success(self):
        """Test successful merge handling."""
        args = MagicMock()
        args.subject = "cs"
        args.dry_run = False

        with patch("src.cli.load_config") as mock_config:
            mock_config.return_value = MagicMock(
                paths=MagicMock(
                    archival_dir="archival",
                    timestamp_format="%Y%m%dT%H%M%S"
                )
            )

            with patch("src.services.merge.MergeService") as MockService:
                mock_service = MagicMock()
                mock_service.merge_subject.return_value = MagicMock(
                    success=True,
                    merged_count=5,
                    output_path=Path("output.json")
                )
                MockService.return_value = mock_service

                result = handle_merge(args)

                assert result == 0

    def test_handle_merge_failure(self):
        """Test merge handling when merge fails."""
        args = MagicMock()
        args.subject = "cs"
        args.dry_run = False

        with patch("src.cli.load_config") as mock_config:
            mock_config.return_value = MagicMock(
                paths=MagicMock(archival_dir="archival", timestamp_format="%Y%m%dT%H%M%S")
            )

            with patch("src.services.merge.MergeService") as MockService:
                mock_service = MagicMock()
                mock_service.merge_subject.return_value = MagicMock(
                    success=False,
                    merged_count=0,
                    error="Directory not found"
                )
                MockService.return_value = mock_service

                result = handle_merge(args)

                assert result == 1


class TestHandleExportMd:
    """Tests for handle_export_md function."""

    def test_handle_export_md_success(self):
        """Test successful export handling."""
        args = MagicMock()
        args.source = None
        args.target = None
        args.dry_run = False

        with patch("src.cli.load_config") as mock_config:
            mock_config.return_value = MagicMock(
                paths=MagicMock(archival_dir="archival", markdown_dir="markdown")
            )

            with patch("src.services.export.ExportService") as MockService:
                mock_service = MagicMock()
                mock_service.export_to_markdown.return_value = MagicMock(
                    success=True,
                    exported_count=10
                )
                MockService.return_value = mock_service

                result = handle_export_md(args)

                assert result == 0

    def test_handle_export_md_failure(self):
        """Test export handling when export fails."""
        args = MagicMock()
        args.source = "/nonexistent"
        args.target = None
        args.dry_run = False

        with patch("src.cli.load_config") as mock_config:
            mock_config.return_value = MagicMock(
                paths=MagicMock(archival_dir="archival", markdown_dir="markdown")
            )

            with patch("src.services.export.ExportService") as MockService:
                mock_service = MagicMock()
                mock_service.export_to_markdown.return_value = MagicMock(
                    success=False,
                    exported_count=0,
                    error="Source not found"
                )
                MockService.return_value = mock_service

                result = handle_export_md(args)

                assert result == 1


class TestMain:
    """Tests for main function."""

    def test_main_no_command(self):
        """Test main with no command shows help."""
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    MockRegistry.return_value = mock_registry

                    result = main([])

                    assert result == 0

    def test_main_generate_command(self):
        """Test main with generate command."""
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    mock_registry.is_valid_subject.return_value = True
                    mock_registry.get_config.return_value = MagicMock()
                    MockRegistry.return_value = mock_registry

                    with patch("src.cli.asyncio.run") as mock_run:
                        mock_run.return_value = 0

                        result = main(["generate", "leetcode"])

                        assert mock_run.called

    def test_main_convert_command(self, tmp_path):
        """Test main with convert command."""
        input_file = tmp_path / "test.json"
        input_file.write_text("[]")

        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    MockRegistry.return_value = mock_registry

                    with patch("src.cli.handle_convert") as mock_handle:
                        mock_handle.return_value = 0

                        result = main(["convert", str(input_file)])

                        mock_handle.assert_called_once()
