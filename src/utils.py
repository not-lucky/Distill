import json
import re
import datetime
from pathlib import Path
from typing import Dict, List

import logging

logger = logging.getLogger(__name__)


def sanitize_filename(original_name: str) -> str:
    # Remove special characters and spaces
    cleaned_name = re.sub(r"[^\w\s-]", "", original_name).strip().lower()
    return re.sub(r"[-\s]+", "_", cleaned_name)


def save_final_deck(
    all_problems: List[Dict], filename_prefix: str = "leetcode_anki_deck"
):
    current_timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    output_filename = f"{filename_prefix}_{current_timestamp}.json"

    with open(output_filename, "w", encoding="utf-8") as output_file:
        json.dump(all_problems, output_file, indent=2, ensure_ascii=False)
    logger.info(f"Final deck saved to {output_filename}")
