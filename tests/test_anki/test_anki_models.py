"""Tests for anki/models.py."""

import pytest
from unittest.mock import patch, MagicMock

from src.anki.models import AnkiModelFactory


class TestAnkiModelFactory:
    """Tests for AnkiModelFactory class."""

    def test_init_creates_models(self):
        """Test that initialization creates both models."""
        factory = AnkiModelFactory()

        assert factory.basic_model is not None
        assert factory.mcq_model is not None

    def test_basic_model_name(self):
        """Test basic model has correct name."""
        factory = AnkiModelFactory()

        assert factory.basic_model.name == "LeetCode Basic"

    def test_mcq_model_name(self):
        """Test MCQ model has correct name."""
        factory = AnkiModelFactory()

        assert factory.mcq_model.name == "MCQ Card"

    def test_basic_model_fields(self):
        """Test basic model has required fields."""
        factory = AnkiModelFactory()

        field_names = [f["name"] for f in factory.basic_model.fields]

        assert "Front" in field_names
        assert "Back" in field_names
        assert "CardType" in field_names
        assert "Topic" in field_names
        assert "Problem" in field_names
        assert "Difficulty" in field_names
        assert "Tags" in field_names

    def test_basic_model_has_7_fields(self):
        """Test basic model has exactly 7 fields."""
        factory = AnkiModelFactory()

        assert len(factory.basic_model.fields) == 7

    def test_mcq_model_fields(self):
        """Test MCQ model has required fields."""
        factory = AnkiModelFactory()

        field_names = [f["name"] for f in factory.mcq_model.fields]

        assert "Question" in field_names
        assert "OptionA" in field_names
        assert "OptionB" in field_names
        assert "OptionC" in field_names
        assert "OptionD" in field_names
        assert "CorrectAnswer" in field_names
        assert "Explanation" in field_names
        assert "CardType" in field_names
        assert "Topic" in field_names
        assert "Problem" in field_names
        assert "Difficulty" in field_names
        assert "Tags" in field_names

    def test_mcq_model_has_12_fields(self):
        """Test MCQ model has exactly 12 fields."""
        factory = AnkiModelFactory()

        assert len(factory.mcq_model.fields) == 12

    def test_basic_model_has_template(self):
        """Test basic model has at least one template."""
        factory = AnkiModelFactory()

        assert len(factory.basic_model.templates) >= 1

    def test_mcq_model_has_template(self):
        """Test MCQ model has at least one template."""
        factory = AnkiModelFactory()

        assert len(factory.mcq_model.templates) >= 1

    def test_basic_model_template_content(self):
        """Test basic model template has front and back format."""
        factory = AnkiModelFactory()

        template = factory.basic_model.templates[0]
        assert "qfmt" in template
        assert "afmt" in template
        assert "{{Front}}" in template["qfmt"]
        assert "{{Back}}" in template["afmt"]

    def test_mcq_model_template_content(self):
        """Test MCQ model template has question and options."""
        factory = AnkiModelFactory()

        template = factory.mcq_model.templates[0]
        assert "qfmt" in template
        assert "afmt" in template
        assert "{{Question}}" in template["qfmt"]
        assert "{{OptionA}}" in template["qfmt"]
        assert "{{CorrectAnswer}}" in template["afmt"]
        assert "{{Explanation}}" in template["afmt"]

    def test_basic_model_has_css(self):
        """Test basic model has CSS styling."""
        factory = AnkiModelFactory()

        assert factory.basic_model.css is not None
        assert len(factory.basic_model.css) > 0

    def test_mcq_model_has_css(self):
        """Test MCQ model has CSS styling."""
        factory = AnkiModelFactory()

        assert factory.mcq_model.css is not None
        assert len(factory.mcq_model.css) > 0


