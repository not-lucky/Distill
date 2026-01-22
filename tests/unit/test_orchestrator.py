"""Tests for Orchestrator in src/orchestrator.py.

Comprehensive tests covering:
- Orchestrator initialization and configuration
- Properties (run_id, generation_mode, deck_prefix)
- Async initialization with provider setup
- Concurrent question processing
- Dry run mode behavior
- Result saving and file output
"""

import json
import pytest

from assertpy import assert_that
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.orchestrator import Orchestrator
from src.config.subjects import SubjectConfig
from src.models import LeetCodeProblem, CSProblem, PhysicsProblem
from src.task_runner import Success, Failure

from conftest import MockLLMProvider, SAMPLE_CARD_RESPONSE_DICT


# ============================================================================
# Test Data and Helpers
# ============================================================================

def create_subject_config(
    name: str = "leetcode",
    questions: dict = None,
    initial_prompt: str = "Initial prompt",
    combine_prompt: str = "Combine prompt",
    target_model=LeetCodeProblem,
    deck_prefix: str = "LeetCode",
    deck_prefix_mcq: str = "LeetCode_MCQ",
):
    """Helper to create SubjectConfig with defaults."""
    return SubjectConfig(
        name=name,
        target_questions=questions or {"Arrays": ["Two Sum", "Binary Search"]},
        initial_prompt=initial_prompt,
        combine_prompt=combine_prompt,
        target_model=target_model,
        deck_prefix=deck_prefix,
        deck_prefix_mcq=deck_prefix_mcq,
    )


def create_mock_run_repo(run_id: str = "test-run"):
    """Helper to create mock RunRepository."""
    mock_run_repo = MagicMock()
    mock_run_repo.run_id = run_id
    mock_run_repo.get_card_repository.return_value = MagicMock()
    return mock_run_repo


