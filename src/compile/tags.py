"""
Tag construction for LLM2Deck notes.

Builds the set of Anki tags for a note by combining:
- topic::<normalized_topic_name>
- difficulty::<normalized_difficulty_level>
- type::<normalized_card_type>
- source::<normalized_source_file_name>
- subject::<normalized_folder_path>
- card-level tags emitted by the LLM
"""

from .html import normalize_tag


def build_tags(
    card: dict, topic_data: dict, source: str | None = None, subject: str | None = None
) -> list[str]:
    """
    Builds the set of tags for the note including card-level tags and hierarchical taxonomy tags.
    """
    # Safe handling if card or topic_data are not dicts
    if not isinstance(card, dict):
        card = {}
    if not isinstance(topic_data, dict):
        topic_data = {}

    tags_list: list[str] = []

    # 1. Topic Tag
    topic = topic_data.get("topic", "DefaultTopic")
    tags_list.append(f"topic::{normalize_tag(topic)}")

    # 2. Difficulty Tag
    difficulty = topic_data.get("difficulty", "Unknown")
    tags_list.append(f"difficulty::{normalize_tag(difficulty)}")

    # 3. Type Tag
    card_type = card.get("card_type", "Concept")
    tags_list.append(f"type::{normalize_tag(card_type)}")

    # 4. Source Tag
    if source:
        # Use provided source name
        tags_list.append(f"source::{normalize_tag(source)}")
    else:
        # Fallback to title
        title = topic_data.get("title", "DefaultTitle")
        tags_list.append(f"source::{normalize_tag(title)}")

    # 5. Subject Tag
    if subject:
        tags_list.append(f"subject::{normalize_tag(subject)}")

    # 6. Card-level tags
    card_tags = card.get("tags", [])
    if isinstance(card_tags, list):
        for tag in card_tags:
            if tag:
                tags_list.append(normalize_tag(str(tag)))

    # Dedup tags list while preserving relative order
    unique_tags: list[str] = []
    for tag in tags_list:
        if tag and tag not in unique_tags:
            unique_tags.append(tag)

    return unique_tags
