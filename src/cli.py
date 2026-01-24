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
    SUBCOMMANDS = {"generate", "convert", "merge", "export-md", "cache", "query", "-h", "--help"}

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
    generate_parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="RUN_ID",
        help="Resume a failed/interrupted run (skips already-processed questions)",
    )
    generate_parser.add_argument(
        "--category",
        type=str,
        default=None,
        metavar="CATEGORY",
        help="Only generate cards for specific category (case-insensitive partial match)",
    )
    generate_parser.add_argument(
        "--question",
        type=str,
        default=None,
        metavar="NAME",
        help="Generate cards for questions matching this name (case-insensitive partial match)",
    )
    generate_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of questions to process (for testing)",
    )
    generate_parser.add_argument(
        "--skip-until",
        type=str,
        default=None,
        metavar="NAME",
        help="Skip questions until reaching this one (case-insensitive partial match)",
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

    # ====== cache command ======
    cache_parser = subparsers.add_parser(
        "cache",
        help="Cache management commands",
        description="Manage LLM response cache.",
    )
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", help="Cache operations")

    # cache clear
    cache_clear_parser = cache_subparsers.add_parser(
        "clear",
        help="Clear all cached LLM responses",
    )

    # cache stats
    cache_stats_parser = cache_subparsers.add_parser(
        "stats",
        help="Show cache statistics",
    )

    # ====== query command ======
    query_parser = subparsers.add_parser(
        "query",
        help="Query database for runs, problems, cards, and statistics",
        description="Query the LLM2Deck database.",
    )
    query_subparsers = query_parser.add_subparsers(dest="query_command", help="Query operations")

    # Common query options
    def add_format_option(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--format",
            "-f",
            choices=["table", "json"],
            default="table",
            help="Output format (default: table)",
        )

    def add_limit_option(parser: argparse.ArgumentParser, default: int = 20) -> None:
        parser.add_argument(
            "--limit",
            "-n",
            type=int,
            default=default,
            help=f"Maximum number of results (default: {default})",
        )

    # query runs
    query_runs_parser = query_subparsers.add_parser(
        "runs",
        help="List generation runs",
    )
    query_runs_parser.add_argument(
        "--subject",
        "-s",
        type=str,
        default=None,
        help="Filter by subject (leetcode, cs, physics, etc.)",
    )
    query_runs_parser.add_argument(
        "--status",
        type=str,
        choices=["running", "completed", "failed"],
        default=None,
        help="Filter by status",
    )
    add_limit_option(query_runs_parser)
    add_format_option(query_runs_parser)

    # query run <id>
    query_run_parser = query_subparsers.add_parser(
        "run",
        help="Show details for a specific run",
    )
    query_run_parser.add_argument(
        "run_id",
        type=str,
        help="Run ID (can be partial, will match prefix)",
    )
    add_format_option(query_run_parser)

    # query problems
    query_problems_parser = query_subparsers.add_parser(
        "problems",
        help="List problems",
    )
    query_problems_parser.add_argument(
        "--run",
        "-r",
        type=str,
        default=None,
        help="Filter by run ID",
    )
    query_problems_parser.add_argument(
        "--status",
        type=str,
        choices=["running", "success", "failed", "partial"],
        default=None,
        help="Filter by status",
    )
    query_problems_parser.add_argument(
        "--search",
        "-q",
        type=str,
        default=None,
        help="Search in question names",
    )
    add_limit_option(query_problems_parser)
    add_format_option(query_problems_parser)

    # query providers
    query_providers_parser = query_subparsers.add_parser(
        "providers",
        help="List provider results",
    )
    query_providers_parser.add_argument(
        "--run",
        "-r",
        type=str,
        default=None,
        help="Filter by run ID",
    )
    query_providers_parser.add_argument(
        "--provider",
        "-p",
        type=str,
        default=None,
        help="Filter by provider name",
    )
    query_providers_parser.add_argument(
        "--success",
        action="store_true",
        default=None,
        help="Show only successful results",
    )
    query_providers_parser.add_argument(
        "--failed",
        action="store_true",
        default=None,
        help="Show only failed results",
    )
    add_limit_option(query_providers_parser)
    add_format_option(query_providers_parser)

    # query cards
    query_cards_parser = query_subparsers.add_parser(
        "cards",
        help="List and search cards",
    )
    query_cards_parser.add_argument(
        "--run",
        "-r",
        type=str,
        default=None,
        help="Filter by run ID",
    )
    query_cards_parser.add_argument(
        "--type",
        "-t",
        type=str,
        default=None,
        help="Filter by card type",
    )
    query_cards_parser.add_argument(
        "--search",
        "-q",
        type=str,
        default=None,
        help="Search in card content (front/back)",
    )
    add_limit_option(query_cards_parser)
    add_format_option(query_cards_parser)

    # query stats
    query_stats_parser = query_subparsers.add_parser(
        "stats",
        help="Show global statistics",
    )
    query_stats_parser.add_argument(
        "--subject",
        "-s",
        type=str,
        default=None,
        help="Filter by subject",
    )
    add_format_option(query_stats_parser)

    return parser


# ====== Command Handlers ======


async def handle_generate(args: argparse.Namespace) -> int:
    """Handle the generate subcommand."""
    from src.orchestrator import Orchestrator
    from src.questions import QuestionFilter

    is_mcq = args.card_type == "mcq"
    dry_run = getattr(args, "dry_run", False)
    no_cache = getattr(args, "no_cache", False)
    resume_run_id = getattr(args, "resume", None)

    # Build question filter from CLI args
    question_filter = QuestionFilter(
        category=getattr(args, "category", None),
        question_name=getattr(args, "question", None),
        limit=getattr(args, "limit", None),
        skip_until=getattr(args, "skip_until", None),
    )

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
    if resume_run_id:
        logger.info(f"Resuming run: {resume_run_id}")
    if question_filter.has_filters():
        filter_parts = []
        if question_filter.category:
            filter_parts.append(f"category='{question_filter.category}'")
        if question_filter.question_name:
            filter_parts.append(f"question='{question_filter.question_name}'")
        if question_filter.skip_until:
            filter_parts.append(f"skip-until='{question_filter.skip_until}'")
        if question_filter.limit:
            filter_parts.append(f"limit={question_filter.limit}")
        logger.info(f"Question filters: {', '.join(filter_parts)}")

    orchestrator = Orchestrator(
        subject_config=subject_config,
        is_mcq=is_mcq,
        run_label=args.label,
        dry_run=dry_run,
        bypass_cache_lookup=no_cache,
        resume_run_id=resume_run_id,
        question_filter=question_filter if question_filter.has_filters() else None,
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


def handle_cache(args: argparse.Namespace) -> int:
    """Handle the cache subcommand."""
    from src.config import DATABASE_PATH
    from src.database import DatabaseManager
    from src.cache import CacheRepository

    if args.cache_command is None:
        print("Usage: llm2deck cache {clear,stats}")
        print("Run 'llm2deck cache --help' for more information.")
        return 1

    # Initialize database if needed
    db_manager = DatabaseManager.get_default()
    db_manager.initialize(DATABASE_PATH)

    if args.cache_command == "clear":
        with db_manager.session_scope() as session:
            repo = CacheRepository(session)
            count = repo.clear()
            print(f"Cleared {count} cache entries.")
        return 0

    elif args.cache_command == "stats":
        with db_manager.session_scope() as session:
            repo = CacheRepository(session)
            stats = repo.stats()
            print(f"Cache entries: {stats['total_entries']}")
            print(f"Total hits: {stats['total_hits']}")
        return 0

    return 1


def handle_query(args: argparse.Namespace) -> int:
    """Handle the query subcommand."""
    from src.config import DATABASE_PATH
    from src.database import DatabaseManager
    from src.services.query import QueryService

    if args.query_command is None:
        print("Usage: llm2deck query {runs,run,problems,providers,cards,stats}")
        print("Run 'llm2deck query --help' for more information.")
        return 1

    # Initialize database
    db_manager = DatabaseManager.get_default()
    if not db_manager.is_initialized:
        db_manager.initialize(DATABASE_PATH)

    service = QueryService()
    output_format = getattr(args, "format", "table")

    if args.query_command == "runs":
        result = service.list_runs(
            subject=getattr(args, "subject", None),
            status=getattr(args, "status", None),
            limit=getattr(args, "limit", 20),
            output_format=output_format,
        )
    elif args.query_command == "run":
        result = service.show_run(
            run_id=args.run_id,
            output_format=output_format,
        )
    elif args.query_command == "problems":
        result = service.list_problems(
            run_id=getattr(args, "run", None),
            status=getattr(args, "status", None),
            question_search=getattr(args, "search", None),
            limit=getattr(args, "limit", 20),
            output_format=output_format,
        )
    elif args.query_command == "providers":
        # Handle --success and --failed flags
        success_filter = None
        if getattr(args, "success", False):
            success_filter = True
        elif getattr(args, "failed", False):
            success_filter = False

        result = service.list_providers(
            run_id=getattr(args, "run", None),
            provider_name=getattr(args, "provider", None),
            success=success_filter,
            limit=getattr(args, "limit", 20),
            output_format=output_format,
        )
    elif args.query_command == "cards":
        result = service.list_cards(
            run_id=getattr(args, "run", None),
            card_type=getattr(args, "type", None),
            search_query=getattr(args, "search", None),
            limit=getattr(args, "limit", 20),
            output_format=output_format,
        )
    elif args.query_command == "stats":
        result = service.show_stats(
            subject=getattr(args, "subject", None),
            output_format=output_format,
        )
    else:
        print("Unknown query command")
        return 1

    if not result.success:
        print(f"Error: {result.error}")
        return 1

    if result.message:
        print(result.message)
    if result.data:
        print(result.data)

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
    elif args.command == "cache":
        return handle_cache(args)
    elif args.command == "query":
        return handle_query(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
