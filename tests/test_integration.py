"""Integration tests for LLM2Deck.

These tests require real API keys and make actual API calls.
Run with: pytest tests/test_integration.py -v -m integration
"""

import pytest
import itertools


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_generation_pipeline():
    """
    Integration test: Generate cards for 1 question using Cerebras.

    Setup:
    - 2 CerebrasProvider instances (same model: gpt-oss-120b) for parallel generation
    - 1 CerebrasProvider instance (same model) for combining
    - 1 question from leetcode subject ("Min Stack")
    """
    from src.config.keys import load_keys
    from src.providers.cerebras import CerebrasProvider
    from src.generator import CardGenerator
    from src.config.subjects import SubjectRegistry
    from src.database import init_database, get_session, create_problem, update_problem
    from unittest.mock import patch, MagicMock

    # Load real keys
    keys = await load_keys("cerebras")
    assert keys, "Cerebras API keys required for integration test. Add keys to cerebras_keys.json"

    key_cycle = itertools.cycle(keys)

    # Create 2 providers for generation + 1 for combining (all use same model)
    provider1 = CerebrasProvider(api_keys=key_cycle, model="gpt-oss-120b")
    provider2 = CerebrasProvider(api_keys=key_cycle, model="gpt-oss-120b")
    combiner = CerebrasProvider(api_keys=key_cycle, model="gpt-oss-120b")

    # Get config for leetcode
    subject_config = SubjectRegistry.get_config("leetcode", is_multiple_choice=False)

    # Create generator
    generator = CardGenerator(
        providers=[provider1, provider2],
        combiner=combiner,
        combine_prompt=subject_config.combine_prompt,
        run_id="integration-test-run",
    )

    # Mock database operations to avoid side effects
    with patch("src.generator.get_session") as mock_session:
        mock_session.return_value = MagicMock()

        with patch("src.generator.create_problem") as mock_create_problem:
            mock_problem = MagicMock()
            mock_problem.id = "test-problem-id"
            mock_create_problem.return_value = mock_problem

            with patch("src.generator.create_provider_result"):
                with patch("src.generator.update_problem"):
                    with patch("src.generator.create_cards"):
                        # Process single question
                        result = await generator.process_question(
                            question="Min Stack",
                            prompt_template=subject_config.initial_prompt,
                            model_class=subject_config.target_model,
                            category_index=1,
                            category_name="Stacks",
                            problem_index=1,
                        )

    # Assertions
    assert result is not None, "Result should not be None"
    assert "cards" in result, "Result should contain 'cards' key"
    assert len(result["cards"]) > 0, "Should generate at least one card"

    # Verify card structure
    for card in result["cards"]:
        # Cards should have either front/back (standard) or question/explanation (MCQ)
        has_front_back = "front" in card and "back" in card
        has_question_explanation = "question" in card and "explanation" in card
        assert has_front_back or has_question_explanation, (
            f"Card should have front/back or question/explanation: {card.keys()}"
        )

        # Cards should have card_type
        assert "card_type" in card, "Card should have card_type"

        # Cards should have tags (list)
        if "tags" in card:
            assert isinstance(card["tags"], list), "Tags should be a list"

    # Verify metadata
    assert result.get("category_index") == 1
    assert result.get("category_name") == "Stacks"
    assert result.get("problem_index") == 1

    print(f"\n✓ Integration test passed!")
    print(f"  Generated {len(result['cards'])} cards for 'Min Stack'")
    print(f"  Card types: {[c.get('card_type') for c in result['cards']]}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_generation_only():
    """
    Integration test: Test that a single provider can generate initial cards.

    This is a simpler test that only tests the generation step.
    Note: generate_initial_cards returns raw output - valid JSON is not
    guaranteed on a single call. The combiner handles JSON validation/retry.
    """
    from src.config.keys import load_keys
    from src.providers.cerebras import CerebrasProvider
    from src.models import LeetCodeProblem

    # Load real keys
    keys = await load_keys("cerebras")
    assert keys, "Cerebras API keys required for integration test"

    key_cycle = itertools.cycle(keys)
    provider = CerebrasProvider(api_keys=key_cycle, model="gpt-oss-120b")

    # Generate cards
    result = await provider.generate_initial_cards(
        question="Min Stack",
        json_schema=LeetCodeProblem.model_json_schema(),
        prompt_template=None  # Use default prompt
    )

    # Verify we got a response (JSON validity is not guaranteed on single call)
    assert result is not None, "Should get a response"
    assert len(result) > 0, "Response should not be empty"

    # Check that response looks like JSON (starts with { or [)
    # Full JSON validation happens in combine_cards with retry logic
    stripped = result.strip()
    assert stripped.startswith("{") or stripped.startswith("["), (
        "Response should look like JSON"
    )

    # Try to parse - log result but don't fail on parse errors
    import json
    try:
        parsed = json.loads(result)
        print(f"\n✓ Single provider generation passed!")
        print(f"  Generated {len(parsed.get('cards', []))} cards")
    except json.JSONDecodeError:
        # This is expected sometimes - raw generation doesn't guarantee valid JSON
        print(f"\n✓ Single provider generation passed (got response, JSON incomplete)")
        print(f"  Response length: {len(result)} chars")

