import json
import re
import datetime
from pathlib import Path
from typing import Dict, List

from src.config import ARCHIVAL_DIR

def sanitize_filename(name: str) -> str:
    # Remove special characters and spaces
    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
    return re.sub(r'[-\s]+', '_', name)

def save_archival(question: str, data: Dict):
    ARCHIVAL_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    sanitized_name = sanitize_filename(question)
    filename = f"{timestamp}_{sanitized_name}.json"
    filepath = ARCHIVAL_DIR / filename
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [Save] Archived to {filepath}")

def save_final_deck(all_problems: List[Dict], filename_prefix: str = "leetcode_anki_deck"):
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(all_problems, f, indent=2)
    print(f"  [Save] Final deck saved to {filename}")
