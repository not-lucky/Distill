"""Tests for Orchestrator in src/orchestrator.py."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.orchestrator import Orchestrator
from src.config.subjects import SubjectConfig
from src.models import LeetCodeProblem

from conftest import MockLLMProvider, SAMPLE_CARD_RESPONSE_DICT


class TestOrchestrator:
    """Tests for Orchestrator class."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return SubjectConfig(
            name="leetcode",
            target_questions={"Arrays": ["Two Sum", "Binary Search"]},
            initial_prompt="Initial prompt",
            combine_prompt="Combine prompt",
            target_model=LeetCodeProblem,
            deck_prefix="LeetCode",
            deck_prefix_mcq="LeetCode_MCQ",
        )

    @pytest.fixture
    def orchestrator(self, subject_config, in_memory_db):
        """Create an Orchestrator instance."""
        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            mock_run_repo.run_id = "test-run-id"
            mock_run_repo.get_card_repository.return_value = MagicMock()
            MockRunRepo.return_value = mock_run_repo

            orch = Orchestrator(
                subject_config=subject_config,
                is_mcq=False,
                run_label="test",
            )
            orch.run_repo = mock_run_repo
            return orch

    def test_init(self, subject_config):
        """Test Orchestrator initialization."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(
                subject_config=subject_config,
                is_mcq=False,
                run_label="test label",
            )

            assert orch.subject_config == subject_config
            assert orch.is_mcq is False
            assert orch.run_label == "test label"
            assert orch.dry_run is False

    def test_init_mcq_mode(self, subject_config):
        """Test Orchestrator in MCQ mode."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(
                subject_config=subject_config,
                is_mcq=True,
            )

            assert orch.is_mcq is True

    def test_init_dry_run(self, subject_config):
        """Test Orchestrator in dry run mode."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(
                subject_config=subject_config,
                is_mcq=False,
                dry_run=True,
            )

            assert orch.dry_run is True

    def test_generation_mode_standard(self, orchestrator):
        """Test generation_mode for standard mode."""
        assert orchestrator.generation_mode == "leetcode"

    def test_generation_mode_mcq(self, subject_config):
        """Test generation_mode for MCQ mode."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(
                subject_config=subject_config,
                is_mcq=True,
            )
            assert orch.generation_mode == "leetcode_mcq"

    def test_deck_prefix_standard(self, orchestrator):
        """Test deck_prefix for standard mode."""
        assert orchestrator.deck_prefix == "LeetCode"

    def test_deck_prefix_mcq(self, subject_config):
        """Test deck_prefix for MCQ mode."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(
                subject_config=subject_config,
                is_mcq=True,
            )
            assert orch.deck_prefix == "LeetCode_MCQ"

    def test_run_id_property(self, orchestrator):
        """Test run_id property."""
        orchestrator.run_repo.run_id = "test-123"
        assert orchestrator.run_id == "test-123"


class TestOrchestratorInitialize:
    """Tests for Orchestrator.initialize method."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return SubjectConfig(
            name="leetcode",
            target_questions={"Arrays": ["Two Sum"]},
            initial_prompt="Prompt",
            combine_prompt="Combine",
            target_model=LeetCodeProblem,
            deck_prefix="LeetCode",
            deck_prefix_mcq="LeetCode_MCQ",
        )

    @pytest.mark.asyncio
    async def test_initialize_success(self, subject_config, in_memory_db):
        """Test successful initialization."""
        mock_providers = [
            MockLLMProvider(name="p1", model="m1"),
            MockLLMProvider(name="p2", model="m2"),
        ]
        mock_combiner = MockLLMProvider(name="combiner", model="c-model")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            mock_run_repo.run_id = "test-run"
            mock_run_repo.get_card_repository.return_value = MagicMock()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = (mock_providers, mock_combiner, None)

                orch = Orchestrator(subject_config=subject_config)
                result = await orch.initialize()

                assert result is True
                assert orch.card_generator is not None

    @pytest.mark.asyncio
    async def test_initialize_no_providers(self, subject_config):
        """Test initialization with no providers."""
        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], None, None)

                orch = Orchestrator(subject_config=subject_config)
                result = await orch.initialize()

                assert result is False
                mock_run_repo.mark_run_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_dry_run(self, subject_config):
        """Test initialization in dry run mode."""
        mock_providers = [MockLLMProvider()]
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository"):
            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = (mock_providers, mock_combiner, None)

                orch = Orchestrator(subject_config=subject_config, dry_run=True)
                result = await orch.initialize()

                assert result is True
                # Card generator should have None repository in dry run
                assert orch.card_generator.repository is None

    @pytest.mark.asyncio
    async def test_initialize_uses_first_provider_as_combiner(self, subject_config):
        """Test that first provider is used as combiner if none specified."""
        mock_providers = [
            MockLLMProvider(name="first", model="m1"),
            MockLLMProvider(name="second", model="m2"),
        ]

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            mock_run_repo.run_id = "test"
            mock_run_repo.get_card_repository.return_value = MagicMock()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                # Return providers but no explicit combiner
                mock_init.return_value = (mock_providers, None, None)

                orch = Orchestrator(subject_config=subject_config)
                result = await orch.initialize()

                assert result is True
                # First provider should be combiner, rest should be generators
                assert orch.card_generator.card_combiner.name == "first"
                assert len(orch.card_generator.llm_providers) == 1


