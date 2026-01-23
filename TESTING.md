# Testing Guide

This document describes the testing infrastructure, patterns, and practices for LLM2Deck.

## Overview

LLM2Deck targets high testing rigor:
- **5:1** test-to-code ratio for core modules (providers, generator, orchestrator)
- **2:1** ratio for peripheral modules (anki, services, config)
- **Current metrics**: ~4.0:1 overall ratio, 1425+ tests, 87% coverage

Check current metrics:
```bash
uv run python scripts/test-metrics.py
```

## Test Organization

Tests are organized into three categories:

```
tests/
├── conftest.py          # Global fixtures and factories
├── fixtures/            # JSON fixture files
│   └── responses.json   # Mock LLM responses
├── unit/                # Fast, isolated tests
│   ├── conftest.py      # Unit-specific fixtures + auto-marker
│   ├── anki/            # Tests for src/anki/
│   ├── config/          # Tests for src/config/
│   │   └── test_keys.py # API key loading tests
│   ├── providers/       # Tests for src/providers/
│   │   └── test_gemini_factory.py  # Gemini factory tests
│   ├── services/        # Tests for src/services/
│   ├── test_cli.py      # CLI tests (including handle_cache)
│   ├── test_setup.py    # Provider initialization tests
│   ├── test_queries.py  # Database query function tests
│   └── test_*.py        # Tests for other src/*.py modules
├── integration/         # Component interaction tests
│   └── conftest.py
└── e2e/                 # End-to-end CLI tests
    └── conftest.py
```

### Test Types

| Type | Location | Purpose | Speed |
|------|----------|---------|-------|
| Unit | `tests/unit/` | Test single components in isolation | Fast (<1s) |
| Integration | `tests/integration/` | Test component interactions | Medium |
| E2E | `tests/e2e/` | Test full CLI workflows | Slow |

## Running Tests

### By Type

```bash
# All tests
uv run pytest

# Unit tests only (fast)
uv run pytest tests/unit/ -m unit

# Integration tests
uv run pytest tests/integration/ -m integration

# E2E tests
uv run pytest tests/e2e/ -m e2e

# Exclude slow tests
uv run pytest -m "not slow"
```

### Parallel Execution

```bash
# Run unit tests in parallel (recommended for CI)
uv run pytest tests/unit/ -n auto

# Specific number of workers
uv run pytest tests/unit/ -n 4
```

### With Coverage

```bash
# Generate coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term

# Coverage for specific module
uv run pytest tests/unit/providers/ --cov=src/providers
```

### Mutation Testing

```bash
# Run mutation testing (slow, comprehensive)
uv run mutmut run --paths-to-mutate=src/

# Show surviving mutants
uv run mutmut results

# Generate HTML report
uv run mutmut html
```

## Test Patterns

### Naming Convention (BDD-style)

Use descriptive test names that explain the behavior:

```python
def test_generate_returns_cards_when_provider_succeeds():
    """
    Given a provider that returns valid JSON
    When generate_initial_cards is called
    Then it should return parsed Card objects
    """
```

Pattern: `test_<action>_<result>_when_<condition>`

### Parametrization

Use `@pytest.mark.parametrize` for testing variations:

```python
@pytest.mark.parametrize("status,expected", [
    (500, ProviderError),
    (429, RateLimitError),
    (401, AuthenticationError),
])
def test_provider_handles_error_status(status, expected):
    # Test each error status maps to correct exception
    ...
```

### Fixtures

Use the factory fixtures defined in `tests/conftest.py`:

```python
def test_card_creation(card_factory):
    card = card_factory(front="What is X?", back="Y")
    assert card["front"] == "What is X?"

def test_llm_response_parsing(mock_llm_response):
    response = mock_llm_response(content='{"cards": []}')
    assert response["choices"][0]["message"]["content"] == '{"cards": []}'

def test_database_operations(memory_db):
    # memory_db is a fresh in-memory database
    ...
```

