"""Tests for Pydantic models in src/models.py."""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from pydantic import ValidationError

from assertpy import assert_that

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
        """
        Given valid card parameters
        When AnkiCard is created
        Then all fields are stored correctly
        """
        card = AnkiCard(
            card_type="Concept",
            tags=["Tag1", "Tag2"],
            front="What is X?",
            back="X is Y."
        )
        assert_that(card.card_type).is_equal_to("Concept")
        assert_that(card.tags).is_equal_to(["Tag1", "Tag2"])
        assert_that(card.front).is_equal_to("What is X?")
        assert_that(card.back).is_equal_to("X is Y.")

    def test_anki_card_required_fields(self):
        """
        Given missing required fields
        When AnkiCard is created
        Then ValidationError is raised
        """
        with pytest.raises(ValidationError) as exc_info:
            AnkiCard(card_type="Concept", tags=["Tag1"])
        error_str = str(exc_info.value)
        assert_that("front" in error_str or "back" in error_str).is_true()

    def test_anki_card_extra_fields_forbidden(self):
        """
        Given extra fields
        When AnkiCard is created
        Then ValidationError is raised
        """
        with pytest.raises(ValidationError) as exc_info:
            AnkiCard(
                card_type="Concept",
                tags=["Tag1"],
                front="Q",
                back="A",
                extra_field="not allowed"
            )
        assert_that(str(exc_info.value).lower()).contains("extra")

    def test_anki_card_empty_tags(self):
        """
        Given empty tags list
        When AnkiCard is created
        Then empty list is stored
        """
        card = AnkiCard(
            card_type="Basic",
            tags=[],
            front="Q",
            back="A"
        )
        assert_that(card.tags).is_equal_to([])


class TestLeetCodeProblem:
    """Tests for LeetCodeProblem model."""

    def test_valid_leetcode_problem(self):
        """
        Given valid LeetCode problem parameters
        When LeetCodeProblem is created
        Then all fields are stored correctly
        """
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
        assert_that(problem.title).is_equal_to("Two Sum")
        assert_that(problem.topic).is_equal_to("Arrays")
        assert_that(problem.difficulty).is_equal_to("Easy")
        assert_that(problem.cards).is_length(1)

    def test_leetcode_problem_multiple_cards(self):
        """
        Given multiple cards
        When LeetCodeProblem is created
        Then all cards are stored
        """
        problem = LeetCodeProblem(
            title="Binary Search",
            topic="Binary Search",
            difficulty="Medium",
            cards=[
                AnkiCard(card_type="Concept", tags=[], front="Q1", back="A1"),
                AnkiCard(card_type="Code", tags=[], front="Q2", back="A2"),
            ]
        )
        assert_that(problem.cards).is_length(2)

    def test_leetcode_problem_required_fields(self):
        """
        Given missing required fields
        When LeetCodeProblem is created
        Then ValidationError is raised
        """
        with pytest.raises(ValidationError):
            LeetCodeProblem(title="Test", topic="Test")

    def test_leetcode_problem_extra_fields_forbidden(self):
        """
        Given extra fields
        When LeetCodeProblem is created
        Then ValidationError is raised
        """
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
        """
        Given valid CS problem parameters
        When CSProblem is created
        Then all fields are stored correctly
        """
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
        assert_that(problem.title).is_equal_to("Process Scheduling")
        assert_that(problem.topic).is_equal_to("Operating Systems")
        assert_that(problem.difficulty).is_equal_to("Intermediate")


class TestPhysicsProblem:
    """Tests for PhysicsProblem model."""

    def test_valid_physics_problem(self):
        """
        Given valid physics problem parameters
        When PhysicsProblem is created
        Then all fields are stored correctly
        """
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
        assert_that(problem.title).is_equal_to("Newton's Laws")
        assert_that(problem.topic).is_equal_to("Mechanics")


