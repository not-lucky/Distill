import json
import re
import datetime
from pathlib import Path
from typing import Dict, List, Any

import logging

logger = logging.getLogger(__name__)


def unescape_newlines(obj: Any) -> Any:
    """Recursively unescape literal \\n in strings."""
    if isinstance(obj, str):
        return obj.replace('\\n', '\n')
    elif isinstance(obj, list):
        return [unescape_newlines(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: unescape_newlines(value) for key, value in obj.items()}
    return obj


def sanitize_filename(original_name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove special characters and spaces
    cleaned_name = re.sub(r"[^\w\s-]", "", original_name).strip().lower()
    return re.sub(r"[-\s]+", "_", cleaned_name)


def strip_json_block(content: str) -> str:
    """
    Strip markdown JSON code block markers if present.

    Handles formats like:
    - ```json ... ```
    - ``` ... ```

    Args:
        content: String that may contain markdown code block markers.

    Returns:
        Content with code block markers removed and whitespace trimmed.
    """
    if content.startswith("```json"):
        content = content[7:]  # Remove ```json
    elif content.startswith("```"):
        content = content[3:]  # Remove ```
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def save_final_deck(
    all_problems: List[Dict], filename_prefix: str = "leetcode_anki_deck"
):
    current_timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    output_filename = f"{filename_prefix}_{current_timestamp}.json"

    with open(output_filename, "w", encoding="utf-8") as output_file:
        json.dump(all_problems, output_file, indent=2, ensure_ascii=False)
    logger.info(f"Final deck saved to {output_filename}")
