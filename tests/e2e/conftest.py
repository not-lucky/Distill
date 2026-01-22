"""End-to-end test fixtures.

E2E tests verify complete user workflows from CLI invocation to output.
They test the entire system as a user would interact with it.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from src.database import DatabaseManager


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def e2e_workspace(tmp_path):
    """Create a complete workspace for e2e tests.

    Sets up:
    - Output directory
    - Archival directory
    - Database
    """
    workspace = tmp_path / "e2e_workspace"
    workspace.mkdir()

    # Create subdirectories
    (workspace / "output").mkdir()
    (workspace / "archival").mkdir()
    (workspace / "archival" / "leetcode").mkdir()
    (workspace / "archival" / "cs").mkdir()
    (workspace / "archival" / "physics").mkdir()

    return workspace


@pytest.fixture
def e2e_db(e2e_workspace):
    """Create a database for e2e tests."""
    db_path = e2e_workspace / "e2e_test.db"
    manager = DatabaseManager()
    manager.initialize(db_path)
    DatabaseManager.set_default(manager)
    yield manager
    DatabaseManager.reset_default()