class TestMCQCard:
    """Tests for MCQCard model."""

    def test_valid_mcq_card(self):
        """
        Given valid MCQ card parameters
        When MCQCard is created
        Then all fields are stored correctly
        """
        card = MCQCard(
            card_type="Concept",
            tags=["Algorithm"],
            question="What is the time complexity of binary search?",
            options=["O(n)", "O(log n)", "O(n^2)", "O(1)"],
            correct_answer="B",
            explanation="Binary search divides the search space in half."
        )
        assert_that(card.card_type).is_equal_to("Concept")
        assert_that(card.question).is_equal_to("What is the time complexity of binary search?")
        assert_that(card.options).is_length(4)
        assert_that(card.correct_answer).is_equal_to("B")

    def test_mcq_card_required_fields(self):
        """
        Given missing required fields
        When MCQCard is created
        Then ValidationError is raised
        """
        with pytest.raises(ValidationError):
            MCQCard(
                card_type="Concept",
                tags=[],
                question="Q?",
                options=["A", "B", "C", "D"]
                # Missing correct_answer and explanation
            )

    def test_mcq_card_extra_fields_forbidden(self):
        """
        Given extra fields
        When MCQCard is created
        Then ValidationError is raised
        """
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
        """
        Given valid MCQ problem parameters
        When MCQProblem is created
        Then all fields are stored correctly
        """
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
        assert_that(problem.title).is_equal_to("Data Structures MCQ")
        assert_that(problem.cards).is_length(1)
        assert_that(problem.cards[0].correct_answer).is_equal_to("A")


class TestGenericProblem:
    """Tests for GenericProblem model."""

    def test_valid_generic_problem(self):
        """
        Given valid generic problem parameters
        When GenericProblem is created
        Then all fields are stored correctly
        """
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
        assert_that(problem.title).is_equal_to("Custom Topic")
        assert_that(problem.topic).is_equal_to("Custom Category")

    def test_generic_problem_inherits_base(self):
        """
        Given GenericProblem class
        When checking inheritance
        Then it is a subclass of BaseProblem
        """
        assert_that(issubclass(GenericProblem, BaseProblem)).is_true()


