"""Integration test fixtures.

Integration tests verify that multiple components work together correctly.
They may touch databases but should not make external API calls.
"""

import pytest
from pathlib import Path


@pytest.fixture
def integration_db(db_factory):
    """Create a file-based database for integration tests.

    Unlike unit tests which use in-memory databases, integration tests
    use a file-based database to better simulate production conditions.
    """
    return db_factory("integration_test.db")


@pytest.fixture
def integration_output_dir(tmp_path):
    """Create a temporary output directory for integration test artifacts."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
