"""Unit test fixtures.

Unit tests are fast, isolated tests that test a single component in isolation.
They should not touch external services or databases.
"""

import pytest


@pytest.fixture
def isolated_function():
    """Fixture for testing pure functions in isolation."""
    def _wrap(func, *args, **kwargs):
        return func(*args, **kwargs)
    return _wrap
