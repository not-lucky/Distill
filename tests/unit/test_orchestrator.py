"""Tests for Orchestrator in src/orchestrator.py."""

import json
import pytest

from assertpy import assert_that
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call, ANY

from src.orchestrator import Orchestrator
from src.config.subjects import SubjectConfig
from src.models import LeetCodeProblem, CSProblem, PhysicsProblem
from src.task_runner import Success, Failure
from src.database import DatabaseManager

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


class TestOrchestrator:
    """Tests for Orchestrator class."""

    @pytest.fixture
    def subject_config(self):
        """Create a sample SubjectConfig."""
        return create_subject_config()

    @pytest.fixture
    def orchestrator(self, subject_config, in_memory_db):
        """Create an Orchestrator instance."""
        # Use patch for load_config to avoid reading file
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 1
            mock_config.return_value.generation.request_delay = 0

            with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
                # Mock DatabaseManager.get_default to return our in_memory_db
                with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                    orch = Orchestrator(
                        subject_config=subject_config,
                        is_mcq=False,
                        run_label="test",
                    )
                    orch.db_manager = in_memory_db
                    return orch

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_init_stores_subject_config(self, subject_config):
        """Test that subject_config is stored correctly."""
        orch = Orchestrator(subject_config=subject_config)
        assert_that(orch.subject_config).is_equal_to(subject_config)

    def test_init_stores_is_mcq(self, subject_config):
        """Test that is_mcq is stored correctly."""
        orch = Orchestrator(subject_config=subject_config, is_mcq=True)
        assert_that(orch.is_mcq).is_true()

    def test_init_is_mcq_defaults_false(self, subject_config):
        """Test that is_mcq defaults to False."""
        orch = Orchestrator(subject_config=subject_config)
        assert_that(orch.is_mcq).is_false()

    def test_init_stores_run_label(self, subject_config):
        """Test that run_label is stored correctly."""
        orch = Orchestrator(
            subject_config=subject_config,
            run_label="my-test-label",
        )
        assert_that(orch.run_label).is_equal_to("my-test-label")

    def test_init_run_label_defaults_none(self, subject_config):
        """Test that run_label defaults to None."""
        orch = Orchestrator(subject_config=subject_config)
        assert_that(orch.run_label).is_none()

    def test_init_stores_dry_run(self, subject_config):
        """Test that dry_run is stored correctly."""
        orch = Orchestrator(
            subject_config=subject_config,
            dry_run=True,
        )
        assert_that(orch.dry_run).is_true()

    def test_init_dry_run_defaults_false(self, subject_config):
        """Test that dry_run defaults to False."""
        orch = Orchestrator(subject_config=subject_config)
        assert_that(orch.dry_run).is_false()

    def test_init_card_generator_starts_none(self, subject_config):
        """Test that card_generator starts as None."""
        orch = Orchestrator(subject_config=subject_config)
        assert_that(orch.card_generator).is_none()

    def test_init_loads_config_settings(self, subject_config):
        """Test that config settings are loaded."""
        with patch("src.orchestrator.load_config") as mock_config:
            mock_config.return_value.generation.concurrent_requests = 10
            mock_config.return_value.generation.request_delay = 0.5

            orch = Orchestrator(subject_config=subject_config)
            assert orch.concurrent_requests == 10
            assert orch.request_delay == 0.5

    # -------------------------------------------------------------------------
    # Property Tests
    # -------------------------------------------------------------------------

    def test_run_id_property(self, orchestrator):
        """Test run_id property returns internal _run_id."""
        orchestrator._run_id = "test-123"
        assert_that(orchestrator.run_id).is_equal_to("test-123")

    def test_run_id_property_none(self, orchestrator):
        """Test run_id property when None."""
        orchestrator._run_id = None
        assert_that(orchestrator.run_id).is_none()

    def test_generation_mode_standard(self, orchestrator):
        """Test generation_mode for standard mode."""
        assert_that(orchestrator.generation_mode).is_equal_to("leetcode")

    def test_generation_mode_mcq(self, subject_config):
        """Test generation_mode for MCQ mode."""
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
        orch = Orchestrator(subject_config=config, is_mcq=is_mcq)
        assert_that(orch.generation_mode).is_equal_to(expected)

    def test_deck_prefix_standard(self, orchestrator):
        """Test deck_prefix for standard mode."""
        assert_that(orchestrator.deck_prefix).is_equal_to("LeetCode")

    def test_deck_prefix_mcq(self, subject_config):
        """Test deck_prefix for MCQ mode."""
        orch = Orchestrator(subject_config=subject_config, is_mcq=True)
        assert_that(orch.deck_prefix).is_equal_to("LeetCode_MCQ")

    @pytest.mark.parametrize("is_mcq,expected", [
        (False, "LeetCode"),
        (True, "LeetCode_MCQ"),
    ])
    def test_deck_prefix_by_mode(self, subject_config, is_mcq, expected):
        """Test deck_prefix by mode."""
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

        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                with patch("src.orchestrator.initialize_providers") as mock_init:
                    mock_init.return_value = (mock_providers, mock_combiner, None)

                    orch = Orchestrator(subject_config=subject_config)
                    result = await orch.initialize()

                    assert_that(result).is_true()
                    assert_that(orch.card_generator).is_not_none()
                    assert_that(orch.run_id).is_not_none()

    @pytest.mark.asyncio
    async def test_initialize_creates_run(self, subject_config, in_memory_db):
        """Test that initialize creates a run."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                with patch("src.orchestrator.initialize_providers") as mock_init:
                    mock_init.return_value = ([], mock_combiner, None)

                    orch = Orchestrator(subject_config=subject_config)

                    # Spy on create_run
                    with patch("src.orchestrator.create_run") as mock_create_run:
                        await orch.initialize()
                        mock_create_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_with_formatter(self, subject_config, in_memory_db):
        """Test initialization with formatter provider."""
        mock_providers = [MockLLMProvider(name="gen", model="m")]
        mock_combiner = MockLLMProvider(name="combiner", model="c")
        mock_formatter = MockLLMProvider(name="formatter", model="f")

        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
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
    async def test_initialize_uses_first_provider_as_combiner(self, subject_config, in_memory_db):
        """Test that first provider is used as combiner if none specified."""
        mock_providers = [
            MockLLMProvider(name="first", model="m1"),
            MockLLMProvider(name="second", model="m2"),
        ]

        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
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
    async def test_initialize_single_provider_becomes_combiner(self, subject_config, in_memory_db):
        """Test single provider becomes combiner with empty generators."""
        mock_providers = [MockLLMProvider(name="single", model="m")]

        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
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
    async def test_initialize_no_providers(self, subject_config, in_memory_db):
        """Test initialization with no providers fails."""
        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                with patch("src.orchestrator.initialize_providers") as mock_init:
                    mock_init.return_value = ([], None, None)

                    orch = Orchestrator(subject_config=subject_config)

                    with patch("src.orchestrator.update_run") as mock_update_run:
                        result = await orch.initialize()

                        assert_that(result).is_false()
                        # Should update run status to failed
                        mock_update_run.assert_called_with(
                            ANY,
                            orch.run_id,
                            status="failed"
                        )

    @pytest.mark.asyncio
    async def test_initialize_marks_failed_when_no_combiner(self, subject_config, in_memory_db):
        """Test run is marked failed when no combiner available."""
        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                with patch("src.orchestrator.initialize_providers") as mock_init:
                    mock_init.return_value = ([], None, None)

                    orch = Orchestrator(subject_config=subject_config)

                    with patch("src.orchestrator.update_run") as mock_update_run:
                        await orch.initialize()
                        mock_update_run.assert_called()

    # -------------------------------------------------------------------------
    # Dry Run Mode
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_initialize_dry_run(self, subject_config):
        """Test initialization in dry run mode."""
        mock_providers = [MockLLMProvider()]
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.initialize_providers") as mock_init:
            mock_init.return_value = (mock_providers, mock_combiner, None)

            orch = Orchestrator(subject_config=subject_config, dry_run=True)
            result = await orch.initialize()

            assert_that(result).is_true()
            # Run ID should be None in dry run
            assert orch.run_id is None

    @pytest.mark.asyncio
    async def test_initialize_dry_run_skips_database(self, subject_config):
        """Test dry run skips database initialization."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.initialize_providers") as mock_init:
            mock_init.return_value = ([], mock_combiner, None)

            orch = Orchestrator(subject_config=subject_config, dry_run=True)

            with patch("src.orchestrator.create_run") as mock_create_run:
                await orch.initialize()
                mock_create_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_dry_run_no_provider_doesnt_mark_failed(self, subject_config):
        """Test dry run doesn't mark run failed when no providers."""
        with patch("src.orchestrator.initialize_providers") as mock_init:
            mock_init.return_value = ([], None, None)

            orch = Orchestrator(subject_config=subject_config, dry_run=True)

            with patch("src.orchestrator.update_run") as mock_update_run:
                await orch.initialize()
                mock_update_run.assert_not_called()

    # -------------------------------------------------------------------------
    # Card Generator Configuration
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_initialize_sets_combine_prompt(self, subject_config, in_memory_db):
        """Test that combine_prompt is passed to CardGenerator."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                with patch("src.orchestrator.initialize_providers") as mock_init:
                    mock_init.return_value = ([], mock_combiner, None)

                    orch = Orchestrator(subject_config=subject_config)
                    await orch.initialize()

                    assert_that(orch.card_generator.combine_prompt).is_equal_to(subject_config.combine_prompt)

    @pytest.mark.asyncio
    async def test_initialize_sets_dry_run_on_generator(self, subject_config):
        """Test that dry_run is passed to CardGenerator."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

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

    # -------------------------------------------------------------------------
    # Error Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_run_not_initialized(self, subject_config):
        """Test run raises error if not initialized."""
        orch = Orchestrator(subject_config=subject_config)

        with pytest.raises(RuntimeError, match="not initialized"):
            await orch.run()

    @pytest.mark.asyncio
    async def test_run_card_generator_none_raises(self, subject_config):
        """Test run raises when card_generator is None."""
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

        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
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
    async def test_run_returns_successful_results(self, subject_config, in_memory_db):
        """Test run returns only successful results."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
                with patch("src.orchestrator.initialize_providers") as mock_init:
                    mock_init.return_value = ([], mock_combiner, None)

                    with patch("src.orchestrator.CardGenerator") as MockGenerator:
                        mock_gen = AsyncMock()
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
    async def test_run_marks_completed(self, subject_config, in_memory_db):
        """Test run marks run as completed."""
        mock_combiner = MockLLMProvider(name="combiner", model="c")

        with patch("src.orchestrator.DATABASE_PATH", ":memory:"):
            with patch("src.database.DatabaseManager.get_default", return_value=in_memory_db):
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

                            with patch("src.orchestrator.update_run") as mock_update_run:
                                await orch.initialize()
                                await orch.run()

                                mock_update_run.assert_called()
                                assert mock_update_run.call_args[1]["status"] == "completed"


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

    def test_save_results_empty(self, subject_config):
        """Test saving empty results returns None."""
        orch = Orchestrator(subject_config=subject_config)
        result = orch.save_results([])
        assert_that(result).is_none()

    def test_save_results_dry_run(self, subject_config):
        """Test saving results in dry run mode."""
        orch = Orchestrator(subject_config=subject_config, dry_run=True)
        result = orch.save_results([{"title": "Test"}])
        assert_that(result).is_equal_to("leetcode_anki_deck")

    def test_save_results_success(self, subject_config, tmp_path, monkeypatch):
        """Test saving results creates file."""
        monkeypatch.chdir(tmp_path)

        orch = Orchestrator(subject_config=subject_config)
        orch._run_id = "test-run"

        problems = [
            {"title": "Problem 1", "cards": []},
            {"title": "Problem 2", "cards": []},
        ]

        result = orch.save_results(problems)

        assert_that(result).is_equal_to("leetcode_anki_deck")
        # Verify file was created
        json_files = list(tmp_path.glob("leetcode_anki_deck_*.json"))
        assert_that(json_files).is_length(1)
