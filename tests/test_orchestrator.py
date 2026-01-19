"""Unit tests for Orchestrator."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestOrchestratorProperties:
    """Test Orchestrator property methods."""

    @pytest.fixture
    def orchestrator(self, single_question_config, tmp_path):
        """Create an Orchestrator with a temp database."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            return Orchestrator(
                subject_config=single_question_config,
                is_mcq=False,
                run_label="test-label",
            )

    def test_generation_mode_standard(self, single_question_config, tmp_path):
        """Test generation_mode for standard cards."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=False)
            assert orch.generation_mode == "leetcode"

    def test_generation_mode_mcq(self, single_question_config, tmp_path):
        """Test generation_mode for MCQ cards."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=True)
            assert orch.generation_mode == "leetcode_mcq"

    def test_deck_prefix_standard(self, single_question_config, tmp_path):
        """Test deck_prefix for standard cards."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=False)
            assert orch.deck_prefix == single_question_config.deck_prefix

    def test_deck_prefix_mcq(self, single_question_config, tmp_path):
        """Test deck_prefix for MCQ cards."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=True)
            assert orch.deck_prefix == single_question_config.deck_prefix_mcq

    def test_run_id_before_initialize(self, orchestrator):
        """Test run_id is None before initialization."""
        assert orchestrator.run_id is None


class TestOrchestratorInitialize:
    """Test Orchestrator.initialize() method."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, single_question_config, tmp_path, mock_provider):
        """Test successful initialization."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=False)

            with patch("src.orchestrator.initialize_providers", new_callable=AsyncMock) as mock_init:
                mock_init.return_value = [mock_provider, mock_provider]

                result = await orch.initialize()

                assert result is True
                assert orch.run_id is not None
                assert orch.card_generator is not None
                mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_no_providers_fails(self, single_question_config, tmp_path):
        """Test initialization fails when no providers available."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=False)

            with patch("src.orchestrator.initialize_providers", new_callable=AsyncMock) as mock_init:
                mock_init.return_value = []

                result = await orch.initialize()

                assert result is False
                assert orch.card_generator is None


class TestOrchestratorRun:
    """Test Orchestrator.run() method."""

    @pytest.mark.asyncio
    async def test_run_without_initialize_raises(self, single_question_config, tmp_path):
        """Test that run() raises RuntimeError if not initialized."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=False)

            with pytest.raises(RuntimeError, match="not initialized"):
                await orch.run()

    @pytest.mark.asyncio
    async def test_run_processes_questions(self, single_question_config, tmp_path, mock_provider, sample_card_dict):
        """Test that run() processes all questions."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=False)

            # Setup mock generator
            mock_generator = MagicMock()
            mock_generator.process_question = AsyncMock(return_value=sample_card_dict)

            with patch("src.orchestrator.initialize_providers", new_callable=AsyncMock) as mock_init:
                mock_init.return_value = [mock_provider, mock_provider]
                await orch.initialize()

                # Replace generator with mock
                orch.card_generator = mock_generator

                problems = await orch.run()

                # Should have processed questions
                assert len(problems) == 1
                mock_generator.process_question.assert_called()


class TestOrchestratorSaveResults:
    """Test Orchestrator.save_results() method."""

    def test_save_results_with_problems(self, single_question_config, tmp_path, sample_card_dict):
        """Test save_results with problems returns filename."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=False)

            with patch("src.orchestrator.save_final_deck") as mock_save:
                result = orch.save_results([sample_card_dict])

                assert result is not None
                assert "leetcode" in result
                mock_save.assert_called_once()

    def test_save_results_empty_returns_none(self, single_question_config, tmp_path):
        """Test save_results with no problems returns None."""
        from src.orchestrator import Orchestrator

        with patch("src.orchestrator.DATABASE_PATH", str(tmp_path / "test.db")):
            orch = Orchestrator(subject_config=single_question_config, is_mcq=False)

            with patch("src.orchestrator.save_final_deck") as mock_save:
                result = orch.save_results([])

                assert result is None
                mock_save.assert_not_called()
