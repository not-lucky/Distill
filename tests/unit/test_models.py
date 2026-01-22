"""Tests for Pydantic models in src/models.py."""

import pytest
from pydantic import ValidationError

from src.models import (
    AnkiCard,
    BaseProblem,
    LeetCodeProblem,
    CSProblem,
    PhysicsProblem,
    MCQCard,
    MCQProblem,
    GenericProblem,
)


class TestAnkiCard:
    """Tests for AnkiCard model."""

    def test_valid_anki_card(self):
        """Test creating a valid AnkiCard."""
        card = AnkiCard(
            card_type="Concept",
            tags=["Tag1", "Tag2"],
            front="What is X?",
            back="X is Y."
        )
        assert card.card_type == "Concept"
        assert card.tags == ["Tag1", "Tag2"]
        assert card.front == "What is X?"
        assert card.back == "X is Y."

    def test_anki_card_required_fields(self):
        """Test that required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError) as exc_info:
            AnkiCard(card_type="Concept", tags=["Tag1"])
        assert "front" in str(exc_info.value) or "back" in str(exc_info.value)

    def test_anki_card_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            AnkiCard(
                card_type="Concept",
                tags=["Tag1"],
                front="Q",
                back="A",
                extra_field="not allowed"
            )
        assert "extra" in str(exc_info.value).lower()

    def test_anki_card_empty_tags(self):
        """Test AnkiCard with empty tags list."""
        card = AnkiCard(
            card_type="Basic",
            tags=[],
            front="Q",
            back="A"
        )
        assert card.tags == []


class TestLeetCodeProblem:
    """Tests for LeetCodeProblem model."""

    def test_valid_leetcode_problem(self):
        """Test creating a valid LeetCodeProblem."""
        problem = LeetCodeProblem(
            title="Two Sum",
            topic="Arrays",
            difficulty="Easy",
            cards=[
                AnkiCard(
                    card_type="Algorithm",
                    tags=["HashTable"],
                    front="How to solve Two Sum?",
                    back="Use a hash map."
                )
            ]
        )
        assert problem.title == "Two Sum"
        assert problem.topic == "Arrays"
        assert problem.difficulty == "Easy"
        assert len(problem.cards) == 1

    def test_leetcode_problem_multiple_cards(self):
        """Test LeetCodeProblem with multiple cards."""
        problem = LeetCodeProblem(
            title="Binary Search",
            topic="Binary Search",
            difficulty="Medium",
            cards=[
                AnkiCard(card_type="Concept", tags=[], front="Q1", back="A1"),
                AnkiCard(card_type="Code", tags=[], front="Q2", back="A2"),
            ]
        )
        assert len(problem.cards) == 2

    def test_leetcode_problem_required_fields(self):
        """Test that required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError):
            LeetCodeProblem(title="Test", topic="Test")

    def test_leetcode_problem_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            LeetCodeProblem(
                title="Test",
                topic="Test",
                difficulty="Easy",
                cards=[],
                unknown_field="value"
            )


class TestCSProblem:
    """Tests for CSProblem model."""

    def test_valid_cs_problem(self):
        """Test creating a valid CSProblem."""
        problem = CSProblem(
            title="Process Scheduling",
            topic="Operating Systems",
            difficulty="Intermediate",
            cards=[
                AnkiCard(
                    card_type="Concept",
                    tags=["OS"],
                    front="What is FCFS?",
                    back="First Come First Served scheduling."
                )
            ]
        )
        assert problem.title == "Process Scheduling"
        assert problem.topic == "Operating Systems"
        assert problem.difficulty == "Intermediate"


class TestPhysicsProblem:
    """Tests for PhysicsProblem model."""

    def test_valid_physics_problem(self):
        """Test creating a valid PhysicsProblem."""
        problem = PhysicsProblem(
            title="Newton's Laws",
            topic="Mechanics",
            difficulty="Basic",
            cards=[
                AnkiCard(
                    card_type="Law",
                    tags=["Mechanics"],
                    front="What is Newton's First Law?",
                    back="An object at rest stays at rest..."
                )
            ]
        )
        assert problem.title == "Newton's Laws"
        assert problem.topic == "Mechanics"


class TestMCQCard:
    """Tests for MCQCard model."""

    def test_valid_mcq_card(self):
        """Test creating a valid MCQCard."""
        card = MCQCard(
            card_type="Concept",
            tags=["Algorithm"],
            question="What is the time complexity of binary search?",
            options=["O(n)", "O(log n)", "O(n^2)", "O(1)"],
            correct_answer="B",
            explanation="Binary search divides the search space in half."
        )
        assert card.card_type == "Concept"
        assert card.question == "What is the time complexity of binary search?"
        assert len(card.options) == 4
        assert card.correct_answer == "B"

    def test_mcq_card_required_fields(self):
        """Test that required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError):
            MCQCard(
                card_type="Concept",
                tags=[],
                question="Q?",
                options=["A", "B", "C", "D"]
                # Missing correct_answer and explanation
            )

    def test_mcq_card_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            MCQCard(
                card_type="Concept",
                tags=[],
                question="Q?",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Exp",
                extra="not allowed"
            )


class TestMCQProblem:
    """Tests for MCQProblem model."""

    def test_valid_mcq_problem(self):
        """Test creating a valid MCQProblem."""
        problem = MCQProblem(
            title="Data Structures MCQ",
            topic="Arrays",
            difficulty="Medium",
            cards=[
                MCQCard(
                    card_type="Concept",
                    tags=["Array"],
                    question="What is an array?",
                    options=[
                        "A linear data structure",
                        "A tree structure",
                        "A graph",
                        "A hash table"
                    ],
                    correct_answer="A",
                    explanation="An array is a linear data structure."
                )
            ]
        )
        assert problem.title == "Data Structures MCQ"
        assert len(problem.cards) == 1
        assert problem.cards[0].correct_answer == "A"


class TestGenericProblem:
    """Tests for GenericProblem model."""

    def test_valid_generic_problem(self):
        """Test creating a valid GenericProblem."""
        problem = GenericProblem(
            title="Custom Topic",
            topic="Custom Category",
            difficulty="Advanced",
            cards=[
                AnkiCard(
                    card_type="Custom",
                    tags=["Custom"],
                    front="Custom question?",
                    back="Custom answer."
                )
            ]
        )
        assert problem.title == "Custom Topic"
        assert problem.topic == "Custom Category"

    def test_generic_problem_inherits_base(self):
        """Test that GenericProblem inherits from BaseProblem."""
        assert issubclass(GenericProblem, BaseProblem)


class TestBaseProblem:
    """Tests for BaseProblem model."""

    def test_base_problem_is_abstract_like(self):
        """Test that BaseProblem can be instantiated (it's not truly abstract)."""
        # BaseProblem is not abstract in Pydantic, but serves as base class
        problem = BaseProblem(
            title="Test",
            topic="Test",
            difficulty="Easy",
            cards=[]
        )
        assert problem.title == "Test"

    def test_base_problem_empty_cards(self):
        """Test BaseProblem with empty cards list."""
        problem = BaseProblem(
            title="Test",
            topic="Test",
            difficulty="Easy",
            cards=[]
        )
        assert problem.cards == []
