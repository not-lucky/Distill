"""Shared fixtures and mock providers for LLM2Deck tests."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database import Base, DatabaseManager
from src.providers.base import LLMProvider


# ============================================================================
# Sample Test Data
# ============================================================================

SAMPLE_CARD_RESPONSE = json.dumps({
    "title": "Binary Search",
    "topic": "Arrays",
    "difficulty": "Medium",
    "cards": [
        {
            "card_type": "Algorithm",
            "tags": ["BinarySearch", "Arrays"],
            "front": "What is binary search?",
            "back": "A search algorithm that finds the position of a target value within a sorted array."
        },
        {
            "card_type": "TimeComplexity",
            "tags": ["Complexity", "BigO"],
            "front": "What is the time complexity of binary search?",
            "back": "O(log n) where n is the number of elements in the array."
        }
    ]
})

SAMPLE_CARD_RESPONSE_DICT = json.loads(SAMPLE_CARD_RESPONSE)

SAMPLE_MCQ_RESPONSE = json.dumps({
    "title": "Binary Search MCQ",
    "topic": "Algorithms",
    "difficulty": "Medium",
    "cards": [
        {
            "card_type": "Concept",
            "tags": ["BinarySearch"],
            "question": "What is the time complexity of binary search?",
            "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
            "correct_answer": "B",
            "explanation": "Binary search divides the search space in half at each step."
        }
    ]
})

SAMPLE_MCQ_RESPONSE_DICT = json.loads(SAMPLE_MCQ_RESPONSE)

SAMPLE_CS_RESPONSE = json.dumps({
    "title": "Process vs Thread",
    "topic": "Operating Systems",
    "difficulty": "Intermediate",
    "cards": [
        {
            "card_type": "Concept",
            "tags": ["OS", "Concurrency"],
            "front": "What is the difference between a process and a thread?",
            "back": "A process is an independent execution unit with its own memory space. A thread is a lightweight unit of execution within a process that shares memory."
        }
    ]
})

SAMPLE_EMPTY_RESPONSE = json.dumps({
    "title": "Empty",
    "topic": "Test",
    "difficulty": "Easy",
    "cards": []
})

SAMPLE_QUESTIONS = {
    "Binary Search": ["Binary Search", "Search a 2D Matrix"],
    "Two Pointers": ["Valid Palindrome", "3Sum"]
}


# ============================================================================
# Mock Provider Classes
# ============================================================================

class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing that returns configurable responses."""

    def __init__(
        self,
        name: str = "mock_provider",
        model: str = "mock-model",
        responses: Optional[Dict[str, Any]] = None,
        fail_initial: bool = False,
        fail_combine: bool = False,
    ):
        self._name = name
        self._model = model
        self.responses = responses or {}
        self.fail_initial = fail_initial
        self.fail_combine = fail_combine
        self.initial_call_count = 0
        self.combine_call_count = 0
        self.format_call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    async def generate_initial_cards(
        self,
        question: str,
        json_schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
    ) -> str:
        self.initial_call_count += 1
        if self.fail_initial:
            return ""
        return self.responses.get("initial", SAMPLE_CARD_RESPONSE)

    async def combine_cards(
        self,
        question: str,
        combined_inputs: str,
        json_schema: Dict[str, Any],
        combine_prompt_template: Optional[str] = None,
    ) -> Optional[str]:
        self.combine_call_count += 1
        if self.fail_combine:
            return None
        return self.responses.get("combine", SAMPLE_CARD_RESPONSE)

    async def format_json(
        self,
        raw_content: str,
        json_schema: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        self.format_call_count += 1
        return self.responses.get("format", SAMPLE_CARD_RESPONSE_DICT)


class FailingMockProvider(MockLLMProvider):
    """Mock provider that always fails."""

    def __init__(self, name: str = "failing_provider", model: str = "fail-model"):
        super().__init__(name=name, model=model, fail_initial=True, fail_combine=True)


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    manager = DatabaseManager()
    manager.initialize(Path(":memory:"))
    DatabaseManager.set_default(manager)
    yield manager
    DatabaseManager.reset_default()


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary file-based SQLite database for testing."""
    db_path = tmp_path / "test.db"
    manager = DatabaseManager()
    manager.initialize(db_path)
    DatabaseManager.set_default(manager)
    yield manager
    DatabaseManager.reset_default()


# ============================================================================
# Mock Provider Fixtures
# ============================================================================

@pytest.fixture
def mock_provider():
    """Create a single mock provider with default responses."""
    return MockLLMProvider()


@pytest.fixture
def mock_provider_with_responses():
    """Factory fixture to create mock providers with custom responses."""
    def _create(responses: Dict[str, Any] = None, **kwargs):
        return MockLLMProvider(responses=responses, **kwargs)
    return _create


@pytest.fixture
def failing_provider():
    """Create a failing mock provider."""
    return FailingMockProvider()


@pytest.fixture
def mock_providers():
    """Create a list of mock providers for testing parallel generation."""
    return [
        MockLLMProvider(name="provider1", model="model1"),
        MockLLMProvider(name="provider2", model="model2"),
    ]


# ============================================================================
# OpenAI Client Mock Fixtures
# ============================================================================

class MockMessage:
    """Mock OpenAI message object."""
    def __init__(self, content: str):
        self.content = content


class MockChoice:
    """Mock OpenAI choice object."""
    def __init__(self, message: MockMessage):
        self.message = message


class MockCompletion:
    """Mock OpenAI completion response."""
    def __init__(self, choices: list):
        self.choices = choices


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI completion response."""
    return MockCompletion(
        choices=[MockChoice(message=MockMessage(content=SAMPLE_CARD_RESPONSE))]
    )


@pytest.fixture
def mock_openai_client(mock_openai_response):
    """Mock the AsyncOpenAI client."""
    with patch("src.providers.openai_compatible.AsyncOpenAI") as mock:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_openai_empty_response():
    """Create a mock OpenAI completion with empty response."""
    return MockCompletion(
        choices=[MockChoice(message=MockMessage(content=""))]
    )


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_config_yaml(tmp_path):
    """Create a sample config.yaml file for testing."""
    config_content = """
defaults:
  timeout: 60.0
  temperature: 0.5
  max_retries: 3

providers:
  cerebras:
    enabled: true
    model: "llama3.1-70b"
  openrouter:
    enabled: false
    model: "gpt-4"

generation:
  concurrent_requests: 4
  request_delay: 0.1

subjects:
  leetcode:
    enabled: true
  cs:
    enabled: true
  physics:
    enabled: false
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_questions_file(tmp_path):
    """Create a sample questions JSON file for testing."""
    questions = {
        "Category1": ["Question 1", "Question 2"],
        "Category2": ["Question 3"]
    }
    questions_path = tmp_path / "questions.json"
    questions_path.write_text(json.dumps(questions))
    return questions_path


# ============================================================================
# Prompt Fixtures
# ============================================================================

@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create a temporary prompts directory with sample prompts."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    (prompts_dir / "initial.md").write_text("Generate cards for {question}\nSchema: {schema}")
    (prompts_dir / "combine.md").write_text("Combine cards: {inputs}")
    (prompts_dir / "initial_cs.md").write_text("CS prompt for {question}")
    (prompts_dir / "combine_cs.md").write_text("CS combine: {inputs}")
    (prompts_dir / "mcq.md").write_text("MCQ prompt for {question}")
    (prompts_dir / "mcq_combine.md").write_text("MCQ combine: {inputs}")
    (prompts_dir / "physics.md").write_text("Physics prompt for {question}")
    (prompts_dir / "physics_mcq.md").write_text("Physics MCQ for {question}")
    (prompts_dir / "combine_leetcode.md").write_text("LeetCode combine: {inputs}")

    return prompts_dir


# ============================================================================
# Anki Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_card_data():
    """Sample card data for Anki deck generation tests."""
    return [
        {
            "title": "Binary Search",
            "topic": "Arrays",
            "difficulty": "Medium",
            "category_index": 1,
            "category_name": "Binary Search",
            "problem_index": 1,
            "cards": [
                {
                    "card_type": "Algorithm",
                    "tags": ["BinarySearch", "Arrays"],
                    "front": "What is binary search?",
                    "back": "A search algorithm for sorted arrays."
                }
            ]
        }
    ]


@pytest.fixture
def sample_mcq_card_data():
    """Sample MCQ card data for Anki deck generation tests."""
    return [
        {
            "title": "Binary Search MCQ",
            "topic": "Algorithms",
            "difficulty": "Medium",
            "cards": [
                {
                    "card_type": "Concept",
                    "tags": ["BinarySearch"],
                    "question": "What is the time complexity?",
                    "options": ["O(n)", "O(log n)", "O(n^2)", "O(1)"],
                    "correct_answer": "B",
                    "explanation": "Binary search is O(log n)."
                }
            ]
        }
    ]


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_archival_dir(tmp_path):
    """Create a temporary archival directory structure for testing."""
    archival_dir = tmp_path / "archival"
    archival_dir.mkdir()

    # Create subject subdirectories
    for subject in ["leetcode", "cs", "physics"]:
        subject_dir = archival_dir / subject
        subject_dir.mkdir()

    return archival_dir


@pytest.fixture
def populated_archival_dir(temp_archival_dir):
    """Create an archival directory with sample JSON files."""
    cs_dir = temp_archival_dir / "cs"

    # Create sample JSON files
    for i in range(3):
        file_path = cs_dir / f"sample_{i}.json"
        data = {
            "title": f"Topic {i}",
            "topic": "CS",
            "difficulty": "Medium",
            "cards": [{"front": f"Q{i}", "back": f"A{i}", "card_type": "Basic", "tags": []}]
        }
        file_path.write_text(json.dumps(data))

    return temp_archival_dir


# ============================================================================
# Async Test Helpers
# ============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
