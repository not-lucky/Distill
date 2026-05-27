"""
Deterministic ID generation for Distill.

Anki requires stable, positive 64-bit integer IDs for models and decks so that
notes can be updated in place across runs. We derive them from MD5 hashes of
human-readable names (e.g., "Distill Basic Model") and resolve collisions by
incrementing until a free slot is found.
"""

import hashlib
import sys

# Module-level ID collision tracking registry.
generated_ids: dict[str, int] = {}
used_ids: set[int] = set()


def reset_id_registry() -> None:
    """Resets the ID registry. Helpful for unit tests."""
    global generated_ids, used_ids
    generated_ids.clear()
    used_ids.clear()


def generate_id(name: str) -> int:
    """
    Generates a deterministic 52-bit positive integer by hashing the input name
    using MD5, taking the first 13 hex characters, and parsing as base-16.
    If the name has already been registered, returns the same ID.
    Resolves hash value collisions by incrementing by 1 and logging a warning.
    """
    global generated_ids, used_ids
    # Coerce to string to avoid errors on None or non-string inputs
    name_str = str(name)
    if name_str in generated_ids:
        return generated_ids[name_str]

    h = hashlib.md5(name_str.encode("utf-8")).hexdigest()
    # First 13 hex characters = 52 bits. Fits safely under JS 2^53 - 1 ceiling
    # and satisfies Anki's requirements for positive 64-bit integer IDs.
    val = int(h[:13], 16)

    # Collision resolution for different names hashing to the same value
    if val in used_ids:
        orig_val = val
        while val in used_ids:
            val += 1
        print(
            f"Warning: ID collision detected for '{name_str}' (computed: {orig_val}). "
            f"Incremented to {val}.",
            file=sys.stderr,
        )

    used_ids.add(val)
    generated_ids[name_str] = val
    return val