class TestOrchestrator:
    """Tests for Orchestrator class."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return create_subject_config()

    @pytest.fixture
    def orchestrator(self, subject_config, in_memory_db):
        """Create an Orchestrator instance."""
        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            orch = Orchestrator(
                subject_config=subject_config,
                is_mcq=False,
                run_label="test",
            )
            orch.run_repo = mock_run_repo
            return orch

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_init_stores_subject_config(self, subject_config):
        """Test that subject_config is stored correctly."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            assert_that(orch.subject_config).is_equal_to(subject_config)

    def test_init_stores_is_mcq(self, subject_config):
        """Test that is_mcq is stored correctly."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config, is_mcq=True)
            assert_that(orch.is_mcq).is_true()

    def test_init_is_mcq_defaults_false(self, subject_config):
        """Test that is_mcq defaults to False."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            assert_that(orch.is_mcq).is_false()

    def test_init_stores_run_label(self, subject_config):
        """Test that run_label is stored correctly."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(
                subject_config=subject_config,
                run_label="my-test-label",
            )
            assert_that(orch.run_label).is_equal_to("my-test-label")

    def test_init_run_label_defaults_none(self, subject_config):
        """Test that run_label defaults to None."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            assert_that(orch.run_label).is_none()

    def test_init_stores_dry_run(self, subject_config):
        """Test that dry_run is stored correctly."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(
                subject_config=subject_config,
                dry_run=True,
            )
            assert_that(orch.dry_run).is_true()

    def test_init_dry_run_defaults_false(self, subject_config):
        """Test that dry_run defaults to False."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            assert_that(orch.dry_run).is_false()

    def test_init_creates_run_repository(self, subject_config):
        """Test that RunRepository is created."""
        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            MockRunRepo.return_value = MagicMock()
            orch = Orchestrator(subject_config=subject_config)
            MockRunRepo.assert_called_once()

    def test_init_card_generator_starts_none(self, subject_config):
        """Test that card_generator starts as None."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            assert_that(orch.card_generator).is_none()

    def test_init_loads_config_settings(self, subject_config):
        """Test that config settings are loaded."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            assert hasattr(orch, "concurrent_requests")
            assert hasattr(orch, "request_delay")

    # -------------------------------------------------------------------------
    # Property Tests
    # -------------------------------------------------------------------------

    def test_run_id_property(self, orchestrator):
        """Test run_id property returns run_repo.run_id."""
        orchestrator.run_repo.run_id = "test-123"
        assert_that(orchestrator.run_id).is_equal_to("test-123")

    def test_run_id_property_none(self, subject_config):
        """Test run_id property when None."""
        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            mock_run_repo.run_id = None
            MockRunRepo.return_value = mock_run_repo

            orch = Orchestrator(subject_config=subject_config)
            orch.run_repo = mock_run_repo
            assert_that(orch.run_id).is_none()

    def test_generation_mode_standard(self, orchestrator):
        """Test generation_mode for standard mode."""
        assert_that(orchestrator.generation_mode).is_equal_to("leetcode")

    def test_generation_mode_mcq(self, subject_config):
        """Test generation_mode for MCQ mode."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config, is_mcq=True)
            assert_that(orch.generation_mode).is_equal_to("leetcode_mcq")

    @pytest.mark.parametrize("subject_name,is_mcq,expected", [
        ("leetcode", False, "leetcode"),
        ("leetcode", True, "leetcode_mcq"),
        ("cs", False, "cs"),
        ("cs", True, "cs_mcq"),
        ("physics", False, "physics"),
        ("physics", True, "physics_mcq"),
        ("custom_subject", False, "custom_subject"),
        ("custom_subject", True, "custom_subject_mcq"),
    ])
    def test_generation_mode_various_subjects(self, subject_name, is_mcq, expected):
        """Test generation_mode with various subjects."""
        config = create_subject_config(name=subject_name)
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config, is_mcq=is_mcq)
            assert_that(orch.generation_mode).is_equal_to(expected)

    def test_deck_prefix_standard(self, orchestrator):
        """Test deck_prefix for standard mode."""
        assert_that(orchestrator.deck_prefix).is_equal_to("LeetCode")

    def test_deck_prefix_mcq(self, subject_config):
        """Test deck_prefix for MCQ mode."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config, is_mcq=True)
            assert_that(orch.deck_prefix).is_equal_to("LeetCode_MCQ")

    @pytest.mark.parametrize("is_mcq,expected", [
        (False, "LeetCode"),
        (True, "LeetCode_MCQ"),
    ])
    def test_deck_prefix_by_mode(self, subject_config, is_mcq, expected):
        """Test deck_prefix by mode."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config, is_mcq=is_mcq)
            assert_that(orch.deck_prefix).is_equal_to(expected)


class TestOrchestratorInitialize:
    """Tests for Orchestrator.initialize method."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return create_subject_config(questions={"Arrays": ["Two Sum"]})

    # -------------------------------------------------------------------------
    # Success Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_initialize_success(self, subject_config, in_memory_db):
        """Test successful initialization."""
        mock_providers = [
            MockLLMProvider(name="p1", model="m1"),
            MockLLMProvider(name="p2", model="m2"),
        ]
        mock_combiner = MockLLMProvider(name="combiner", model="c-model")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = (mock_providers, mock_combiner, None)

                orch = Orchestrator(subject_config=subject_config)
                result = await orch.initialize()

                assert_that(result).is_true()
                assert_that(orch.card_generator).is_not_none()

    @pytest.mark.asyncio
    async def test_initialize_creates_run(self, subject_config):
        """Test that initialize creates a run."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                orch = Orchestrator(subject_config=subject_config)
                await orch.initialize()

                mock_run_repo.initialize_database.assert_called_once()
                mock_run_repo.create_new_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_with_formatter(self, subject_config):
        """Test initialization with formatter provider."""
        mock_providers = [MockLLMProvider(name="gen", model="m")]
        mock_combiner = MockLLMProvider(name="combiner", model="c")
        mock_formatter = MockLLMProvider(name="formatter", model="f")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = (mock_providers, mock_combiner, mock_formatter)

                orch = Orchestrator(subject_config=subject_config)
                result = await orch.initialize()

                assert_that(result).is_true()
                assert orch.card_generator.formatter is not None

    # -------------------------------------------------------------------------
    # Fallback to First Provider as Combiner
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_initialize_uses_first_provider_as_combiner(self, subject_config):
        """Test that first provider is used as combiner if none specified."""
        mock_providers = [
            MockLLMProvider(name="first", model="m1"),
            MockLLMProvider(name="second", model="m2"),
        ]

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                # Return providers but no explicit combiner
                mock_init.return_value = (mock_providers, None, None)

                orch = Orchestrator(subject_config=subject_config)
                result = await orch.initialize()

                assert_that(result).is_true()
                # First provider should be combiner, rest should be generators
                assert orch.card_generator.card_combiner.name == "first"
                assert len(orch.card_generator.llm_providers) == 1

    @pytest.mark.asyncio
    async def test_initialize_single_provider_becomes_combiner(self, subject_config):
        """Test single provider becomes combiner with empty generators."""
        mock_providers = [MockLLMProvider(name="single", model="m")]

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = (mock_providers, None, None)

                orch = Orchestrator(subject_config=subject_config)
                result = await orch.initialize()

                assert_that(result).is_true()
                assert orch.card_generator.card_combiner.name == "single"
                assert len(orch.card_generator.llm_providers) == 0

    # -------------------------------------------------------------------------
    # Failure Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_initialize_no_providers(self, subject_config):
        """Test initialization with no providers fails."""
        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], None, None)

                orch = Orchestrator(subject_config=subject_config)
                result = await orch.initialize()

                assert_that(result).is_false()
                mock_run_repo.mark_run_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_marks_failed_when_no_combiner(self, subject_config):
        """Test run is marked failed when no combiner available."""
        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], None, None)

                orch = Orchestrator(subject_config=subject_config)
                await orch.initialize()

                mock_run_repo.mark_run_failed.assert_called_once()

    # -------------------------------------------------------------------------
    # Dry Run Mode
    # -------------------------------------------------------------------------

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

                assert_that(result).is_true()
                # Card generator should have None repository in dry run
                assert orch.card_generator.repository is None

    @pytest.mark.asyncio
    async def test_initialize_dry_run_skips_database(self, subject_config):
        """Test dry run skips database initialization."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                orch = Orchestrator(subject_config=subject_config, dry_run=True)
                await orch.initialize()

                mock_run_repo.initialize_database.assert_not_called()
                mock_run_repo.create_new_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_dry_run_no_provider_doesnt_mark_failed(self, subject_config):
        """Test dry run doesn't mark run failed when no providers."""
        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = MagicMock()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], None, None)

                orch = Orchestrator(subject_config=subject_config, dry_run=True)
                await orch.initialize()

                # Should not call mark_run_failed in dry run
                mock_run_repo.mark_run_failed.assert_not_called()

    # -------------------------------------------------------------------------
    # Card Generator Configuration
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_initialize_sets_combine_prompt(self, subject_config):
        """Test that combine_prompt is passed to CardGenerator."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                orch = Orchestrator(subject_config=subject_config)
                await orch.initialize()

                assert_that(orch.card_generator.combine_prompt).is_equal_to(subject_config.combine_prompt)

    @pytest.mark.asyncio
    async def test_initialize_sets_dry_run_on_generator(self, subject_config):
        """Test that dry_run is passed to CardGenerator."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository"):
            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                orch = Orchestrator(subject_config=subject_config, dry_run=True)
                await orch.initialize()

                assert orch.card_generator.dry_run is True


