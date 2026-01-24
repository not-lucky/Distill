"""Tests for CLI in src/cli.py."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import warnings

from assertpy import assert_that

from src.cli import (
    normalize_legacy_args,
    create_parser,
    handle_generate,
    handle_convert,
    handle_merge,
    handle_export_md,
    handle_cache,
    main,
)


class TestNormalizeLegacyArgs:
    """Tests for normalize_legacy_args function."""

    def test_empty_args(self):
        """
        Given empty argument list
        When normalize_legacy_args is called
        Then empty list is returned
        """
        result = normalize_legacy_args([])
        assert_that(result).is_equal_to([])

    def test_new_style_generate(self):
        """
        Given new-style generate command
        When normalize_legacy_args is called
        Then args pass through unchanged
        """
        args = ["generate", "leetcode", "standard"]
        result = normalize_legacy_args(args)
        assert_that(result).is_equal_to(args)

    def test_new_style_convert(self):
        """
        Given new-style convert command
        When normalize_legacy_args is called
        Then args pass through unchanged
        """
        args = ["convert", "file.json"]
        result = normalize_legacy_args(args)
        assert_that(result).is_equal_to(args)

    def test_new_style_merge(self):
        """
        Given new-style merge command
        When normalize_legacy_args is called
        Then args pass through unchanged
        """
        args = ["merge", "cs"]
        result = normalize_legacy_args(args)
        assert_that(result).is_equal_to(args)

    def test_new_style_export_md(self):
        """
        Given new-style export-md command
        When normalize_legacy_args is called
        Then args pass through unchanged
        """
        args = ["export-md", "--source", "./dir"]
        result = normalize_legacy_args(args)
        assert_that(result).is_equal_to(args)

    def test_help_flag(self):
        """
        Given help flag
        When normalize_legacy_args is called
        Then flag passes through unchanged
        """
        for flag in ["-h", "--help"]:
            result = normalize_legacy_args([flag])
            assert_that(result).is_equal_to([flag])

    def test_legacy_subject_only(self):
        """
        Given legacy style with subject only
        When normalize_legacy_args is called
        Then generate command is prepended and deprecation warning is issued
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = normalize_legacy_args(["leetcode"])
            assert_that(result).is_equal_to(["generate", "leetcode"])
            assert_that(w).is_length(1)
            assert_that(str(w[0].message).lower()).contains("deprecated")

    def test_legacy_subject_with_mcq(self):
        """
        Given legacy style with subject and mcq
        When normalize_legacy_args is called
        Then generate command is prepended
        """
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["cs", "mcq"])
            assert_that(result).is_equal_to(["generate", "cs", "mcq"])

    def test_legacy_with_label_equals(self):
        """
        Given legacy style with --label=value format
        When normalize_legacy_args is called
        Then label is split and generate is prepended
        """
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["physics", "--label=test"])
            assert_that(result).is_equal_to(["generate", "physics", "--label", "test"])


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
        """
        Given generate command with no arguments
        When parsed
        Then default subject is leetcode and card_type is standard
        """
        args = parser.parse_args(["generate"])
        assert_that(args.command).is_equal_to("generate")
        assert_that(args.subject).is_equal_to("leetcode")
        assert_that(args.card_type).is_equal_to("standard")

    def test_generate_command_with_subject(self, parser):
        """
        Given generate command with explicit subject
        When parsed
        Then subject is set correctly
        """
        args = parser.parse_args(["generate", "cs"])
        assert_that(args.subject).is_equal_to("cs")
        assert_that(args.card_type).is_equal_to("standard")

    def test_generate_command_mcq(self, parser):
        """
        Given generate command with MCQ card type
        When parsed
        Then card_type is mcq
        """
        args = parser.parse_args(["generate", "physics", "mcq"])
        assert_that(args.subject).is_equal_to("physics")
        assert_that(args.card_type).is_equal_to("mcq")

    def test_generate_command_with_label(self, parser):
        """
        Given generate command with label
        When parsed
        Then label is set correctly
        """
        args = parser.parse_args(["generate", "leetcode", "--label", "test run"])
        assert_that(args.label).is_equal_to("test run")

    def test_generate_command_dry_run(self, parser):
        """
        Given generate command with dry-run flag
        When parsed
        Then dry_run is True
        """
        args = parser.parse_args(["generate", "--dry-run"])
        assert_that(args.dry_run).is_true()

    def test_convert_command(self, parser):
        """
        Given convert command with json file
        When parsed
        Then command and json_file are set correctly
        """
        args = parser.parse_args(["convert", "deck.json"])
        assert_that(args.command).is_equal_to("convert")
        assert_that(args.json_file).is_equal_to("deck.json")

    def test_convert_command_with_mode(self, parser):
        """
        Given convert command with explicit mode
        When parsed
        Then mode is set correctly
        """
        args = parser.parse_args(["convert", "deck.json", "--mode", "cs_mcq"])
        assert_that(args.mode).is_equal_to("cs_mcq")

    def test_convert_command_with_output(self, parser):
        """
        Given convert command with output path
        When parsed
        Then output is set correctly
        """
        args = parser.parse_args(["convert", "deck.json", "-o", "output.apkg"])
        assert_that(args.output).is_equal_to("output.apkg")

    def test_merge_command(self, parser):
        """
        Given merge command with subject
        When parsed
        Then command and subject are set correctly
        """
        args = parser.parse_args(["merge", "cs"])
        assert_that(args.command).is_equal_to("merge")
        assert_that(args.subject).is_equal_to("cs")

    def test_export_md_command(self, parser):
        """
        Given export-md command
        When parsed
        Then command is set and paths are None by default
        """
        args = parser.parse_args(["export-md"])
        assert_that(args.command).is_equal_to("export-md")
        assert_that(args.source).is_none()
        assert_that(args.target).is_none()

    def test_export_md_command_with_paths(self, parser):
        """
        Given export-md command with paths
        When parsed
        Then paths are set correctly
        """
        args = parser.parse_args(["export-md", "--source", "./in", "--target", "./out"])
        assert_that(args.source).is_equal_to("./in")
        assert_that(args.target).is_equal_to("./out")


