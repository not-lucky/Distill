#!/usr/bin/env python3
"""
Backward-compatible CLI entry point for LLM2Deck's Anki compiler.

The implementation has been split into the `src/compile/` package; this
file exists solely so the historical subprocess invocation
`uv run src/compile.py …` (used by `src/pipeline/compiler.js` and the
CLI tests) continues to work. When both this file and the package
directory exist, Python's import system prefers the package, so
`from src.compile import compile_deck` resolves to the package, and
running this file as a script also imports the package.

Re-exports public names AND exposes the historical module-level ID
registry state (`generated_ids`, `used_ids`) so tests that previously
mutated `src.compile.used_ids` directly continue to work.
"""

import argparse
import os
import sys

# Importing the package re-exports the public surface. The names below
# are intentionally re-exported even when not referenced in this file,
# because `python src/compile.py` historically exposed them as module
# attributes; tests and downstream code rely on that contract.
from compile import (  # noqa: F401,E402  pylint: disable=wrong-import-position
    build_tags,
    compile_deck,
    create_models,
    create_note_for_card,
    generate_id,
    load_json_data,
    normalize_tag,
    render_markdown,
    reset_id_registry,
    resolve_deck_name,
    shuffle_mcq_options,
)


def main() -> None:
    """CLI entry point: parse args, then call compile_deck."""
    parser = argparse.ArgumentParser(
        description="Compile Stage 3 JSON cards into Anki .apkg deck."
    )
    parser.add_argument("json_file", help="Path to input Stage 3 JSON file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to output .apkg file. Defaults to <json_file_basename>.apkg.",
    )
    parser.add_argument(
        "--deck-name",
        help="Override the deck name. Defaults to the 'topic' field in JSON.",
    )
    parser.add_argument(
        "--subject",
        help="Subject metadata for taxonomy tagging (e.g. 'CS/Algorithms').",
    )
    parser.add_argument(
        "--source", help="Source filename override for taxonomy tagging."
    )

    args = parser.parse_args()

    if not os.path.exists(args.json_file):
        print(
            f"Error: Input JSON file '{args.json_file}' does not exist.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Determine default output path if not specified
    if not args.output:
        base = os.path.splitext(args.json_file)[0]
        args.output = f"{base}.apkg"

    try:
        compile_deck(
            json_data=args.json_file,
            output_path=args.output,
            deck_name=args.deck_name,
            subject=args.subject,
            source=args.source,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Compilation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