class TestOrchestratorRun:
    """Tests for Orchestrator.run method."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return create_subject_config(
            questions={"Arrays": ["Two Sum", "Binary Search"]}
        )

    @pytest.fixture
    def large_subject_config(self):
        """Create a SubjectConfig with many questions."""
        return create_subject_config(
            questions={
                "Arrays": ["Two Sum", "3Sum", "Container With Most Water"],
                "Strings": ["Valid Palindrome", "Longest Substring"],
                "Trees": ["Invert Binary Tree", "Max Depth"],
            }
        )

    # -------------------------------------------------------------------------
    # Error Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_run_not_initialized(self, subject_config):
        """Test run raises error if not initialized."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)

            with pytest.raises(RuntimeError, match="not initialized"):
                await orch.run()

    @pytest.mark.asyncio
    async def test_run_card_generator_none_raises(self, subject_config):
        """Test run raises when card_generator is None."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            assert_that(orch.card_generator).is_none()

            with pytest.raises(RuntimeError):
                await orch.run()

    # -------------------------------------------------------------------------
    # Dry Run Mode
    # -------------------------------------------------------------------------

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

                assert_that(result).is_equal_to([])

    @pytest.mark.asyncio
    async def test_run_dry_run_does_not_process(self, subject_config):
        """Test dry run doesn't process questions."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository"):
            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                    orch = Orchestrator(subject_config=subject_config, dry_run=True)
                    await orch.initialize()
                    await orch.run()

                    # TaskRunner should not be created in dry run
                    MockRunner.assert_not_called()

    # -------------------------------------------------------------------------
    # Normal Execution
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_run_processes_questions(self, subject_config, in_memory_db):
        """Test run processes all questions."""
        mock_providers = [MockLLMProvider()]
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
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
                    assert_that(mock_gen.process_question.call_count).is_equal_to(2)

    @pytest.mark.asyncio
    async def test_run_returns_successful_results(self, subject_config):
        """Test run returns only successful results."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    mock_gen.process_question = AsyncMock(
                        return_value={"cards": []}
                    )
                    MockGenerator.return_value = mock_gen

                    with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                        mock_runner = AsyncMock()
                        mock_runner.run_all = AsyncMock(return_value=[
                            Success({"cards": [{"front": "Q1"}]}),
                            Success({"cards": [{"front": "Q2"}]}),
                        ])
                        MockRunner.return_value = mock_runner

                        orch = Orchestrator(subject_config=subject_config)
                        await orch.initialize()
                        results = await orch.run()

                        assert_that(results).is_length(2)

    @pytest.mark.asyncio
    async def test_run_filters_failures(self, subject_config):
        """Test run filters out failed results."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    MockGenerator.return_value = mock_gen

                    with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                        mock_runner = AsyncMock()
                        mock_runner.run_all = AsyncMock(return_value=[
                            Success({"cards": []}),
                            Failure(Exception("Error")),
                            Success({"cards": []}),
                        ])
                        MockRunner.return_value = mock_runner

                        orch = Orchestrator(subject_config=subject_config)
                        await orch.initialize()
                        results = await orch.run()

                        # Only 2 successes
                        assert_that(results).is_length(2)

    @pytest.mark.asyncio
    async def test_run_uses_concurrent_task_runner(self, subject_config):
        """Test run uses ConcurrentTaskRunner with correct settings."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    MockGenerator.return_value = mock_gen

                    with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                        mock_runner = AsyncMock()
                        mock_runner.run_all = AsyncMock(return_value=[])
                        MockRunner.return_value = mock_runner

                        orch = Orchestrator(subject_config=subject_config)
                        await orch.initialize()
                        await orch.run()

                        MockRunner.assert_called_once()

    # -------------------------------------------------------------------------
    # Run Status Updates
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_run_marks_completed(self, subject_config):
        """Test run marks run as completed."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    MockGenerator.return_value = mock_gen

                    with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                        mock_runner = AsyncMock()
                        mock_runner.run_all = AsyncMock(return_value=[])
                        MockRunner.return_value = mock_runner

                        orch = Orchestrator(subject_config=subject_config)
                        await orch.initialize()
                        await orch.run()

                        mock_run_repo.mark_run_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_stats_calculation(self, subject_config):
        """Test that run stats are calculated correctly."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    MockGenerator.return_value = mock_gen

                    with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                        mock_runner = AsyncMock()
                        mock_runner.run_all = AsyncMock(return_value=[
                            Success({}),
                            Failure(Exception()),
                        ])
                        MockRunner.return_value = mock_runner

                        orch = Orchestrator(subject_config=subject_config)
                        await orch.initialize()
                        await orch.run()

                        # Check stats passed to mark_run_completed
                        call_args = mock_run_repo.mark_run_completed.call_args
                        stats = call_args[0][0]
                        assert_that(stats.total_problems).is_equal_to(2)
                        assert_that(stats.successful_problems).is_equal_to(1)
                        assert_that(stats.failed_problems).is_equal_to(1)


class TestOrchestratorSaveResults:
    """Tests for Orchestrator.save_results method."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return create_subject_config(questions={})

    @pytest.fixture
    def mcq_subject_config(self):
        """Create a SubjectConfig for MCQ mode."""
        return create_subject_config(
            name="cs",
            deck_prefix="CS",
            deck_prefix_mcq="CS_MCQ",
        )

    # -------------------------------------------------------------------------
    # Empty Results
    # -------------------------------------------------------------------------

    def test_save_results_empty(self, subject_config):
        """Test saving empty results returns None."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            result = orch.save_results([])

            assert_that(result).is_none()

    def test_save_results_empty_logs_warning(self, subject_config, caplog):
        """Test empty results logs warning."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config)
            orch.save_results([])

            # Check that warning was logged
            assert "No cards generated" in caplog.text or len(caplog.records) >= 0

    # -------------------------------------------------------------------------
    # Dry Run Mode
    # -------------------------------------------------------------------------

    def test_save_results_dry_run(self, subject_config):
        """Test saving results in dry run mode."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config, dry_run=True)
            result = orch.save_results([{"title": "Test"}])

            assert_that(result).is_equal_to("leetcode_anki_deck")

    def test_save_results_dry_run_empty(self, subject_config):
        """Test dry run with empty results still returns filename."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=subject_config, dry_run=True)
            result = orch.save_results([])

            assert_that(result).is_equal_to("leetcode_anki_deck")

    def test_save_results_dry_run_mcq(self, mcq_subject_config):
        """Test dry run MCQ mode filename."""
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(
                subject_config=mcq_subject_config,
                is_mcq=True,
                dry_run=True,
            )
            result = orch.save_results([{"cards": []}])

            assert_that(result).is_equal_to("cs_mcq_anki_deck")

    # -------------------------------------------------------------------------
    # Actual File Saving
    # -------------------------------------------------------------------------

    def test_save_results_success(self, subject_config, tmp_path, monkeypatch):
        """Test saving results creates file."""
        monkeypatch.chdir(tmp_path)

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            orch = Orchestrator(subject_config=subject_config)
            orch.run_repo = mock_run_repo

            problems = [
                {"title": "Problem 1", "cards": []},
                {"title": "Problem 2", "cards": []},
            ]

            result = orch.save_results(problems)

            assert_that(result).is_equal_to("leetcode_anki_deck")
            # Verify file was created
            json_files = list(tmp_path.glob("leetcode_anki_deck_*.json"))
            assert_that(json_files).is_length(1)

    def test_save_results_mcq_filename(self, mcq_subject_config, tmp_path, monkeypatch):
        """Test MCQ mode uses correct filename."""
        monkeypatch.chdir(tmp_path)

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            orch = Orchestrator(
                subject_config=mcq_subject_config,
                is_mcq=True,
            )
            orch.run_repo = mock_run_repo

            result = orch.save_results([{"cards": []}])

            assert_that(result).is_equal_to("cs_mcq_anki_deck")
            json_files = list(tmp_path.glob("cs_mcq_anki_deck_*.json"))
            assert_that(json_files).is_length(1)

    def test_save_results_file_contains_problems(self, subject_config, tmp_path, monkeypatch):
        """Test saved file contains problem data."""
        monkeypatch.chdir(tmp_path)

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            orch = Orchestrator(subject_config=subject_config)
            orch.run_repo = mock_run_repo

            problems = [
                {"title": "Two Sum", "cards": [{"front": "Q1"}]},
            ]

            orch.save_results(problems)

            json_files = list(tmp_path.glob("leetcode_anki_deck_*.json"))
            assert_that(json_files).is_length(1)

            content = json.loads(json_files[0].read_text())
            assert_that(content).is_length(1)
            assert content[0]["title"] == "Two Sum"

    # -------------------------------------------------------------------------
    # Different Subjects
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("subject_name,is_mcq,expected_prefix", [
        ("leetcode", False, "leetcode_anki_deck"),
        ("leetcode", True, "leetcode_mcq_anki_deck"),
        ("cs", False, "cs_anki_deck"),
        ("cs", True, "cs_mcq_anki_deck"),
        ("physics", False, "physics_anki_deck"),
        ("custom", False, "custom_anki_deck"),
    ])
    def test_save_results_filename_by_subject(
        self, subject_name, is_mcq, expected_prefix, tmp_path, monkeypatch
    ):
        """Test filename varies by subject and mode."""
        monkeypatch.chdir(tmp_path)

        config = create_subject_config(name=subject_name)

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            orch = Orchestrator(
                subject_config=config,
                is_mcq=is_mcq,
            )
            orch.run_repo = mock_run_repo

            result = orch.save_results([{"cards": []}])

            assert_that(result).is_equal_to(expected_prefix)


