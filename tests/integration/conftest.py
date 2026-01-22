"""Integration test fixtures.

Integration tests verify that multiple components work together correctly.
They may touch databases but should not make external API calls.
"""

import pytest
from pathlib import Path

from src.database import DatabaseManager


@pytest.fixture
def integration_db(tmp_path):
    """Create a file-based database for integration tests.

    Unlike unit tests which use in-memory databases, integration tests
    use a file-based database to better simulate production conditions.
    """
    db_path = tmp_path / "integration_test.db"
    manager = DatabaseManager()
    manager.initialize(db_path)
    DatabaseManager.set_default(manager)
    yield manager
    DatabaseManager.reset_default()


@pytest.fixture
def integration_output_dir(tmp_path):
    """Create a temporary output directory for integration test artifacts."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
