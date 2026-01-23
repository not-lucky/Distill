#!/usr/bin/env python3
"""Calculate and display test metrics for LLM2Deck."""

import json
import subprocess
import sys
from pathlib import Path


def count_python_lines(directory: str) -> int:
    """Count total lines in Python files within a directory."""
    total = 0
    for py_file in Path(directory).rglob("*.py"):
        try:
            total += len(py_file.read_text().splitlines())
        except Exception:
            continue
    return total


def count_tests() -> int:
    """Count total number of tests using pytest --collect-only."""
    result = subprocess.run(
        ["uv", "run", "pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
    )
    # Count lines that contain test items (format: file::class::test or file::test)
    return len([line for line in result.stdout.splitlines() if "::test_" in line])


def main() -> None:
    """Calculate and print test metrics."""
    src_lines = count_python_lines("src")
    test_lines = count_python_lines("tests")
    ratio = test_lines / src_lines if src_lines > 0 else 0
    test_count = count_tests()

    print(f"Source lines:  {src_lines:,}")
    print(f"Test lines:    {test_lines:,}")
    print(f"Ratio:         {ratio:.2f}:1")
    print(f"Test count:    {test_count:,}")
    print()

    # Output JSON for tracking/CI
    metrics = {
        "src_lines": src_lines,
        "test_lines": test_lines,
        "ratio": round(ratio, 2),
        "test_count": test_count,
    }

    if "--json" in sys.argv:
        print(json.dumps(metrics, indent=2))
    else:
        print(f"JSON: {json.dumps(metrics)}")


if __name__ == "__main__":
    main()