class TestHandleGenerate:
    """Tests for handle_generate function."""

    @pytest.mark.asyncio
    async def test_handle_generate_success(self):
        """
        Given valid generate arguments
        When handle_generate is called
        Then it returns 0 for success
        """
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

                assert_that(result).is_equal_to(0)

    @pytest.mark.asyncio
    async def test_handle_generate_invalid_subject(self):
        """
        Given invalid subject
        When handle_generate is called
        Then it returns 1 for failure
        """
        args = MagicMock()
        args.subject = "invalid"
        args.card_type = "standard"

        with patch("src.cli.SubjectRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.is_valid_subject.return_value = False
            mock_registry.get_available_subjects.return_value = ["leetcode", "cs"]
            MockRegistry.return_value = mock_registry

            result = await handle_generate(args)

            assert_that(result).is_equal_to(1)

    @pytest.mark.asyncio
    async def test_handle_generate_init_fails(self):
        """
        Given orchestrator initialization failure
        When handle_generate is called
        Then it returns 1 for failure
        """
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

                assert_that(result).is_equal_to(1)


class TestHandleConvert:
    """Tests for handle_convert function."""

    def test_handle_convert_file_not_found(self, tmp_path):
        """
        Given non-existent file
        When handle_convert is called
        Then it returns 1 for failure
        """
        args = MagicMock()
        args.json_file = str(tmp_path / "nonexistent.json")
        args.mode = None
        args.output = None
        args.dry_run = False

        result = handle_convert(args)

        assert_that(result).is_equal_to(1)

    def test_handle_convert_success(self, tmp_path):
        """
        Given valid JSON file
        When handle_convert is called
        Then it returns 0 for success
        """
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

                assert_that(result).is_equal_to(0)

    def test_handle_convert_dry_run(self, tmp_path):
        """
        Given dry run mode
        When handle_convert is called
        Then it returns 0 for success without creating output
        """
        input_file = tmp_path / "test.json"
        input_file.write_text('[{"title": "Test", "cards": [{"front": "Q", "back": "A"}]}]')

        args = MagicMock()
        args.json_file = str(input_file)
        args.mode = "leetcode"
        args.output = None
        args.dry_run = True

        result = handle_convert(args)

        assert_that(result).is_equal_to(0)


class TestHandleMerge:
    """Tests for handle_merge function."""

    def test_handle_merge_success(self):
        """
        Given valid merge arguments
        When handle_merge is called
        Then it returns 0 for success
        """
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

                assert_that(result).is_equal_to(0)

    def test_handle_merge_failure(self):
        """
        Given merge failure
        When handle_merge is called
        Then it returns 1 for failure
        """
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

                assert_that(result).is_equal_to(1)


class TestHandleExportMd:
    """Tests for handle_export_md function."""

    def test_handle_export_md_success(self):
        """
        Given valid export arguments
        When handle_export_md is called
        Then it returns 0 for success
        """
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

                assert_that(result).is_equal_to(0)

    def test_handle_export_md_failure(self):
        """
        Given export failure
        When handle_export_md is called
        Then it returns 1 for failure
        """
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

                assert_that(result).is_equal_to(1)


class TestMain:
    """Tests for main function."""

    def test_main_no_command(self):
        """
        Given no command
        When main is called
        Then it shows help and returns 0
        """
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    MockRegistry.return_value = mock_registry

                    result = main([])

                    assert_that(result).is_equal_to(0)

    def test_main_generate_command(self):
        """
        Given generate command
        When main is called
        Then asyncio.run is called
        """
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

                            assert_that(mock_run.called).is_true()

    def test_main_convert_command(self, tmp_path):
        """
        Given convert command
        When main is called
        Then handle_convert is called
        """
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
        """
        Given legacy style with mcq and label
        When normalize_legacy_args is called
        Then generate is prepended and label is split
        """
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["leetcode", "mcq", "--label=test"])
            assert_that(result).is_equal_to(["generate", "leetcode", "mcq", "--label", "test"])

    def test_legacy_physics_subject(self):
        """
        Given legacy physics subject
        When normalize_legacy_args is called
        Then generate is prepended
        """
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["physics"])
            assert_that(result).is_equal_to(["generate", "physics"])

    def test_legacy_custom_subject(self):
        """
        Given legacy custom subject
        When normalize_legacy_args is called
        Then generate is prepended
        """
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = normalize_legacy_args(["my_custom"])
            assert_that(result).is_equal_to(["generate", "my_custom"])

    def test_generate_with_args_passes_through(self):
        """
        Given generate with all args
        When normalize_legacy_args is called
        Then args pass through unchanged
        """
        args = ["generate", "cs", "mcq", "--label", "test", "--dry-run"]
        result = normalize_legacy_args(args)
        assert_that(result).is_equal_to(args)

    def test_convert_with_all_args(self):
        """
        Given convert with all arguments
        When normalize_legacy_args is called
        Then args pass through unchanged
        """
        args = ["convert", "file.json", "--mode", "cs_mcq", "-o", "out.apkg"]
        result = normalize_legacy_args(args)
        assert_that(result).is_equal_to(args)

    def test_merge_with_args(self):
        """
        Given merge with arguments
        When normalize_legacy_args is called
        Then args pass through unchanged
        """
        args = ["merge", "physics", "--dry-run"]
        result = normalize_legacy_args(args)
        assert_that(result).is_equal_to(args)

    def test_export_md_with_all_args(self):
        """
        Given export-md with all arguments
        When normalize_legacy_args is called
        Then args pass through unchanged
        """
        args = ["export-md", "--source", "./in", "--target", "./out", "--dry-run"]
        result = normalize_legacy_args(args)
        assert_that(result).is_equal_to(args)


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
        """
        Given generate with all options
        When parsed
        Then all options are set correctly
        """
        args = parser.parse_args(["generate", "cs", "mcq", "--label", "test", "--dry-run"])
        assert_that(args.subject).is_equal_to("cs")
        assert_that(args.card_type).is_equal_to("mcq")
        assert_that(args.label).is_equal_to("test")
        assert_that(args.dry_run).is_true()

    def test_convert_all_options(self, parser):
        """
        Given convert with all options
        When parsed
        Then all options are set correctly
        """
        args = parser.parse_args(["convert", "deck.json", "--mode", "physics_mcq", "-o", "out.apkg", "--dry-run"])
        assert_that(args.json_file).is_equal_to("deck.json")
        assert_that(args.mode).is_equal_to("physics_mcq")
        assert_that(args.output).is_equal_to("out.apkg")
        assert_that(args.dry_run).is_true()

    def test_convert_mode_choices(self, parser):
        """
        Given convert with valid mode choices
        When parsed
        Then mode is set correctly for each choice
        """
        for mode in ["leetcode", "leetcode_mcq", "cs", "cs_mcq", "physics", "physics_mcq"]:
            args = parser.parse_args(["convert", "deck.json", "--mode", mode])
            assert_that(args.mode).is_equal_to(mode)

    def test_merge_with_dry_run(self, parser):
        """
        Given merge with dry-run flag
        When parsed
        Then dry_run is True
        """
        args = parser.parse_args(["merge", "cs", "--dry-run"])
        assert_that(args.subject).is_equal_to("cs")
        assert_that(args.dry_run).is_true()

    def test_export_md_with_dry_run(self, parser):
        """
        Given export-md with dry-run flag
        When parsed
        Then dry_run is True
        """
        args = parser.parse_args(["export-md", "--dry-run"])
        assert_that(args.dry_run).is_true()

    def test_generate_card_type_choices(self, parser):
        """
        Given generate with valid card_type choices
        When parsed
        Then card_type is set correctly for each choice
        """
        for card_type in ["standard", "mcq"]:
            args = parser.parse_args(["generate", "leetcode", card_type])
            assert_that(args.card_type).is_equal_to(card_type)


