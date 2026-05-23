"""Pytest configuration.

Adds the repository root to ``sys.path`` so test modules can import
``src.compile`` directly without any per-file path hacking.
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