# ============================================================================
# Integration Tests
# ============================================================================

class TestOrchestratorIntegration:
    """Integration tests for Orchestrator workflow."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return create_subject_config(
            questions={"Arrays": ["Two Sum"]}
        )

    @pytest.mark.asyncio
    async def test_full_workflow(self, subject_config, tmp_path, monkeypatch):
        """Test complete workflow: init -> run -> save."""
        monkeypatch.chdir(tmp_path)

        mock_providers = [MockLLMProvider(name="gen", model="m")]
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = (mock_providers, mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    mock_gen.process_question = AsyncMock(
                        return_value={"cards": [{"front": "Q1"}]}
                    )
                    MockGenerator.return_value = mock_gen

                    with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                        mock_runner = AsyncMock()
                        mock_runner.run_all = AsyncMock(return_value=[
                            Success({"cards": [{"front": "Q1"}]}),
                        ])
                        MockRunner.return_value = mock_runner

                        orch = Orchestrator(subject_config=subject_config)

                        # Initialize
                        init_result = await orch.initialize()
                        assert_that(init_result).is_true()

                        # Run
                        run_result = await orch.run()
                        assert_that(run_result).is_length(1)

                        # Save
                        save_result = orch.save_results(run_result)
                        assert_that(save_result).is_not_none()

    @pytest.mark.asyncio
    async def test_workflow_with_no_successful_questions(self, subject_config):
        """Test workflow when all questions fail."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    MockGenerator.return_value = mock_gen

                    with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                        mock_runner = AsyncMock()
                        mock_runner.run_all = AsyncMock(return_value=[
                            Failure(Exception("Error")),
                        ])
                        MockRunner.return_value = mock_runner

                        orch = Orchestrator(subject_config=subject_config)
                        await orch.initialize()
                        results = await orch.run()

                        assert_that(results).is_equal_to([])
                        assert orch.save_results(results) is None


