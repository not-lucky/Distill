"""Service for merging archived JSON files."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """Result of a merge operation."""

    success: bool
    merged_count: int
    output_path: Optional[Path] = None
    error: Optional[str] = None


class MergeService:
    """Service for merging archived JSON files for a subject."""

    def __init__(self, archival_dir: Path, timestamp_format: str = "%Y%m%dT%H%M%S"):
        """
        Initialize MergeService.

        Args:
            archival_dir: Base directory containing subject subdirectories.
            timestamp_format: Format for output filename timestamp.
        """
        self.archival_dir = archival_dir
        self.timestamp_format = timestamp_format

    def merge_subject(self, subject: str, dry_run: bool = False) -> MergeResult:
        """
        Merge all JSON files for a given subject.

        Args:
            subject: Subject name (e.g., "cs", "leetcode", "physics").
            dry_run: If True, return what would be done without writing.

        Returns:
            MergeResult with outcome details.
        """
        source_directory = self.archival_dir / subject

        if not source_directory.exists():
            return MergeResult(
                success=False,
                merged_count=0,
                error=f"Directory '{source_directory}' does not exist.",
            )

        json_files = list(source_directory.glob("*.json"))
        if not json_files:
            return MergeResult(
                success=False,
                merged_count=0,
                error=f"No JSON files found in '{source_directory}'.",
            )

        logger.info(f"Found {len(json_files)} JSON files in '{source_directory}'.")

        merged_data: List = []
        for json_path in json_files:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        merged_data.append(data)
                    else:
                        logger.warning(
                            f"Skipping '{json_path.name}' - expected object, got {type(data).__name__}"
                        )
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse '{json_path.name}': {e}")
            except Exception as e:
                logger.error(f"Error processing '{json_path.name}': {e}")

        if not merged_data:
            return MergeResult(
                success=False,
                merged_count=0,
                error="No valid data found to merge.",
            )

        timestamp = datetime.now().strftime(self.timestamp_format)
        output_filename = f"{subject}_anki_deck_{timestamp}.json"
        output_path = Path(output_filename)

        if dry_run:
            return MergeResult(
                success=True,
                merged_count=len(merged_data),
                output_path=output_path,
            )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)

        return MergeResult(
            success=True,
            merged_count=len(merged_data),
            output_path=output_path.absolute(),
        )
