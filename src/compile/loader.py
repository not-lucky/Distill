"""
Input loading and normalization for the compile stage.

Accepts either a path to a JSON file or an in-memory data structure and returns
a list of topic dictionaries plus the resolved source name. The single-topic
shape is normalized into the multi-topic shape so the rest of the compiler
can iterate uniformly.
"""

import json
import os


def load_json_data(json_data, source: str | None = None) -> tuple[list, str | None]:
    """
    Loads and normalizes JSON input into a list of topic dictionaries.
    Handles both file paths and in-memory data structures.
    Returns: (topics_list, resolved_source_name)
    """
    if isinstance(json_data, str):
        with open(json_data, "r", encoding="utf-8") as f:
            data = json.load(f)
        # If source is not explicitly specified, derive it from the input filename
        if not source:
            base = os.path.basename(json_data)
            source = os.path.splitext(base)[0]
    else:
        data = json_data

    # Wrap in a list if it is a single dictionary (object) to normalize processing
    # of both single-topic and multi-topic merged JSON data structures.
    topics = data if isinstance(data, list) else [data]
    return topics, source


def resolve_deck_name(topics: list, deck_name: str | None = None) -> str:
    """
    Determines the deck name. If not explicitly specified by CLI arguments,
    defaults to the topic name for single-topic runs, or a generic name for multi-topic runs.
    """
    if deck_name:
        return deck_name
    if len(topics) == 1 and isinstance(topics[0], dict):
        return topics[0].get("topic", "LLM2Deck Compiled")
    return "LLM2Deck Compiled"