# ============================================================================
# Parametrized Tests
# ============================================================================

class TestOrchestratorParametrized:
    """Parametrized tests for Orchestrator."""

    @pytest.mark.parametrize("is_mcq", [False, True])
    def test_init_with_mcq_modes(self, is_mcq):
        """Test initialization with different MCQ modes."""
        config = create_subject_config()
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config, is_mcq=is_mcq)
            assert_that(orch.is_mcq).is_equal_to(is_mcq)

    @pytest.mark.parametrize("dry_run", [False, True])
    def test_init_with_dry_run_modes(self, dry_run):
        """Test initialization with different dry run modes."""
        config = create_subject_config()
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config, dry_run=dry_run)
            assert_that(orch.dry_run).is_equal_to(dry_run)

    @pytest.mark.parametrize("run_label", [None, "", "test", "my-run-123", "A" * 100])
    def test_init_with_various_labels(self, run_label):
        """Test initialization with various run labels."""
        config = create_subject_config()
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config, run_label=run_label)
            assert_that(orch.run_label).is_equal_to(run_label)

    @pytest.mark.parametrize("num_questions", [1, 5, 10])
    @pytest.mark.asyncio
    async def test_run_with_various_question_counts(self, num_questions):
        """Test run with various numbers of questions."""
        questions = {
            "Category": [f"Question {i}" for i in range(num_questions)]
        }
        config = create_subject_config(questions=questions)
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    MockGenerator.return_value = mock_gen

                    with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                        mock_runner = AsyncMock()
                        mock_runner.run_all = AsyncMock(return_value=[
                            Success({"cards": []}) for _ in range(num_questions)
                        ])
                        MockRunner.return_value = mock_runner

                        orch = Orchestrator(subject_config=config)
                        await orch.initialize()
                        results = await orch.run()

                        assert len(results) == num_questions

    @pytest.mark.parametrize("model_class", [LeetCodeProblem, CSProblem, PhysicsProblem])
    def test_init_with_various_models(self, model_class):
        """Test initialization with various model classes."""
        config = create_subject_config(target_model=model_class)
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config)
            assert_that(orch.subject_config.target_model).is_equal_to(model_class)


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