class TestHandleGenerateExtended:
    """Extended tests for handle_generate function."""

    @pytest.mark.asyncio
    async def test_handle_generate_dry_run(self):
        """
        Given dry run mode
        When handle_generate is called
        Then orchestrator is called with dry_run=True
        """
        args = MagicMock()
        args.subject = "leetcode"
        args.card_type = "standard"
        args.label = None
        args.dry_run = True
        args.no_cache = False
        args.resume = None

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

                assert_that(result).is_equal_to(0)
                MockOrch.assert_called_with(
                    subject_config=mock_registry.get_config.return_value,
                    is_mcq=False,
                    run_label=None,
                    dry_run=True,
                    bypass_cache_lookup=False,
                    resume_run_id=None,
                )

    @pytest.mark.asyncio
    async def test_handle_generate_mcq_mode(self):
        """
        Given MCQ card type
        When handle_generate is called
        Then orchestrator is called with is_mcq=True
        """
        args = MagicMock()
        args.subject = "cs"
        args.card_type = "mcq"
        args.label = "test-mcq"
        args.dry_run = False
        args.no_cache = False
        args.resume = None

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

                assert_that(result).is_equal_to(0)
                MockOrch.assert_called_with(
                    subject_config=mock_registry.get_config.return_value,
                    is_mcq=True,
                    run_label="test-mcq",
                    dry_run=False,
                    bypass_cache_lookup=False,
                    resume_run_id=None,
                )

    @pytest.mark.asyncio
    async def test_handle_generate_with_label(self):
        """
        Given user label
        When handle_generate is called
        Then label is passed to orchestrator
        """
        args = MagicMock()
        args.subject = "physics"
        args.card_type = "standard"
        args.label = "my-run-label"
        args.dry_run = False
        args.no_cache = False

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

                assert_that(result).is_equal_to(0)
                # Verify label was passed
                call_kwargs = MockOrch.call_args.kwargs
                assert_that(call_kwargs["run_label"]).is_equal_to("my-run-label")


