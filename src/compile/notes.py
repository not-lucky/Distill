"""
genanki Note construction from card dictionaries.

Selects the right Model (Basic, Cloze, MCQ) based on the card's `card_format`
field, builds the field list, and tags the note for hierarchical filtering in
Anki. Unsupported card formats are skipped with a warning rather than
crashing the entire compile.
"""

import sys

import genanki

from .html import render_markdown
from .mcq import shuffle_mcq_options
from .tags import build_tags


def _create_basic_note(
    card, topic, title, difficulty, tags_str, unique_tags, deck_name, basic_model
):
    return genanki.Note(
        model=basic_model,
        fields=[
            render_markdown(card.get("front", "")),
            render_markdown(card.get("back", "")),
            render_markdown(card.get("explanation", "")),
            card.get("card_type", "Concept"),
            topic,
            title,
            difficulty,
            tags_str,
        ],
        tags=unique_tags,
        guid=genanki.guid_for(card.get("front", ""), deck_name),
    )


def _create_cloze_note(
    card, topic, title, difficulty, tags_str, unique_tags, deck_name, cloze_model
):
    return genanki.Note(
        model=cloze_model,
        fields=[
            render_markdown(card.get("front", "")),
            render_markdown(card.get("explanation", "")),
            card.get("card_type", "Concept"),
            topic,
            title,
            difficulty,
            tags_str,
        ],
        tags=unique_tags,
        guid=genanki.guid_for(card.get("front", ""), deck_name),
    )


def _create_mcq_note(
    card, topic, title, difficulty, tags_str, unique_tags, deck_name, mcq_model
):
    shuffled_options, new_correct_letter = shuffle_mcq_options(
        card.get("options", []), card.get("correct_answer", "A")
    )
    return genanki.Note(
        model=mcq_model,
        fields=[
            render_markdown(card.get("front", "")),
            render_markdown(shuffled_options[0], inline=True),
            render_markdown(shuffled_options[1], inline=True),
            render_markdown(shuffled_options[2], inline=True),
            render_markdown(shuffled_options[3], inline=True),
            new_correct_letter,
            render_markdown(card.get("explanation", "")),
            card.get("card_type", "Concept"),
            topic,
            title,
            difficulty,
            tags_str,
        ],
        tags=unique_tags,
        guid=genanki.guid_for(card.get("front", ""), deck_name),
    )


def create_note_for_card(
    card: dict,
    topic_data: dict,
    models: tuple,
    deck_name: str,
    source: str | None = None,
    subject: str | None = None,
) -> genanki.Note | None:
    """
    Creates a genanki Note for a single card dictionary, selecting the appropriate
    model based on card_format. Returns None for unsupported formats (with a warning).
    """
    basic_model, cloze_model, mcq_model = models

    card_format = card.get("card_format", "Basic")

    # Extract topic-level metadata
    topic = topic_data.get("topic", "Default Topic")
    title = topic_data.get("title", "Default Title")
    difficulty = topic_data.get("difficulty", "Unknown")

    # Build card and taxonomy tags
    unique_tags = build_tags(card, topic_data, source=source, subject=subject)
    tags_str = " ".join(unique_tags)

    if card_format == "Basic":
        return _create_basic_note(
            card,
            topic,
            title,
            difficulty,
            tags_str,
            unique_tags,
            deck_name,
            basic_model,
        )
    if card_format == "Cloze":
        return _create_cloze_note(
            card,
            topic,
            title,
            difficulty,
            tags_str,
            unique_tags,
            deck_name,
            cloze_model,
        )
    if card_format == "MCQ":
        return _create_mcq_note(
            card, topic, title, difficulty, tags_str, unique_tags, deck_name, mcq_model
        )

    print(
        f"Warning: Skipped card with unsupported format '{card_format}' "
        f"(front snippet: '{card.get('front', '')[:30]}...').",
        file=sys.stderr,
    )
    return None
