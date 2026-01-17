"""Shared pytest fixtures for LLM2Deck tests."""

import itertools
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any


# ============================================================================
# Mock API Keys
# ============================================================================

@pytest.fixture
def mock_cerebras_keys():
    """Provide mock API keys for testing."""
    return itertools.cycle(["test_key_1", "test_key_2"])


@pytest.fixture
def real_cerebras_keys():
    """Load real Cerebras API keys for integration tests."""
    import asyncio
    from src.config.keys import load_keys

    async def _load():
        return await load_keys("cerebras")

    return asyncio.get_event_loop().run_until_complete(_load())


# ============================================================================
# Provider Fixtures
# ============================================================================

@pytest.fixture
def cerebras_provider(mock_cerebras_keys):
    """Create a CerebrasProvider with mocked keys."""
    from src.providers.cerebras import CerebrasProvider
    return CerebrasProvider(api_keys=mock_cerebras_keys, model="gpt-oss-120b")


@pytest.fixture
def mock_provider():
    """Create a fully mocked LLM provider."""
    provider = MagicMock()
    provider.name = "mock_provider"
    provider.model = "mock-model"
    provider.generate_initial_cards = AsyncMock(return_value='{"cards": []}')
    provider.combine_cards = AsyncMock(return_value={"cards": []})
    return provider


# ============================================================================
# Subject Config Fixtures
# ============================================================================

@pytest.fixture
def leetcode_config():
    """Get SubjectConfig for LeetCode standard mode."""
    from src.config.subjects import SubjectRegistry
    return SubjectRegistry.get_config("leetcode", is_multiple_choice=False)


@pytest.fixture
def cs_mcq_config():
    """Get SubjectConfig for CS MCQ mode."""
    from src.config.subjects import SubjectRegistry
    return SubjectRegistry.get_config("cs", is_multiple_choice=True)


@pytest.fixture
def single_question_config(leetcode_config):
    """Return a SubjectConfig with only 1 question for testing."""
    # Override target_questions to have only 1 question
    from dataclasses import replace
    return replace(
        leetcode_config,
        target_questions={"Stacks": ["Min Stack"]}
    )


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_card_json() -> str:
    """Sample valid card JSON response."""
    import json
    return json.dumps({
        "title": "Min Stack",
        "topic": "Stacks",
        "difficulty": "Medium",
        "cards": [
            {
                "card_type": "Concept",
                "front": "What is a Min Stack?",
                "back": "A stack that supports push, pop, and retrieving minimum in O(1).",
                "tags": ["stack", "design"]
            }
        ]
    })


@pytest.fixture
def sample_card_dict() -> Dict[str, Any]:
    """Sample valid card dictionary."""
    return {
        "title": "Min Stack",
        "topic": "Stacks",
        "difficulty": "Medium",
        "cards": [
            {
                "card_type": "Concept",
                "front": "What is a Min Stack?",
                "back": "A stack that supports push, pop, and retrieving minimum in O(1).",
                "tags": ["stack", "design"]
            }
        ]
    }


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_database(tmp_path):
    """Create a temporary database for testing."""
    from src.database import init_database
    db_path = tmp_path / "test_llm2deck.db"
    init_database(str(db_path))
    return str(db_path)