class TestOrchestratorRun:
    """Tests for Orchestrator.run method."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return SubjectConfig(
            name="leetcode",
            target_questions={"Arrays": ["Two Sum", "Binary Search"]},
            initial_prompt="Prompt",
            combine_prompt="Combine",
            target_model=LeetCodeProblem,
            deck_prefix="LeetCode",
            deck_prefix_mcq="LeetCode_MCQ",
        )

    @pytest.mark.asyncio
    async def test_run_not_initialized(self, subject_config):
        """Test run raises error if not initialized."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)

            with pytest.raises(RuntimeError, match="not initialized"):
                await orch.run()

    @pytest.mark.asyncio
    async def test_run_dry_run_returns_empty(self, subject_config):
        """Test run in dry run mode returns empty list."""
        mock_providers = [MockLLMProvider()]
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository"):
            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = (mock_providers, mock_combiner, None)

                orch = Orchestrator(subject_config=subject_config, dry_run=True)
                await orch.initialize()
                result = await orch.run()

                assert result == []

    @pytest.mark.asyncio
    async def test_run_processes_questions(self, subject_config, in_memory_db):
        """Test run processes all questions."""
        mock_providers = [MockLLMProvider()]
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            mock_run_repo.run_id = "test"
            mock_run_repo.get_card_repository.return_value = MagicMock()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = (mock_providers, mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    mock_gen.process_question = AsyncMock(
                        return_value=SAMPLE_CARD_RESPONSE_DICT
                    )
                    MockGenerator.return_value = mock_gen

                    orch = Orchestrator(subject_config=subject_config)
                    await orch.initialize()
                    results = await orch.run()

                    # Should have called process_question for each question
                    assert mock_gen.process_question.call_count == 2


class TestOrchestratorSaveResults:
    """Tests for Orchestrator.save_results method."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return SubjectConfig(
            name="leetcode",
            target_questions={},
            initial_prompt=None,
            combine_prompt=None,
            target_model=LeetCodeProblem,
            deck_prefix="LeetCode",
            deck_prefix_mcq="LeetCode_MCQ",
        )

    def test_save_results_empty(self, subject_config):
        """Test saving empty results returns None."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            result = orch.save_results([])

            assert result is None

    def test_save_results_dry_run(self, subject_config):
        """Test saving results in dry run mode."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config, dry_run=True)
            result = orch.save_results([{"title": "Test"}])

            assert result == "leetcode_anki_deck"

    def test_save_results_success(self, subject_config, tmp_path, monkeypatch):
        """Test saving results creates file."""
        monkeypatch.chdir(tmp_path)

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            mock_run_repo.run_id = "test-run"
            MockRunRepo.return_value = mock_run_repo

            orch = Orchestrator(subject_config=subject_config)
            orch.run_repo = mock_run_repo

            problems = [
                {"title": "Problem 1", "cards": []},
                {"title": "Problem 2", "cards": []},
            ]

            result = orch.save_results(problems)

            assert result == "leetcode_anki_deck"
            # Verify file was created
            json_files = list(tmp_path.glob("leetcode_anki_deck_*.json"))
            assert len(json_files) == 1
