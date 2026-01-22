"""Tests for Pydantic models in src/models.py."""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
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


# Custom Hypothesis Strategies
@composite
def valid_card_types(draw):
    """Generate valid card type strings."""
    types = ["Concept", "Code", "Algorithm", "Intuition", "EdgeCase", "Pattern", "Implementation"]
    return draw(st.sampled_from(types))


@composite
def valid_tags(draw):
    """Generate valid tag lists."""
    tag_chars = st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
        min_size=1,
        max_size=20
    )
    return draw(st.lists(tag_chars, min_size=0, max_size=5))


@composite
def valid_anki_cards(draw):
    """Generate valid AnkiCard instances."""
    return AnkiCard(
        card_type=draw(valid_card_types()),
        tags=draw(valid_tags()),
        front=draw(st.text(min_size=1, max_size=500)),
        back=draw(st.text(min_size=1, max_size=500)),
    )


@composite
def valid_mcq_cards(draw):
    """Generate valid MCQCard instances."""
    return MCQCard(
        card_type=draw(valid_card_types()),
        tags=draw(valid_tags()),
        question=draw(st.text(min_size=1, max_size=500)),
        options=draw(st.lists(st.text(min_size=1, max_size=100), min_size=4, max_size=4)),
        correct_answer=draw(st.sampled_from(["A", "B", "C", "D"])),
        explanation=draw(st.text(min_size=1, max_size=500)),
    )


@composite
def valid_difficulty_levels(draw):
    """Generate valid difficulty level strings."""
    return draw(st.sampled_from(["Easy", "Medium", "Hard", "Basic", "Intermediate", "Advanced"]))


class TestAnkiCardPropertyBased:
    """Property-based tests for AnkiCard model."""

    @given(
        card_type=st.text(min_size=1, max_size=50),
        front=st.text(min_size=1, max_size=1000),
        back=st.text(min_size=1, max_size=1000),
    )
    @settings(max_examples=50)
    def test_anki_card_accepts_any_strings(self, card_type, front, back):
        """Test that AnkiCard accepts any non-empty strings."""
        card = AnkiCard(
            card_type=card_type,
            tags=[],
            front=front,
            back=back,
        )
        assert card.card_type == card_type
        assert card.front == front
        assert card.back == back

    @given(tags=st.lists(st.text(min_size=1, max_size=30), min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_anki_card_accepts_any_tags(self, tags):
        """Test that AnkiCard accepts any list of tags."""
        card = AnkiCard(
            card_type="Test",
            tags=tags,
            front="Q",
            back="A",
        )
        assert card.tags == tags

    @given(card=valid_anki_cards())
    @settings(max_examples=30)
    def test_anki_card_roundtrip_serialization(self, card):
        """Test that AnkiCard can be serialized and deserialized."""
        data = card.model_dump()
        restored = AnkiCard(**data)
        assert restored == card

    @given(card=valid_anki_cards())
    @settings(max_examples=30)
    def test_anki_card_json_roundtrip(self, card):
        """Test that AnkiCard survives JSON roundtrip."""
        json_str = card.model_dump_json()
        restored = AnkiCard.model_validate_json(json_str)
        assert restored == card


class TestMCQCardPropertyBased:
    """Property-based tests for MCQCard model."""

    @given(correct_answer=st.sampled_from(["A", "B", "C", "D"]))
    @settings(max_examples=20)
    def test_mcq_card_correct_answer_values(self, correct_answer):
        """Test that MCQCard accepts valid correct answer values."""
        card = MCQCard(
            card_type="Test",
            tags=[],
            question="Q?",
            options=["A", "B", "C", "D"],
            correct_answer=correct_answer,
            explanation="Exp",
        )
        assert card.correct_answer == correct_answer

    @given(
        options=st.lists(st.text(min_size=1, max_size=100), min_size=4, max_size=4)
    )
    @settings(max_examples=30)
    def test_mcq_card_accepts_any_options(self, options):
        """Test that MCQCard accepts any 4 non-empty options."""
        card = MCQCard(
            card_type="Test",
            tags=[],
            question="Q?",
            options=options,
            correct_answer="A",
            explanation="Exp",
        )
        assert card.options == options

    @given(card=valid_mcq_cards())
    @settings(max_examples=30)
    def test_mcq_card_roundtrip_serialization(self, card):
        """Test that MCQCard can be serialized and deserialized."""
        data = card.model_dump()
        restored = MCQCard(**data)
        assert restored == card

    @given(
        question=st.text(min_size=1, max_size=500),
        explanation=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=30)
    def test_mcq_card_accepts_unicode_content(self, question, explanation):
        """Test that MCQCard accepts unicode in question and explanation."""
        card = MCQCard(
            card_type="Test",
            tags=[],
            question=question,
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation=explanation,
        )
        assert card.question == question
        assert card.explanation == explanation


class TestProblemModelsPropertyBased:
    """Property-based tests for problem models."""

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_leetcode_problem_accepts_valid_strings(self, title, topic, difficulty):
        """Test that LeetCodeProblem accepts valid string fields."""
        problem = LeetCodeProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[],
        )
        assert problem.title == title
        assert problem.topic == topic
        assert problem.difficulty == difficulty

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_cs_problem_accepts_valid_strings(self, title, topic, difficulty):
        """Test that CSProblem accepts valid string fields."""
        problem = CSProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[],
        )
        assert problem.title == title
        assert problem.topic == topic

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_physics_problem_accepts_valid_strings(self, title, topic, difficulty):
        """Test that PhysicsProblem accepts valid string fields."""
        problem = PhysicsProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[],
        )
        assert problem.title == title

    @given(num_cards=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    def test_problem_accepts_multiple_cards(self, num_cards):
        """Test that problems accept multiple cards."""
        cards = [
            AnkiCard(card_type="Test", tags=[], front=f"Q{i}", back=f"A{i}")
            for i in range(num_cards)
        ]
        problem = LeetCodeProblem(
            title="Test",
            topic="Test",
            difficulty="Easy",
            cards=cards,
        )
        assert len(problem.cards) == num_cards

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=30)
    def test_generic_problem_behaves_like_base(self, title, topic):
        """Test that GenericProblem behaves like BaseProblem."""
        generic = GenericProblem(
            title=title,
            topic=topic,
            difficulty="Medium",
            cards=[],
        )
        base = BaseProblem(
            title=title,
            topic=topic,
            difficulty="Medium",
            cards=[],
        )
        assert generic.title == base.title
        assert generic.topic == base.topic