class TestBaseProblem:
    """Tests for BaseProblem model."""

    def test_base_problem_is_abstract_like(self):
        """
        Given BaseProblem class
        When instantiated
        Then it can be created (not truly abstract in Pydantic)
        """
        # BaseProblem is not abstract in Pydantic, but serves as base class
        problem = BaseProblem(
            title="Test",
            topic="Test",
            difficulty="Easy",
            cards=[]
        )
        assert_that(problem.title).is_equal_to("Test")

    def test_base_problem_empty_cards(self):
        """
        Given empty cards list
        When BaseProblem is created
        Then empty list is stored
        """
        problem = BaseProblem(
            title="Test",
            topic="Test",
            difficulty="Easy",
            cards=[]
        )
        assert_that(problem.cards).is_equal_to([])


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
        """
        Given any non-empty strings
        When AnkiCard is created
        Then all values are stored correctly
        """
        card = AnkiCard(
            card_type=card_type,
            tags=[],
            front=front,
            back=back,
        )
        assert_that(card.card_type).is_equal_to(card_type)
        assert_that(card.front).is_equal_to(front)
        assert_that(card.back).is_equal_to(back)

    @given(tags=st.lists(st.text(min_size=1, max_size=30), min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_anki_card_accepts_any_tags(self, tags):
        """
        Given any list of tags
        When AnkiCard is created
        Then tags are stored correctly
        """
        card = AnkiCard(
            card_type="Test",
            tags=tags,
            front="Q",
            back="A",
        )
        assert_that(card.tags).is_equal_to(tags)

    @given(card=valid_anki_cards())
    @settings(max_examples=30)
    def test_anki_card_roundtrip_serialization(self, card):
        """
        Given a valid AnkiCard
        When serialized and deserialized
        Then the restored card equals the original
        """
        data = card.model_dump()
        restored = AnkiCard(**data)
        assert_that(restored).is_equal_to(card)

    @given(card=valid_anki_cards())
    @settings(max_examples=30)
    def test_anki_card_json_roundtrip(self, card):
        """
        Given a valid AnkiCard
        When converted to JSON and back
        Then the restored card equals the original
        """
        json_str = card.model_dump_json()
        restored = AnkiCard.model_validate_json(json_str)
        assert_that(restored).is_equal_to(card)


class TestMCQCardPropertyBased:
    """Property-based tests for MCQCard model."""

    @given(correct_answer=st.sampled_from(["A", "B", "C", "D"]))
    @settings(max_examples=20)
    def test_mcq_card_correct_answer_values(self, correct_answer):
        """
        Given valid correct answer values (A, B, C, D)
        When MCQCard is created
        Then correct_answer is stored correctly
        """
        card = MCQCard(
            card_type="Test",
            tags=[],
            question="Q?",
            options=["A", "B", "C", "D"],
            correct_answer=correct_answer,
            explanation="Exp",
        )
        assert_that(card.correct_answer).is_equal_to(correct_answer)

    @given(
        options=st.lists(st.text(min_size=1, max_size=100), min_size=4, max_size=4)
    )
    @settings(max_examples=30)
    def test_mcq_card_accepts_any_options(self, options):
        """
        Given any 4 non-empty options
        When MCQCard is created
        Then options are stored correctly
        """
        card = MCQCard(
            card_type="Test",
            tags=[],
            question="Q?",
            options=options,
            correct_answer="A",
            explanation="Exp",
        )
        assert_that(card.options).is_equal_to(options)

    @given(card=valid_mcq_cards())
    @settings(max_examples=30)
    def test_mcq_card_roundtrip_serialization(self, card):
        """
        Given a valid MCQCard
        When serialized and deserialized
        Then the restored card equals the original
        """
        data = card.model_dump()
        restored = MCQCard(**data)
        assert_that(restored).is_equal_to(card)

    @given(
        question=st.text(min_size=1, max_size=500),
        explanation=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=30)
    def test_mcq_card_accepts_unicode_content(self, question, explanation):
        """
        Given unicode content in question and explanation
        When MCQCard is created
        Then unicode is stored correctly
        """
        card = MCQCard(
            card_type="Test",
            tags=[],
            question=question,
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation=explanation,
        )
        assert_that(card.question).is_equal_to(question)
        assert_that(card.explanation).is_equal_to(explanation)


class TestProblemModelsPropertyBased:
    """Property-based tests for problem models."""

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_leetcode_problem_accepts_valid_strings(self, title, topic, difficulty):
        """
        Given valid string fields
        When LeetCodeProblem is created
        Then all values are stored correctly
        """
        problem = LeetCodeProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[],
        )
        assert_that(problem.title).is_equal_to(title)
        assert_that(problem.topic).is_equal_to(topic)
        assert_that(problem.difficulty).is_equal_to(difficulty)

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_cs_problem_accepts_valid_strings(self, title, topic, difficulty):
        """
        Given valid string fields
        When CSProblem is created
        Then all values are stored correctly
        """
        problem = CSProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[],
        )
        assert_that(problem.title).is_equal_to(title)
        assert_that(problem.topic).is_equal_to(topic)

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_physics_problem_accepts_valid_strings(self, title, topic, difficulty):
        """
        Given valid string fields
        When PhysicsProblem is created
        Then all values are stored correctly
        """
        problem = PhysicsProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[],
        )
        assert_that(problem.title).is_equal_to(title)

    @given(num_cards=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    def test_problem_accepts_multiple_cards(self, num_cards):
        """
        Given multiple cards
        When LeetCodeProblem is created
        Then all cards are stored
        """
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
        assert_that(problem.cards).is_length(num_cards)

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=30)
    def test_generic_problem_behaves_like_base(self, title, topic):
        """
        Given same title and topic
        When GenericProblem and BaseProblem are created
        Then they have equivalent values
        """
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
        assert_that(generic.title).is_equal_to(base.title)
        assert_that(generic.topic).is_equal_to(base.topic)


