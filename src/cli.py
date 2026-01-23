"""Unified CLI for LLM2Deck."""

import argparse
import asyncio
import sys
import warnings
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src.config.subjects import SubjectRegistry, BUILTIN_SUBJECTS
from src.config.loader import load_config
from src.config.modes import (
    VALID_MODES,
    detect_mode_from_filename,
    get_deck_prefix,
)
from src.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)


def normalize_legacy_args(argv: list[str]) -> list[str]:
    """
    Convert legacy CLI syntax to new subcommand syntax.

    Old style: main.py <subject> [mcq] [--label=X]
    New style: main.py generate <subject> [mcq] [--label X]

    Args:
        argv: Command line arguments (excluding program name)

    Returns:
        Normalized argument list compatible with new subcommand syntax.
    """
    SUBCOMMANDS = {"generate", "convert", "merge", "export-md", "-h", "--help"}

    if not argv or argv[0] in SUBCOMMANDS:
        return argv

    # Old-style arguments detected - convert to new style
    warnings.warn(
        "Legacy CLI syntax is deprecated. Use 'llm2deck generate <subject> [card_type]' instead.",
        DeprecationWarning,
        stacklevel=3,
    )
    new_argv = ["generate"]
    for arg in argv:
        if arg.startswith("--label="):
            new_argv.extend(["--label", arg.split("=", 1)[1]])
        else:
            new_argv.append(arg)
    return new_argv


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""
    # Get available subjects from registry
    registry = SubjectRegistry()
    available_subjects = registry.get_available_subjects()

    parser = argparse.ArgumentParser(
        prog="llm2deck",
        description="Generate Anki flashcards using multiple LLMs in parallel.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ====== generate command ======
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate flashcards from LLM providers",
        description="Generate Anki flashcards using multiple LLMs in parallel.",
    )
    generate_parser.add_argument(
        "subject",
        nargs="?",
        default="leetcode",
        help=f"Subject to generate cards for (available: {', '.join(available_subjects)}, default: leetcode)",
    )
    generate_parser.add_argument(
        "card_type",
        nargs="?",
        default="standard",
        choices=["standard", "mcq"],
        help="Card type (default: standard)",
    )
    generate_parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Optional label for this run",
    )
    generate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making API calls or writing files",
    )
    generate_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass cache lookup (still stores new results)",
    )

    # ====== convert command ======
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert JSON deck to Anki .apkg format",
        description="Convert LLM JSON output to Anki .apkg package.",
    )
    convert_parser.add_argument(
        "json_file",
        type=str,
        help="Path to the JSON file containing synthesized cards",
    )
    convert_parser.add_argument(
        "--mode",
        default=None,
        choices=list(VALID_MODES),
        help="Mode of generation (auto-detected from filename if not specified)",
    )
    convert_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output .apkg filename (default: <input_stem>.apkg)",
    )
    convert_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )

    # ====== merge command ======
    merge_parser = subparsers.add_parser(
        "merge",
        help="Merge archived JSON files",
        description="Merge all JSON files from archival directory for a subject.",
    )
    merge_parser.add_argument(
        "subject",
        help=f"Subject to merge files for (available: {', '.join(available_subjects)})",
    )
    merge_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )

    # ====== export-md command ======
    export_parser = subparsers.add_parser(
        "export-md",
        help="Export JSON cards to Markdown",
        description="Convert archived JSON files to Markdown format.",
    )
    export_parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Source directory containing JSON files (default: from config)",
    )
    export_parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target directory for Markdown output (default: from config)",
    )
    export_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )

    return parser


# ====== Command Handlers ======