class TestHandleConvertExtended:
    """Extended tests for handle_convert function."""

    def test_handle_convert_auto_detect_mode(self, tmp_path):
        """
        Given filename with mode hint
        When handle_convert is called with mode=None
        Then mode is auto-detected
        """
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

                assert_that(result).is_equal_to(0)

    def test_handle_convert_explicit_output_path(self, tmp_path):
        """
        Given explicit output path
        When handle_convert is called
        Then save_package is called with that path
        """
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

                assert_that(result).is_equal_to(0)
                mock_gen.save_package.assert_called_with(str(output_file))

    def test_handle_convert_exception_handling(self, tmp_path):
        """
        Given exception during conversion
        When handle_convert is called
        Then it returns 1 for failure
        """
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

            assert_that(result).is_equal_to(1)

    def test_handle_convert_dry_run_with_error(self, tmp_path):
        """
        Given dry run with read error
        When handle_convert is called
        Then it returns 1 for failure
        """
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

            assert_that(result).is_equal_to(1)


class TestHandleMergeExtended:
    """Extended tests for handle_merge function."""

    def test_handle_merge_dry_run(self):
        """
        Given dry run mode
        When handle_merge is called
        Then merge_subject is called with dry_run=True
        """
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

                assert_that(result).is_equal_to(0)
                mock_service.merge_subject.assert_called_with("physics", dry_run=True)

    def test_handle_merge_error_message(self):
        """
        Given merge failure with error message
        When handle_merge is called
        Then it returns 1 for failure
        """
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

                assert_that(result).is_equal_to(1)


class TestHandleExportMdExtended:
    """Extended tests for handle_export_md function."""

    def test_handle_export_md_with_custom_paths(self):
        """
        Given custom source and target paths
        When handle_export_md is called
        Then ExportService is called with those paths
        """
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

                assert_that(result).is_equal_to(0)
                MockService.assert_called_with(
                    source_dir=Path("/custom/source"),
                    target_dir=Path("/custom/target")
                )

    def test_handle_export_md_dry_run(self):
        """
        Given dry run mode
        When handle_export_md is called
        Then export_to_markdown is called with dry_run=True
        """
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

                assert_that(result).is_equal_to(0)
                mock_service.export_to_markdown.assert_called_with(dry_run=True)