class TestMCQProblemPropertyBased:
    """Property-based tests for MCQProblem model."""

    @given(
        title=st.text(min_size=1, max_size=100),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_mcq_problem_accepts_valid_strings(self, title, topic, difficulty):
        """
        Given valid string fields
        When MCQProblem is created
        Then all values are stored correctly
        """
        problem = MCQProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[],
        )
        assert_that(problem.title).is_equal_to(title)
        assert_that(problem.topic).is_equal_to(topic)
        assert_that(problem.difficulty).is_equal_to(difficulty)

    @given(num_cards=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    def test_mcq_problem_accepts_multiple_cards(self, num_cards):
        """
        Given multiple MCQ cards
        When MCQProblem is created
        Then all cards are stored
        """
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
        assert_that(problem.cards).is_length(num_cards)


class TestModelSerializationPropertyBased:
    """Property-based tests for model serialization."""

    @given(card=valid_anki_cards())
    @settings(max_examples=30)
    def test_anki_card_model_dump_contains_all_fields(self, card):
        """
        Given a valid AnkiCard
        When model_dump is called
        Then all fields are present with no extras
        """
        data = card.model_dump()
        assert_that(data).contains_key("card_type")
        assert_that(data).contains_key("tags")
        assert_that(data).contains_key("front")
        assert_that(data).contains_key("back")
        assert_that(data).is_length(4)  # No extra fields

    @given(card=valid_mcq_cards())
    @settings(max_examples=30)
    def test_mcq_card_model_dump_contains_all_fields(self, card):
        """
        Given a valid MCQCard
        When model_dump is called
        Then all fields are present with no extras
        """
        data = card.model_dump()
        assert_that(data).contains_key("card_type")
        assert_that(data).contains_key("tags")
        assert_that(data).contains_key("question")
        assert_that(data).contains_key("options")
        assert_that(data).contains_key("correct_answer")
        assert_that(data).contains_key("explanation")
        assert_that(data).is_length(6)

    @given(
        title=st.text(min_size=1, max_size=50),
        topic=st.text(min_size=1, max_size=50),
        difficulty=valid_difficulty_levels(),
    )
    @settings(max_examples=30)
    def test_problem_model_dump_roundtrip(self, title, topic, difficulty):
        """
        Given a valid LeetCodeProblem
        When serialized and deserialized via model_dump
        Then all fields are preserved
        """
        original = LeetCodeProblem(
            title=title,
            topic=topic,
            difficulty=difficulty,
            cards=[AnkiCard(card_type="Test", tags=[], front="Q", back="A")],
        )
        data = original.model_dump()
        restored = LeetCodeProblem(**data)
        assert_that(restored.title).is_equal_to(original.title)
        assert_that(restored.topic).is_equal_to(original.topic)
        assert_that(restored.difficulty).is_equal_to(original.difficulty)
        assert_that(restored.cards).is_length(len(original.cards))


class TestModelValidationPropertyBased:
    """Property-based tests for model validation."""

    @given(extra_key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll",))))
    @settings(max_examples=20)
    def test_anki_card_rejects_extra_fields(self, extra_key):
        """
        Given an extra field key
        When AnkiCard is created with that extra field
        Then ValidationError is raised
        """
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
        """
        Given an extra field key
        When MCQCard is created with that extra field
        Then ValidationError is raised
        """
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
        """
        Given an extra field key
        When LeetCodeProblem is created with that extra field
        Then ValidationError is raised
        """
        assume(extra_key not in ["title", "topic", "difficulty", "cards"])
        with pytest.raises(ValidationError):
            LeetCodeProblem(
                title="Test",
                topic="Test",
                difficulty="Easy",
                cards=[],
                **{extra_key: "value"}
            )