class TestGenerateId:
    """Tests for _generate_id method."""

    def test_generate_id_returns_int(self):
        """Test that _generate_id returns an integer."""
        factory = AnkiModelFactory()

        result = factory._generate_id("test text")

        assert isinstance(result, int)

    def test_generate_id_consistent(self):
        """Test that same input produces same ID."""
        factory = AnkiModelFactory()

        id1 = factory._generate_id("test text")
        id2 = factory._generate_id("test text")

        assert id1 == id2

    def test_generate_id_different_for_different_input(self):
        """Test that different inputs produce different IDs."""
        factory = AnkiModelFactory()

        id1 = factory._generate_id("text one")
        id2 = factory._generate_id("text two")

        assert id1 != id2

    def test_generate_id_uses_md5(self):
        """Test that ID is based on MD5 hash."""
        factory = AnkiModelFactory()
        import hashlib

        text = "test content"
        expected = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        result = factory._generate_id(text)

        assert result == expected

    def test_generate_id_handles_unicode(self):
        """Test that _generate_id handles unicode text."""
        factory = AnkiModelFactory()

        # Should not raise
        result = factory._generate_id("Unicode: \u4e2d\u6587 \u65e5\u672c\u8a9e")

        assert isinstance(result, int)

    def test_generate_id_handles_empty_string(self):
        """Test that _generate_id handles empty string."""
        factory = AnkiModelFactory()

        result = factory._generate_id("")

        assert isinstance(result, int)


class TestModelIds:
    """Tests for model ID generation."""

    def test_basic_model_has_id(self):
        """Test basic model has a numeric ID."""
        factory = AnkiModelFactory()

        assert factory.basic_model.model_id is not None
        assert isinstance(factory.basic_model.model_id, int)

    def test_mcq_model_has_id(self):
        """Test MCQ model has a numeric ID."""
        factory = AnkiModelFactory()

        assert factory.mcq_model.model_id is not None
        assert isinstance(factory.mcq_model.model_id, int)

    def test_models_have_different_ids(self):
        """Test that basic and MCQ models have different IDs."""
        factory = AnkiModelFactory()

        assert factory.basic_model.model_id != factory.mcq_model.model_id

    def test_model_ids_are_consistent(self):
        """Test that model IDs are consistent across instances."""
        factory1 = AnkiModelFactory()
        factory2 = AnkiModelFactory()

        assert factory1.basic_model.model_id == factory2.basic_model.model_id
        assert factory1.mcq_model.model_id == factory2.mcq_model.model_id


class TestTemplateStructure:
    """Tests for template structure."""

    def test_basic_template_name(self):
        """Test basic template has correct name."""
        factory = AnkiModelFactory()

        template = factory.basic_model.templates[0]
        assert template["name"] == "Card 1"

    def test_mcq_template_name(self):
        """Test MCQ template has correct name."""
        factory = AnkiModelFactory()

        template = factory.mcq_model.templates[0]
        assert template["name"] == "MCQ Card"

    def test_basic_template_shows_metadata(self):
        """Test basic template displays metadata."""
        factory = AnkiModelFactory()

        qfmt = factory.basic_model.templates[0]["qfmt"]

        assert "{{CardType}}" in qfmt
        assert "{{Topic}}" in qfmt
        assert "{{Problem}}" in qfmt
        assert "{{Difficulty}}" in qfmt

    def test_mcq_template_shows_all_options(self):
        """Test MCQ template shows all four options."""
        factory = AnkiModelFactory()

        qfmt = factory.mcq_model.templates[0]["qfmt"]

        assert "{{OptionA}}" in qfmt
        assert "{{OptionB}}" in qfmt
        assert "{{OptionC}}" in qfmt
        assert "{{OptionD}}" in qfmt

    def test_mcq_answer_template_shows_correct_answer(self):
        """Test MCQ answer template shows correct answer."""
        factory = AnkiModelFactory()

        afmt = factory.mcq_model.templates[0]["afmt"]

        assert "{{CorrectAnswer}}" in afmt
        assert "{{Explanation}}" in afmt
