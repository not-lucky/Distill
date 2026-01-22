"""Unit test fixtures.

Unit tests are fast, isolated tests that test a single component in isolation.
They should not touch external services or databases.
"""

import pytest


def pytest_collection_modifyitems(items):
    """Automatically add 'unit' marker to all tests in the unit directory."""
    for item in items:
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def isolated_function():
    """Fixture for testing pure functions in isolation."""
    def _wrap(func, *args, **kwargs):
        return func(*args, **kwargs)
    return _wrap
