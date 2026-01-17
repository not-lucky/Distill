"""Unit tests for CardGenerator."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestCardGenerator:
    """Tests for CardGenerator class."""

    @pytest.fixture
    def mock_providers(self, sample_card_json):
        """Create list of mock providers."""
        provider1 = MagicMock()
        provider1.name = "provider1"
        provider1.model = "model1"
        provider1.generate_initial_cards = AsyncMock(return_value=sample_card_json)

        provider2 = MagicMock()
        provider2.name = "provider2"
        provider2.model = "model2"
        provider2.generate_initial_cards = AsyncMock(return_value=sample_card_json)

        return [provider1, provider2]

    @pytest.fixture
    def mock_combiner(self, sample_card_dict):
        """Create mock combiner provider."""
        combiner = MagicMock()
        combiner.name = "combiner"
        combiner.model = "combiner-model"
        combiner.combine_cards = AsyncMock(return_value=sample_card_dict)
        return combiner

    @pytest.fixture
    def card_generator(self, mock_providers, mock_combiner):
        """Create CardGenerator with mocked providers."""
        from src.generator import CardGenerator
        return CardGenerator(
            providers=mock_providers,
            combiner=mock_combiner,
            combine_prompt="Test combine prompt",
            run_id="test-run-id"
        )

    @pytest.mark.asyncio
    async def test_process_question_calls_all_providers(
        self, card_generator, mock_providers, temp_database
    ):
        """Test that process_question calls all providers in parallel."""
        with patch("src.generator.get_session") as mock_session:
            mock_session.return_value = MagicMock()

            with patch("src.generator.create_problem") as mock_create:
                mock_problem = MagicMock()
                mock_problem.id = "test-problem-id"
                mock_create.return_value = mock_problem

                with patch("src.generator.create_provider_result"):
                    with patch("src.generator.update_problem"):
                        with patch("src.generator.create_cards"):
                            from src.models import LeetCodeProblem

                            result = await card_generator.process_question(
                                question="Min Stack",
                                prompt_template=None,
                                model_class=LeetCodeProblem,
                                category_index=1,
                                category_name="Stacks",
                                problem_index=1
                            )

        # Both providers should have been called
        for provider in mock_providers:
            provider.generate_initial_cards.assert_called_once()

        assert result is not None

    @pytest.mark.asyncio
    async def test_process_question_all_providers_fail(self, mock_combiner, temp_database):
        """Test behavior when all providers fail."""
        from src.generator import CardGenerator

        # Create providers that return None/empty
        failing_provider1 = MagicMock()
        failing_provider1.name = "failing1"
        failing_provider1.model = "model1"
        failing_provider1.generate_initial_cards = AsyncMock(return_value=None)

        failing_provider2 = MagicMock()
        failing_provider2.name = "failing2"
        failing_provider2.model = "model2"
        failing_provider2.generate_initial_cards = AsyncMock(return_value="")

        generator = CardGenerator(
            providers=[failing_provider1, failing_provider2],
            combiner=mock_combiner,
            run_id="test-run-id"
        )

        with patch("src.generator.get_session") as mock_session:
            mock_session.return_value = MagicMock()

            with patch("src.generator.create_problem") as mock_create:
                mock_problem = MagicMock()
                mock_problem.id = "test-problem-id"
                mock_create.return_value = mock_problem

                with patch("src.generator.update_problem"):
                    from src.models import LeetCodeProblem

                    result = await generator.process_question(
                        question="Test",
                        model_class=LeetCodeProblem
                    )

        # Should return None when all providers fail
        assert result is None
        # Combiner should not be called
        mock_combiner.combine_cards.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_question_combination_succeeds(
        self, card_generator, mock_combiner, sample_card_dict, temp_database
    ):
        """Test that combination produces expected output."""
        with patch("src.generator.get_session") as mock_session:
            mock_session.return_value = MagicMock()

            with patch("src.generator.create_problem") as mock_create:
                mock_problem = MagicMock()
                mock_problem.id = "test-problem-id"
                mock_create.return_value = mock_problem

                with patch("src.generator.create_provider_result"):
                    with patch("src.generator.update_problem"):
                        with patch("src.generator.create_cards"):
                            from src.models import LeetCodeProblem

                            result = await card_generator.process_question(
                                question="Min Stack",
                                model_class=LeetCodeProblem,
                                category_index=1,
                                category_name="Stacks",
                                problem_index=1
                            )

        # Combiner should be called
        mock_combiner.combine_cards.assert_called_once()

        # Result should have cards
        assert result is not None
        assert "cards" in result

        # Should have category metadata
        assert result.get("category_index") == 1
        assert result.get("category_name") == "Stacks"
        assert result.get("problem_index") == 1


class TestCardGeneratorInitialization:
    """Test CardGenerator initialization."""

    def test_generator_stores_providers(self, mock_provider):
        """Test that generator stores providers correctly."""
        from src.generator import CardGenerator

        generator = CardGenerator(
            providers=[mock_provider],
            combiner=mock_provider,
            run_id="test"
        )

        assert len(generator.llm_providers) == 1
        assert generator.card_combiner == mock_provider

    def test_generator_stores_combine_prompt(self, mock_provider):
        """Test that generator stores combine prompt."""
        from src.generator import CardGenerator

        generator = CardGenerator(
            providers=[mock_provider],
            combiner=mock_provider,
            combine_prompt="Custom prompt",
            run_id="test"
        )

        assert generator.combine_prompt == "Custom prompt"
