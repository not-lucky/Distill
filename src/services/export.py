"""Service for exporting JSON cards to Markdown."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of an export operation."""

    success: bool
    exported_count: int
    error: Optional[str] = None


class ExportService:
    """Service for exporting JSON cards to Markdown format."""

    def __init__(self, source_dir: Path, target_dir: Path):
        """
        Initialize ExportService.

        Args:
            source_dir: Directory containing JSON files.
            target_dir: Directory for Markdown output.
        """
        self.source_dir = source_dir
        self.target_dir = target_dir

    def export_to_markdown(self, dry_run: bool = False) -> ExportResult:
        """
        Export all JSON files to Markdown format.

        Args:
            dry_run: If True, return what would be done without writing.

        Returns:
            ExportResult with outcome details.
        """
        if not self.source_dir.exists():
            return ExportResult(
                success=False,
                exported_count=0,
                error=f"Source directory '{self.source_dir}' does not exist.",
            )

        json_files = list(self.source_dir.rglob("*.json"))
        if not json_files:
            return ExportResult(
                success=False,
                exported_count=0,
                error="No JSON files found.",
            )

        if dry_run:
            return ExportResult(
                success=True,
                exported_count=len(json_files),
            )

        self.target_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {self.target_dir.resolve()}")

        exported_count = 0
        for json_path in json_files:
            try:
                self._export_file(json_path)
                exported_count += 1
            except Exception as e:
                logger.error(f"Error processing {json_path.name}: {e}")

        return ExportResult(
            success=True,
            exported_count=exported_count,
        )

    def _export_file(self, json_path: Path) -> None:
        """Export a single JSON file to Markdown."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        md_filename = json_path.stem + ".md"
        md_path = self.target_dir / md_filename

        with open(md_path, "w", encoding="utf-8") as f:
            title = json_path.stem.replace("_", " ").title()
            f.write(f"# {title}\n\n")

            if isinstance(data, dict) and "cards" in data:
                data = data["cards"]

            if isinstance(data, list):
                for i, card in enumerate(data, 1):
                    f.write(f"## Card {i}\n")
                    f.write(f"**Type**: {card.get('card_type', 'N/A')}  \n")
                    tags = card.get("tags", [])
                    tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
                    f.write(f"**Tags**: {tags_str}\n\n")
                    f.write("### Front\n")
                    f.write(f"{card.get('front', '')}\n\n")
                    f.write("### Back\n")
                    f.write(f"{card.get('back', '')}\n\n")
                    f.write("---\n\n")

        logger.info(f"Converted: {json_path.name} -> {md_filename}")