class TestMCQProblemPropertyBased:
    """Property-based tests for MCQProblem model."""

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_mcq_problem_accepts_valid_strings(self, title, topic, difficulty):
        """Test that MCQProblem accepts valid string fields."""
        problem = MCQProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[],
        )
        assert problem.title == title
        assert problem.topic == topic
        assert problem.difficulty == difficulty

    @given(num_cards=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    def test_mcq_problem_accepts_multiple_cards(self, num_cards):
        """Test that MCQProblem accepts multiple MCQ cards."""
        cards = [
            MCQCard(
                card_type="Test",
                tags=[],
                question=f"Q{i}?",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation=f"Exp{i}",
            )
            for i in range(num_cards)
        ]
        problem = MCQProblem(
            title="Test",
            topic="Test",
            difficulty="Easy",
            cards=cards,
        )
        assert len(problem.cards) == num_cards


class TestModelSerializationPropertyBased:
    """Property-based tests for model serialization."""

    @given(card=valid_anki_cards())
    @settings(max_examples=30)
    def test_anki_card_model_dump_contains_all_fields(self, card):
        """Test that model_dump contains all fields."""
        data = card.model_dump()
        assert "card_type" in data
        assert "tags" in data
        assert "front" in data
        assert "back" in data
        assert len(data) == 4  # No extra fields

    @given(card=valid_mcq_cards())
    @settings(max_examples=30)
    def test_mcq_card_model_dump_contains_all_fields(self, card):
        """Test that MCQCard model_dump contains all fields."""
        data = card.model_dump()
        assert "card_type" in data
        assert "tags" in data
        assert "question" in data
        assert "options" in data
        assert "correct_answer" in data
        assert "explanation" in data
        assert len(data) == 6

    @given(
        title=st.text(min_size=1, max_size=50),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_problem_model_dump_roundtrip(self, title, topic, difficulty):
        """Test that problem models survive model_dump roundtrip."""
        original = LeetCodeProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[AnkiCard(card_type="Test", tags=[], front="Q", back="A")],
        )
        data = original.model_dump()
        restored = LeetCodeProblem(**data)
        assert restored.title == original.title
        assert restored.topic == original.topic
        assert restored.difficulty == original.difficulty
        assert len(restored.cards) == len(original.cards)


class TestModelValidationPropertyBased:
    """Property-based tests for model validation."""

    @given(extra_key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll",))))
    @settings(max_examples=20)
    def test_anki_card_rejects_extra_fields(self, extra_key):
        """Test that AnkiCard rejects any extra field."""
        assume(extra_key not in ["card_type", "tags", "front", "back"])
        with pytest.raises(ValidationError):
            AnkiCard(
                card_type="Test",
                tags=[],
                front="Q",
                back="A",
                **{extra_key: "value"}
            )

    @given(extra_key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll",))))
    @settings(max_examples=20)
    def test_mcq_card_rejects_extra_fields(self, extra_key):
        """Test that MCQCard rejects any extra field."""
        assume(extra_key not in ["card_type", "tags", "question", "options", "correct_answer", "explanation"])
        with pytest.raises(ValidationError):
            MCQCard(
                card_type="Test",
                tags=[],
                question="Q?",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Exp",
                **{extra_key: "value"}
            )

    @given(extra_key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll",))))
    @settings(max_examples=20)
    def test_problem_rejects_extra_fields(self, extra_key):
        """Test that problem models reject extra fields."""
        assume(extra_key not in ["title", "topic", "difficulty", "cards"])
        with pytest.raises(ValidationError):
            LeetCodeProblem(
                title="Test",
                topic="Test",
                difficulty="Easy",
                cards=[],
                **{extra_key: "value"}
            )
