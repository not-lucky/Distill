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

                    # Patch handle_generate to return a regular value (not a coroutine)
                    with patch("src.cli.handle_generate") as mock_handle:
                        mock_handle.return_value = 0

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


class TestNormalizeLegacyArgsExtended:
    """Extended tests for normalize_legacy_args edge cases."""

    def test_legacy_with_mcq_and_label(self):
        """Test legacy style with mcq and label."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["leetcode", "mcq", "--label=test"])
            assert result == ["generate", "leetcode", "mcq", "--label", "test"]

    def test_legacy_physics_subject(self):
        """Test legacy physics subject."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["physics"])
            assert result == ["generate", "physics"]

    def test_legacy_custom_subject(self):
        """Test legacy custom subject."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["my_custom"])
            assert result == ["generate", "my_custom"]

    def test_generate_with_args_passes_through(self):
        """Test that generate with all args passes through."""
        args = ["generate", "cs", "mcq", "--label", "test", "--dry-run"]
        result = normalize_legacy_args(args)
        assert result == args

    def test_convert_with_all_args(self):
        """Test convert with all arguments."""
        args = ["convert", "file.json", "--mode", "cs_mcq", "-o", "out.apkg"]
        result = normalize_legacy_args(args)
        assert result == args

    def test_merge_with_args(self):
        """Test merge with arguments."""
        args = ["merge", "physics", "--dry-run"]
        result = normalize_legacy_args(args)
        assert result == args

    def test_export_md_with_all_args(self):
        """Test export-md with all arguments."""
        args = ["export-md", "--source", "./in", "--target", "./out", "--dry-run"]
        result = normalize_legacy_args(args)
        assert result == args


class TestCreateParserExtended:
    """Extended tests for argument parser."""

    @pytest.fixture
    def parser(self):
        """Create the argument parser."""
        with patch("src.cli.SubjectRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.get_available_subjects.return_value = ["leetcode", "cs", "physics", "custom"]
            MockRegistry.return_value = mock_registry
            return create_parser()

    def test_generate_all_options(self, parser):
        """Test generate with all options."""
        args = parser.parse_args(["generate", "cs", "mcq", "--label", "test", "--dry-run"])
        assert args.subject == "cs"
        assert args.card_type == "mcq"
        assert args.label == "test"
        assert args.dry_run is True

    def test_convert_all_options(self, parser):
        """Test convert with all options."""
        args = parser.parse_args(["convert", "deck.json", "--mode", "physics_mcq", "-o", "out.apkg", "--dry-run"])
        assert args.json_file == "deck.json"
        assert args.mode == "physics_mcq"
        assert args.output == "out.apkg"
        assert args.dry_run is True

    def test_convert_mode_choices(self, parser):
        """Test convert accepts valid modes."""
        for mode in ["leetcode", "leetcode_mcq", "cs", "cs_mcq", "physics", "physics_mcq"]:
            args = parser.parse_args(["convert", "deck.json", "--mode", mode])
            assert args.mode == mode

    def test_merge_with_dry_run(self, parser):
        """Test merge with dry-run flag."""
        args = parser.parse_args(["merge", "cs", "--dry-run"])
        assert args.subject == "cs"
        assert args.dry_run is True

    def test_export_md_with_dry_run(self, parser):
        """Test export-md with dry-run flag."""
        args = parser.parse_args(["export-md", "--dry-run"])
        assert args.dry_run is True

    def test_generate_card_type_choices(self, parser):
        """Test generate card_type choices."""
        for card_type in ["standard", "mcq"]:
            args = parser.parse_args(["generate", "leetcode", card_type])
            assert args.card_type == card_type


class TestHandleGenerateExtended:
    """Extended tests for handle_generate function."""

    @pytest.mark.asyncio
    async def test_handle_generate_dry_run(self):
        """Test generate in dry run mode."""
        args = MagicMock()
        args.subject = "leetcode"
        args.card_type = "standard"
        args.label = None
        args.dry_run = True

        with patch("src.cli.SubjectRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.is_valid_subject.return_value = True
            mock_registry.get_config.return_value = MagicMock()
            MockRegistry.return_value = mock_registry

            with patch("src.orchestrator.Orchestrator") as MockOrch:
                mock_orch = AsyncMock()
                mock_orch.initialize = AsyncMock(return_value=True)
                mock_orch.run = AsyncMock(return_value=[])
                mock_orch.save_results = MagicMock()
                MockOrch.return_value = mock_orch

                result = await handle_generate(args)

                assert result == 0
                MockOrch.assert_called_with(
                    subject_config=mock_registry.get_config.return_value,
                    is_mcq=False,
                    run_label=None,
                    dry_run=True,
                )

    @pytest.mark.asyncio
    async def test_handle_generate_mcq_mode(self):
        """Test generate with MCQ card type."""
        args = MagicMock()
        args.subject = "cs"
        args.card_type = "mcq"
        args.label = "test-mcq"
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
                mock_orch.save_results = MagicMock()
                MockOrch.return_value = mock_orch

                result = await handle_generate(args)

                assert result == 0
                MockOrch.assert_called_with(
                    subject_config=mock_registry.get_config.return_value,
                    is_mcq=True,
                    run_label="test-mcq",
                    dry_run=False,
                )

    @pytest.mark.asyncio
    async def test_handle_generate_with_label(self):
        """Test generate with user label."""
        args = MagicMock()
        args.subject = "physics"
        args.card_type = "standard"
        args.label = "my-run-label"
        args.dry_run = False

        with patch("src.cli.SubjectRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.is_valid_subject.return_value = True
            mock_registry.get_config.return_value = MagicMock()
            MockRegistry.return_value = mock_registry

            with patch("src.orchestrator.Orchestrator") as MockOrch:
                mock_orch = AsyncMock()
                mock_orch.initialize = AsyncMock(return_value=True)
                mock_orch.run = AsyncMock(return_value=[])
                mock_orch.save_results = MagicMock()
                MockOrch.return_value = mock_orch

                result = await handle_generate(args)

                assert result == 0
                # Verify label was passed
                call_kwargs = MockOrch.call_args.kwargs
                assert call_kwargs["run_label"] == "my-run-label"


class TestHandleConvertExtended:
    """Extended tests for handle_convert function."""

    def test_handle_convert_auto_detect_mode(self, tmp_path):
        """Test mode auto-detection from filename."""
        input_file = tmp_path / "cs_mcq_deck.json"
        input_file.write_text('[{"title": "Test", "cards": []}]')

        args = MagicMock()
        args.json_file = str(input_file)
        args.mode = None  # Auto-detect
        args.output = None
        args.dry_run = False

        with patch("src.anki.generator.load_card_data") as mock_load:
            mock_load.return_value = [{"title": "Test", "cards": []}]
            with patch("src.anki.generator.DeckGenerator") as MockGen:
                mock_gen = MagicMock()
                MockGen.return_value = mock_gen

                result = handle_convert(args)

                assert result == 0

    def test_handle_convert_explicit_output_path(self, tmp_path):
        """Test convert with explicit output path."""
        input_file = tmp_path / "test.json"
        input_file.write_text('[{"title": "Test", "cards": []}]')
        output_file = tmp_path / "custom_output.apkg"

        args = MagicMock()
        args.json_file = str(input_file)
        args.mode = "leetcode"
        args.output = str(output_file)
        args.dry_run = False

        with patch("src.anki.generator.load_card_data") as mock_load:
            mock_load.return_value = [{"title": "Test", "cards": []}]
            with patch("src.anki.generator.DeckGenerator") as MockGen:
                mock_gen = MagicMock()
                MockGen.return_value = mock_gen

                result = handle_convert(args)

                assert result == 0
                mock_gen.save_package.assert_called_with(str(output_file))

    def test_handle_convert_exception_handling(self, tmp_path):
        """Test convert handles exceptions gracefully."""
        input_file = tmp_path / "test.json"
        input_file.write_text('[{"title": "Test", "cards": []}]')

        args = MagicMock()
        args.json_file = str(input_file)
        args.mode = "leetcode"
        args.output = None
        args.dry_run = False

        with patch("src.anki.generator.load_card_data") as mock_load:
            mock_load.side_effect = Exception("Failed to load")

            result = handle_convert(args)

            assert result == 1

    def test_handle_convert_dry_run_with_error(self, tmp_path):
        """Test dry run with file read error."""
        input_file = tmp_path / "test.json"
        input_file.write_text("invalid json")

        args = MagicMock()
        args.json_file = str(input_file)
        args.mode = "leetcode"
        args.output = None
        args.dry_run = True

        with patch("src.anki.generator.load_card_data") as mock_load:
            mock_load.side_effect = Exception("Invalid JSON")

            result = handle_convert(args)

            assert result == 1


class TestHandleMergeExtended:
    """Extended tests for handle_merge function."""

    def test_handle_merge_dry_run(self):
        """Test merge in dry run mode."""
        args = MagicMock()
        args.subject = "physics"
        args.dry_run = True

        with patch("src.cli.load_config") as mock_config:
            mock_config.return_value = MagicMock(
                paths=MagicMock(archival_dir="archival", timestamp_format="%Y%m%dT%H%M%S")
            )

            with patch("src.services.merge.MergeService") as MockService:
                mock_service = MagicMock()
                mock_service.merge_subject.return_value = MagicMock(
                    success=True,
                    merged_count=3,
                    output_path=Path("output.json")
                )
                MockService.return_value = mock_service

                result = handle_merge(args)

                assert result == 0
                mock_service.merge_subject.assert_called_with("physics", dry_run=True)

    def test_handle_merge_error_message(self):
        """Test merge displays error message on failure."""
        args = MagicMock()
        args.subject = "leetcode"
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
                    error="No files found for subject"
                )
                MockService.return_value = mock_service

                result = handle_merge(args)

                assert result == 1


class TestHandleExportMdExtended:
    """Extended tests for handle_export_md function."""

    def test_handle_export_md_with_custom_paths(self):
        """Test export with custom source and target paths."""
        args = MagicMock()
        args.source = "/custom/source"
        args.target = "/custom/target"
        args.dry_run = False

        with patch("src.cli.load_config") as mock_config:
            mock_config.return_value = MagicMock(
                paths=MagicMock(archival_dir="archival", markdown_dir="markdown")
            )

            with patch("src.services.export.ExportService") as MockService:
                mock_service = MagicMock()
                mock_service.export_to_markdown.return_value = MagicMock(
                    success=True,
                    exported_count=5
                )
                MockService.return_value = mock_service

                result = handle_export_md(args)

                assert result == 0
                MockService.assert_called_with(
                    source_dir=Path("/custom/source"),
                    target_dir=Path("/custom/target")
                )

    def test_handle_export_md_dry_run(self):
        """Test export in dry run mode."""
        args = MagicMock()
        args.source = None
        args.target = None
        args.dry_run = True

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
                mock_service.export_to_markdown.assert_called_with(dry_run=True)


class TestMainExtended:
    """Extended tests for main function."""

    def test_main_merge_command(self):
        """Test main with merge command."""
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode", "cs"]
                    MockRegistry.return_value = mock_registry

                    with patch("src.cli.handle_merge") as mock_handle:
                        mock_handle.return_value = 0

                        result = main(["merge", "cs"])

                        mock_handle.assert_called_once()

    def test_main_export_md_command(self):
        """Test main with export-md command."""
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    MockRegistry.return_value = mock_registry

                    with patch("src.cli.handle_export_md") as mock_handle:
                        mock_handle.return_value = 0

                        result = main(["export-md"])

                        mock_handle.assert_called_once()

    def test_main_unknown_subcommand(self):
        """Test main with unknown subcommand after generate."""
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    MockRegistry.return_value = mock_registry

                    # Using an invalid card_type should cause argparse to error
                    with pytest.raises(SystemExit):
                        main(["generate", "leetcode", "invalid_card_type"])

    def test_main_help_flag(self):
        """Test main with help flag."""
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    MockRegistry.return_value = mock_registry

                    with pytest.raises(SystemExit) as exc_info:
                        main(["--help"])

                    assert exc_info.value.code == 0

    def test_main_legacy_args_conversion(self):
        """Test main handles legacy args conversion."""
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode", "cs"]
                    mock_registry.is_valid_subject.return_value = True
                    mock_registry.get_config.return_value = MagicMock()
                    MockRegistry.return_value = mock_registry

                    with patch("src.cli.asyncio.run") as mock_run:
                        mock_run.return_value = 0

                        # Pass legacy args
                        with warnings.catch_warnings(record=True):
                            warnings.simplefilter("always")
                            result = main(["cs", "mcq"])

                        mock_run.assert_called_once()

    def test_main_argv_none(self):
        """Test main with argv=None uses sys.argv."""
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    MockRegistry.return_value = mock_registry

                    with patch("sys.argv", ["main.py"]):
                        result = main(None)

                        assert result == 0  # Shows help
