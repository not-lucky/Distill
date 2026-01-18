"""Mode detection and deck prefix utilities."""

from pathlib import Path
from typing import Tuple


# Valid generation modes
VALID_MODES = frozenset([
    "cs", "physics", "leetcode",
    "cs_mcq", "physics_mcq", "leetcode_mcq",
    "mcq",
])

# Deck prefix mappings: subject -> (standard_prefix, mcq_prefix)
DECK_PREFIXES = {
    "cs": ("CS", "CS_MCQ"),
    "physics": ("Physics", "Physics_MCQ"),
    "leetcode": ("LeetCode", "LeetCode_MCQ"),
}


def detect_mode_from_filename(filename: str) -> str:
    """
    Auto-detect generation mode from JSON filename.

    Args:
        filename: Path or filename to analyze.

    Returns:
        Detected mode string (e.g., "leetcode", "cs_mcq").
    """
    stem = Path(filename).stem.lower()

    # Try MCQ variants first (more specific)
    for mode in ["cs_mcq", "physics_mcq", "leetcode_mcq"]:
        if stem.startswith(mode):
            return mode

    # Then base modes
    for mode in ["cs", "physics", "leetcode"]:
        if stem.startswith(mode):
            return mode

    if "mcq" in stem:
        return "mcq"

    return "leetcode"


def parse_mode(mode: str) -> Tuple[str, bool]:
    """
    Parse a mode string into subject and MCQ flag.

    Args:
        mode: Mode string (e.g., "cs_mcq", "leetcode").

    Returns:
        Tuple of (subject, is_mcq).
    """
    if mode == "mcq":
        return "leetcode", True

    if mode.endswith("_mcq"):
        return mode.replace("_mcq", ""), True

    return mode, False


def get_deck_prefix(mode: str) -> str:
    """
    Get the Anki deck prefix for a given mode.

    Args:
        mode: Mode string (e.g., "cs_mcq", "leetcode").

    Returns:
        Deck prefix string (e.g., "CS_MCQ", "LeetCode").
    """
    subject, is_mcq = parse_mode(mode)
    prefix, prefix_mcq = DECK_PREFIXES.get(subject, ("LeetCode", "LeetCode_MCQ"))
    return prefix_mcq if is_mcq else prefix


def is_valid_mode(mode: str) -> bool:
    """Check if a mode string is valid."""
    return mode in VALID_MODES
