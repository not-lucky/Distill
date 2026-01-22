"""End-to-end test fixtures.

E2E tests verify complete user workflows from CLI invocation to output.
They test the entire system as a user would interact with it.
"""

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def e2e_workspace(workspace_factory):
    """Create a complete workspace for e2e tests.

    Sets up:
    - Output directory
    - Archival directory with subject subdirectories
    """
    return workspace_factory(name="e2e_workspace", include_output=True)


@pytest.fixture
def e2e_db(db_factory):
    """Create a database for e2e tests."""
    return db_factory("e2e_test.db")