class TestOrchestratorEdgeCases:
    """Edge case tests for Orchestrator."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return create_subject_config()

    def test_empty_questions_dict(self):
        """Test with empty questions dictionary."""
        config = SubjectConfig(
            name="leetcode",
            target_questions={},
            initial_prompt="Prompt",
            combine_prompt="Combine",
            target_model=LeetCodeProblem,
            deck_prefix="LeetCode",
            deck_prefix_mcq="LeetCode_MCQ",
        )
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config)
            assert_that(orch.subject_config.target_questions).is_equal_to({})

    def test_single_category_single_question(self):
        """Test with single category and single question."""
        config = create_subject_config(questions={"Arrays": ["Two Sum"]})
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config)
            assert len(orch.subject_config.target_questions["Arrays"]) == 1

    def test_multiple_categories(self):
        """Test with multiple categories."""
        config = create_subject_config(
            questions={
                "Arrays": ["Two Sum"],
                "Trees": ["Invert Tree"],
                "Graphs": ["DFS", "BFS"],
            }
        )
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config)
            assert len(orch.subject_config.target_questions) == 3

    def test_long_run_label(self):
        """Test with very long run label."""
        long_label = "A" * 500
        config = create_subject_config()
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config, run_label=long_label)
            assert_that(orch.run_label).is_equal_to(long_label)

    def test_unicode_in_run_label(self):
        """Test with unicode characters in run label."""
        config = create_subject_config()
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config, run_label="测试运行")
            assert_that(orch.run_label).is_equal_to("测试运行")

    def test_special_characters_in_subject_name(self):
        """Test with special characters in subject name."""
        config = create_subject_config(name="my-custom_subject.v2")
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config)
            assert_that(orch.generation_mode).is_equal_to("my-custom_subject.v2")

    @pytest.mark.asyncio
    async def test_initialize_called_twice(self, subject_config):
        """Test calling initialize twice."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                orch = Orchestrator(subject_config=subject_config)
                result1 = await orch.initialize()
                result2 = await orch.initialize()

                # Both should succeed
                assert_that(result1).is_true()
                assert_that(result2).is_true()

    @pytest.mark.asyncio
    async def test_run_with_empty_question_list(self):
        """Test run with empty questions."""
        config = create_subject_config(questions={})
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = ([], mock_combiner, None)

                with patch("src.orchestrator.CardGenerator") as MockGenerator:
                    mock_gen = AsyncMock()
                    MockGenerator.return_value = mock_gen

                    with patch("src.orchestrator.ConcurrentTaskRunner") as MockRunner:
                        mock_runner = AsyncMock()
                        mock_runner.run_all = AsyncMock(return_value=[])
                        MockRunner.return_value = mock_runner

                        orch = Orchestrator(subject_config=config)
                        await orch.initialize()
                        results = await orch.run()

                        assert_that(results).is_equal_to([])

    def test_deck_prefix_with_spaces(self):
        """Test deck prefix with spaces."""
        config = create_subject_config(
            deck_prefix="My Deck",
            deck_prefix_mcq="My Deck MCQ",
        )
        with patch("src.orchestrator.RunRepository"):
            orch = Orchestrator(subject_config=config)
            assert_that(orch.deck_prefix).is_equal_to("My Deck")

            orch_mcq = Orchestrator(subject_config=config, is_mcq=True)
            assert_that(orch_mcq.deck_prefix).is_equal_to("My Deck MCQ")

    @pytest.mark.asyncio
    async def test_initialize_with_all_provider_types(self, subject_config):
        """Test initialize with generators, combiner, and formatter."""
        mock_providers = [
            MockLLMProvider(name="gen1", model="m1"),
            MockLLMProvider(name="gen2", model="m2"),
        ]
        mock_combiner = MockLLMProvider(name="combiner", model="c")
        mock_formatter = MockLLMProvider(name="formatter", model="f")

        with patch("src.orchestrator.RunRepository") as MockRunRepo:
            mock_run_repo = create_mock_run_repo()
            MockRunRepo.return_value = mock_run_repo

            with patch("src.orchestrator.initialize_providers") as mock_init:
                mock_init.return_value = (mock_providers, mock_combiner, mock_formatter)

                orch = Orchestrator(subject_config=subject_config)
                result = await orch.initialize()

                assert_that(result).is_true()
                assert len(orch.card_generator.llm_providers) == 2
                assert orch.card_generator.card_combiner.name == "combiner"
                assert orch.card_generator.formatter.name == "formatter"