class TestMainExtended:
    """Extended tests for main function."""

    def test_main_merge_command(self):
        """
        Given merge command
        When main is called
        Then handle_merge is called
        """
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
        """
        Given export-md command
        When main is called
        Then handle_export_md is called
        """
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
        """
        Given unknown subcommand after generate
        When main is called
        Then SystemExit is raised
        """
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
        """
        Given help flag
        When main is called
        Then SystemExit with code 0 is raised
        """
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    MockRegistry.return_value = mock_registry

                    with pytest.raises(SystemExit) as exc_info:
                        main(["--help"])

                    assert_that(exc_info.value.code).is_equal_to(0)

    def test_main_legacy_args_conversion(self):
        """
        Given legacy args
        When main is called
        Then asyncio.run is called after conversion
        """
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
        """
        Given argv=None
        When main is called
        Then sys.argv is used and help is shown
        """
        with patch("src.cli.setup_logging"):
            with patch("src.cli.load_dotenv"):
                with patch("src.cli.SubjectRegistry") as MockRegistry:
                    mock_registry = MagicMock()
                    mock_registry.get_available_subjects.return_value = ["leetcode"]
                    MockRegistry.return_value = mock_registry

                    with patch("sys.argv", ["main.py"]):
                        result = main(None)

                        assert_that(result).is_equal_to(0)  # Shows help


class TestHandleCache:
    """Tests for handle_cache function."""

    def test_handle_cache_no_subcommand(self, capsys):
        """
        Given cache command with no subcommand
        When handle_cache is called
        Then it prints usage and returns 1
        """
        args = MagicMock()
        args.cache_command = None

        result = handle_cache(args)

        assert_that(result).is_equal_to(1)
        captured = capsys.readouterr()
        assert_that(captured.out).contains("Usage: llm2deck cache")

    def test_handle_cache_clear_success(self, capsys):
        """
        Given cache clear command
        When handle_cache is called
        Then it clears cache and returns 0
        """
        args = MagicMock()
        args.cache_command = "clear"

        with patch("src.database.DatabaseManager") as MockDbManager:
            mock_db = MagicMock()
            mock_session = MagicMock()
            mock_db.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_db.session_scope.return_value.__exit__ = MagicMock(return_value=False)
            MockDbManager.get_default.return_value = mock_db

            with patch("src.cache.CacheRepository") as MockRepo:
                mock_repo = MagicMock()
                mock_repo.clear.return_value = 5
                MockRepo.return_value = mock_repo

                result = handle_cache(args)

                assert_that(result).is_equal_to(0)
                mock_repo.clear.assert_called_once()
                captured = capsys.readouterr()
                assert_that(captured.out).contains("Cleared 5 cache entries")

    def test_handle_cache_stats_success(self, capsys):
        """
        Given cache stats command
        When handle_cache is called
        Then it prints stats and returns 0
        """
        args = MagicMock()
        args.cache_command = "stats"

        with patch("src.database.DatabaseManager") as MockDbManager:
            mock_db = MagicMock()
            mock_session = MagicMock()
            mock_db.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_db.session_scope.return_value.__exit__ = MagicMock(return_value=False)
            MockDbManager.get_default.return_value = mock_db

            with patch("src.cache.CacheRepository") as MockRepo:
                mock_repo = MagicMock()
                mock_repo.stats.return_value = {"total_entries": 10, "total_hits": 25}
                MockRepo.return_value = mock_repo

                result = handle_cache(args)

                assert_that(result).is_equal_to(0)
                mock_repo.stats.assert_called_once()
                captured = capsys.readouterr()
                assert_that(captured.out).contains("Cache entries: 10")
                assert_that(captured.out).contains("Total hits: 25")

    def test_handle_cache_unknown_subcommand(self, capsys):
        """
        Given cache command with unknown subcommand
        When handle_cache is called
        Then it returns 1
        """
        args = MagicMock()
        args.cache_command = "unknown"

        with patch("src.database.DatabaseManager") as MockDbManager:
            mock_db = MagicMock()
            mock_db.session_scope.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_db.session_scope.return_value.__exit__ = MagicMock(return_value=False)
            MockDbManager.get_default.return_value = mock_db

            result = handle_cache(args)

            assert_that(result).is_equal_to(1)