### Available Fixtures

| Fixture | Purpose |
|---------|---------|
| `mock_llm_response` | Factory for LLM API responses |
| `mock_error_response` | Factory for error responses |
| `card_factory` | Factory for card dictionaries |
| `memory_db` | In-memory SQLite database |
| `sample_config` | Default test configuration |
| `mock_provider` | Mock LLM provider instance |
| `mock_openai_client` | Mocked AsyncOpenAI client |
| `temp_prompts_dir` | Temporary prompts directory |

## Async Testing

### Basic Async Tests

Tests are automatically detected as async with `asyncio_mode = "auto"`:

```python
async def test_parallel_generation():
    """Given multiple providers, when generating, they run in parallel."""
    results = await generate_cards_async(providers)
    assert len(results) == len(providers)
```

### Mocking Async Functions

```python
from unittest.mock import AsyncMock

async def test_provider_calls_api(mock_openai_client):
    provider = CerebrasProvider(api_keys=iter(["key"]), model="test")

    # mock_openai_client fixture already patches AsyncOpenAI
    result = await provider.generate_initial_cards("test", {})

    mock_openai_client.return_value.chat.completions.create.assert_called_once()
```

### Testing Concurrent Operations

```python
import asyncio

async def test_concurrent_requests_respect_limit():
    runner = ConcurrentTaskRunner(max_concurrent=2)
    start_times = []

    async def track_task():
        start_times.append(asyncio.get_event_loop().time())
        await asyncio.sleep(0.1)

    await runner.run_all([track_task for _ in range(4)])

    # Verify only 2 ran concurrently
    assert max(start_times) - min(start_times) >= 0.1
```

## Markers

Tests are automatically marked based on directory:

- `tests/unit/` → `@pytest.mark.unit`
- `tests/integration/` → `@pytest.mark.integration`
- `tests/e2e/` → `@pytest.mark.e2e`

Additional markers:
- `@pytest.mark.slow` - Tests taking >1 second
- `@pytest.mark.hypothesis` - Property-based tests

## Test Data

### Using Fixture Files

```python
import json
from pathlib import Path

def test_with_fixture_data():
    fixtures = Path(__file__).parent.parent / "fixtures" / "responses.json"
    data = json.loads(fixtures.read_text())

    success_response = data["success"]["leetcode_standard"]
    error_response = data["error"]["rate_limit"]
```

### Mock Provider Responses

```python
def test_with_mock_provider(mock_provider_with_responses):
    provider = mock_provider_with_responses(
        responses={"initial": '{"cards": []}'},
        fail_combine=True
    )

    result = await provider.generate_initial_cards("test", {})
    assert result == '{"cards": []}'
```

## Writing Good Tests

1. **One assertion per test** (when practical)
2. **Arrange-Act-Assert** structure
3. **No test interdependencies** - each test is isolated
4. **Mock external services** - never make real API calls in unit tests
5. **Use fixtures** - avoid duplicating setup code
6. **Test edge cases** - empty inputs, errors, boundary conditions

## CI Integration

Tests run automatically via GitHub Actions on push and PR:

```yaml
# .github/workflows/test.yml
jobs:
  unit-tests:     # Python 3.11 & 3.12 matrix, with coverage
  integration-tests:
  e2e-tests:
  type-check:     # ty type checker
  mutation-testing:  # mutmut (push only)
```

### Running CI Locally

```bash
# Full CI check
uv run pytest tests/unit/ --cov=src --cov-report=term && \
uv run pytest tests/integration/ -x && \
ty check src/

# Generate coverage HTML report
uv run pytest --cov=src --cov-report=html && open htmlcov/index.html

# Run mutation testing (slow)
uv run mutmut run --paths-to-mutate=src/

# Check test metrics
uv run python scripts/test-metrics.py

# Run tests in random order (verify isolation)
uv run pytest --random-order
```

