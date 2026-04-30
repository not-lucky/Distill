"""Document processing utilities for LLM2Deck ingest command."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Iterator, Tuple


# Supported document extensions
SUPPORTED_EXTENSIONS = {".md", ".txt", ".rst", ".html", ".htm"}


@dataclass
class DocumentInfo:
    """Information about a document to be processed."""

    file_path: Path
    title: str  # Derived from filename
    deck_name: str  # Top-level directory name (main deck)
    subdeck_path: List[str]  # Path components for nested subdecks
    content: str  # Document content

    @property
    def full_deck_path(self) -> str:
        """Get the full Anki deck path (e.g., 'ReactTutorial::Hooks::UseState')."""
        parts = [self.deck_name] + self.subdeck_path + [self.title]
        return "::".join(parts)

    @property
    def topic_path(self) -> str:
        """Get the topic path for prompts (e.g., 'React Tutorial > Hooks > useState')."""
        parts = [self.deck_name] + self.subdeck_path + [self.title]
        # Convert to more readable format
        readable_parts = [self._humanize(p) for p in parts]
        return " > ".join(readable_parts)

    @staticmethod
    def _humanize(name: str) -> str:
        """Convert filename/dirname to human-readable format."""
        # Remove extension if present
        name = Path(name).stem if "." in name else name
        # Replace hyphens and underscores with spaces
        name = name.replace("-", " ").replace("_", " ")
        # Title case
        return name.title()

    @property
    def relative_path(self) -> str:
        """Get relative path from the source directory."""
        parts = self.subdeck_path + [self.file_path.name]
        return "/".join(parts)


def _filename_to_title(filename: str) -> str:
    """Convert a filename to a readable title.

    Examples:
        'jsx-intro.md' -> 'JsxIntro'
        'use_state.md' -> 'UseState'
        '01-getting-started.md' -> 'GettingStarted'
    """
    stem = Path(filename).stem

    # Remove leading numbers (e.g., '01-', '1_')
    stem = re.sub(r"^\d+[-_]?", "", stem)

    # Split on hyphens and underscores
    parts = re.split(r"[-_]+", stem)

    # Title case each part and join
    return "".join(word.title() for word in parts if word)


def _dirname_to_deck_name(dirname: str) -> str:
    """Convert a directory name to a deck name.

    Examples:
        'react-tutorial' -> 'ReactTutorial'
        'my_awesome_deck' -> 'MyAwesomeDeck'
    """
    # Split on hyphens and underscores
    parts = re.split(r"[-_]+", dirname)

    # Title case each part and join
    return "".join(word.title() for word in parts if word)


def discover_documents(
    source_dir: Path,
    extensions: Optional[set] = None,
) -> Iterator[DocumentInfo]:
    """
    Discover all documents in a directory structure.

    Directory structure maps to Anki deck hierarchy:
        source_dir/           -> Main deck name
        ├── subdir1/          -> Sub-deck
        │   ├── file1.md      -> Innermost sub-deck (cards for this file)
        │   └── file2.md
        └── subdir2/
            └── nested/
                └── file3.md  -> Deeply nested sub-deck

    Args:
        source_dir: Root directory to scan
        extensions: Set of file extensions to include (default: SUPPORTED_EXTENSIONS)

    Yields:
        DocumentInfo for each discovered document
    """
    if extensions is None:
        extensions = SUPPORTED_EXTENSIONS

    source_dir = Path(source_dir).resolve()

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    if not source_dir.is_dir():
        raise ValueError(f"Source path is not a directory: {source_dir}")

    # The source directory name becomes the main deck name
    deck_name = _dirname_to_deck_name(source_dir.name)

    # Walk the directory tree
    for file_path in sorted(source_dir.rglob("*")):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in extensions:
            continue

        # Skip hidden files
        if file_path.name.startswith("."):
            continue

        # Calculate subdeck path (directories between source_dir and file)
        relative = file_path.relative_to(source_dir)
        subdeck_parts = [
            _dirname_to_deck_name(p) for p in relative.parent.parts
        ]

        # Read content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                content = file_path.read_text(encoding="latin-1")
            except Exception:
                continue  # Skip files we can't read

        # Skip empty files
        if not content.strip():
            continue

        yield DocumentInfo(
            file_path=file_path,
            title=_filename_to_title(file_path.name),
            deck_name=deck_name,
            subdeck_path=subdeck_parts,
            content=content,
        )


def get_document_count(source_dir: Path, extensions: Optional[set] = None) -> int:
    """Count the number of documents in a directory structure."""
    return sum(1 for _ in discover_documents(source_dir, extensions))


def preview_deck_structure(
    source_dir: Path,
    extensions: Optional[set] = None,
    max_items: int = 20,
) -> List[Tuple[str, str]]:
    """
    Preview the deck structure that would be created.

    Args:
        source_dir: Root directory to scan
        extensions: Set of file extensions to include
        max_items: Maximum number of items to return

    Returns:
        List of (deck_path, relative_file_path) tuples
    """
    items = []
    for i, doc in enumerate(discover_documents(source_dir, extensions)):
        if i >= max_items:
            break
        items.append((doc.full_deck_path, doc.relative_path))
    return items
