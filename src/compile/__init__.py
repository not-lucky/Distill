"""
LLM2Deck compile package.

Re-exports the public compile API and the ID-registry module-level state for
backward compatibility with the monolithic `src/compile.py` module. New code
should import from `src.compile` (the package) instead of the file path.

Public surface:
- compile_deck(...)
- main() (CLI entry point)
- reset_id_registry, generate_id (for tests)
- generated_ids, used_ids (module-level state, for tests)
- render_markdown, normalize_tag (for tests)
- shuffle_mcq_options (for tests)
- build_tags (for tests)
- load_json_data, resolve_deck_name (for tests)
- create_models, create_note_for_card (for tests)
"""

# Re-export module-level ID registry state. Tests previously mutated
# `src.compile.used_ids` to force collisions; we keep that contract.
from .deck import compile_deck
from .html import normalize_tag, render_markdown
from .ids import generated_ids, generate_id, reset_id_registry, used_ids
from .loader import load_json_data, resolve_deck_name
from .mcq import shuffle_mcq_options
from .models import create_models
from .notes import create_note_for_card
from .tags import build_tags

# Ensure attribute lookups via the package also see the live state.
# the underlying module.
__all__ = [
    "compile_deck",
    "normalize_tag",
    "render_markdown",
    "generate_id",
    "reset_id_registry",
    "generated_ids",
    "used_ids",
    "load_json_data",
    "resolve_deck_name",
    "shuffle_mcq_options",
    "build_tags",
    "create_models",
    "create_note_for_card",
]
