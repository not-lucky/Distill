"""
Top-level Anki deck compilation for Distill.

This module orchestrates loading, model creation, note generation, and
writing the final `.apkg` package. It is intentionally thin: all logic lives
in the focused submodules.
"""

import genanki

from .ids import generate_id
from .loader import load_json_data, resolve_deck_name
from .models import create_models
from .notes import create_note_for_card


def compile_deck(
    json_data,
    output_path: str,
    deck_name: str | None = None,
    subject: str | None = None,
    source: str | None = None,
):
    """
    Main function to parse input JSON, generate notes, and compile to an Anki .apkg package.
    """
    topics, source = load_json_data(json_data, source)
    deck_name = resolve_deck_name(topics, deck_name)
    models = create_models()

    deck_id = generate_id(deck_name)
    deck = genanki.Deck(deck_id, deck_name)

    for topic_data in topics:
        if not isinstance(topic_data, dict):
            continue

        cards = topic_data.get("cards")
        if not isinstance(cards, list):
            cards = []

        for card in cards:
            if not isinstance(card, dict):
                continue
            note = create_note_for_card(
                card, topic_data, models, deck_name, source, subject
            )
            if note is not None:
                deck.add_note(note)

    # Save to file
    pkg = genanki.Package(deck)
    pkg.write_to_file(output_path)
    print(f"Successfully compiled {len(deck.notes)} cards into '{output_path}'")