async def handle_generate(args: argparse.Namespace) -> int:
    """Handle the generate subcommand."""
    from src.orchestrator import Orchestrator

    is_mcq = args.card_type == "mcq"
    dry_run = getattr(args, "dry_run", False)
    no_cache = getattr(args, "no_cache", False)

    # Get subject configuration using registry
    registry = SubjectRegistry()
    if not registry.is_valid_subject(args.subject):
        available = registry.get_available_subjects()
        logger.error(
            f"Unknown subject '{args.subject}'. Available subjects: {', '.join(available)}"
        )
        return 1

    subject_config = registry.get_config(args.subject, is_mcq)

    if dry_run:
        logger.info(f"[DRY RUN] Subject={args.subject.upper()}, Card Type={args.card_type.upper()}")
    else:
        logger.info(f"Running: Subject={args.subject.upper()}, Card Type={args.card_type.upper()}")
    if args.label:
        logger.info(f"Run Label: {args.label}")
    if no_cache:
        logger.info("Cache lookup disabled (--no-cache)")

    orchestrator = Orchestrator(
        subject_config=subject_config,
        is_mcq=is_mcq,
        run_label=args.label,
        dry_run=dry_run,
        bypass_cache_lookup=no_cache,
    )

    if not await orchestrator.initialize():
        return 1

    problems = await orchestrator.run()
    orchestrator.save_results(problems)

    return 0


def handle_convert(args: argparse.Namespace) -> int:
    """Handle the convert subcommand."""
    from src.anki.generator import DeckGenerator, load_card_data

    dry_run = getattr(args, "dry_run", False)

    input_path = Path(args.json_file)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1

    # Auto-detect mode if not specified
    mode = args.mode
    if mode is None:
        mode = detect_mode_from_filename(args.json_file)
        logger.info(f"Auto-detected mode: {mode}")

    # Get deck prefix
    deck_prefix = get_deck_prefix(mode)

    # Determine output filename
    output_path = args.output if args.output else f"{input_path.stem}.apkg"

    if dry_run:
        logger.info(f"[DRY RUN] Would convert {input_path} to {output_path}")
        logger.info(f"[DRY RUN] Deck prefix: {deck_prefix}")
        try:
            card_data = load_card_data(str(input_path))
            card_count = sum(len(p.get("cards", [])) for p in card_data) if isinstance(card_data, list) else 0
            logger.info(f"[DRY RUN] Would process {len(card_data)} problems with {card_count} total cards")
        except Exception as error:
            logger.error(f"[DRY RUN] Failed to read input file: {error}")
            return 1
        return 0

    logger.info(f"Converting {input_path} to {output_path} (deck: {deck_prefix})")

    try:
        card_data = load_card_data(str(input_path))
        generator = DeckGenerator(card_data, deck_prefix=deck_prefix)
        generator.process()
        generator.save_package(output_path)
        logger.info(f"Successfully created: {output_path}")
        return 0
    except Exception as error:
        logger.error(f"Failed to create Anki deck: {error}")
        return 1


def handle_merge(args: argparse.Namespace) -> int:
    """Handle the merge subcommand."""
    from src.services.merge import MergeService

    dry_run = getattr(args, "dry_run", False)
    config = load_config()

    service = MergeService(
        archival_dir=Path(config.paths.archival_dir),
        timestamp_format=config.paths.timestamp_format,
    )
    result = service.merge_subject(args.subject, dry_run=dry_run)

    if not result.success:
        logger.error(result.error)
        return 1

    if dry_run:
        logger.info(f"[DRY RUN] Would merge {result.merged_count} files into {result.output_path}")
    else:
        logger.info(f"Successfully merged {result.merged_count} files.")
        logger.info(f"Output saved to: {result.output_path}")

    return 0


def handle_export_md(args: argparse.Namespace) -> int:
    """Handle the export-md subcommand."""
    from src.services.export import ExportService

    dry_run = getattr(args, "dry_run", False)
    config = load_config()

    source_path = Path(args.source if args.source else config.paths.archival_dir)
    target_path = Path(args.target if args.target else config.paths.markdown_dir)

    service = ExportService(source_dir=source_path, target_dir=target_path)
    result = service.export_to_markdown(dry_run=dry_run)

    if not result.success:
        logger.error(result.error)
        return 1

    if dry_run:
        logger.info(f"[DRY RUN] Would export {result.exported_count} JSON files to {target_path}")
    else:
        logger.info(f"Conversion complete. Exported {result.exported_count} files.")

    return 0


def main(argv: Optional[list] = None) -> int:
    """Main entry point for CLI."""
    setup_logging()
    load_dotenv()

    if argv is None:
        argv = sys.argv[1:]

    argv = normalize_legacy_args(argv)

    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "generate":
        return asyncio.run(handle_generate(args))
    elif args.command == "convert":
        return handle_convert(args)
    elif args.command == "merge":
        return handle_merge(args)
    elif args.command == "export-md":
        return handle_export_md(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
