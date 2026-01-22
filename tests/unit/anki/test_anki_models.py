"""Tests for anki/models.py."""

import pytest
from unittest.mock import patch, MagicMock

from assertpy import assert_that

from src.anki.models import AnkiModelFactory


class TestAnkiModelFactory:
    """Tests for AnkiModelFactory class."""

    def test_init_creates_models(self):
        """
        Given the AnkiModelFactory class
        When instantiated
        Then both basic and MCQ models are created
        """
        factory = AnkiModelFactory()

        assert_that(factory.basic_model).is_not_none()
        assert_that(factory.mcq_model).is_not_none()

    def test_basic_model_name(self):
        """
        Given an AnkiModelFactory
        When accessing basic_model
        Then it has the correct name
        """
        factory = AnkiModelFactory()

        assert_that(factory.basic_model.name).is_equal_to("LeetCode Basic")

    def test_mcq_model_name(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model
        Then it has the correct name
        """
        factory = AnkiModelFactory()

        assert_that(factory.mcq_model.name).is_equal_to("MCQ Card")

    def test_basic_model_fields(self):
        """
        Given an AnkiModelFactory
        When accessing basic_model fields
        Then all required fields are present
        """
        factory = AnkiModelFactory()

        field_names = [f["name"] for f in factory.basic_model.fields]

        assert_that(field_names).contains("Front")
        assert_that(field_names).contains("Back")
        assert_that(field_names).contains("CardType")
        assert_that(field_names).contains("Topic")
        assert_that(field_names).contains("Problem")
        assert_that(field_names).contains("Difficulty")
        assert_that(field_names).contains("Tags")

    def test_basic_model_has_7_fields(self):
        """
        Given an AnkiModelFactory
        When accessing basic_model
        Then it has exactly 7 fields
        """
        factory = AnkiModelFactory()

        assert_that(factory.basic_model.fields).is_length(7)

    def test_mcq_model_fields(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model fields
        Then all required fields are present
        """
        factory = AnkiModelFactory()

        field_names = [f["name"] for f in factory.mcq_model.fields]

        assert_that(field_names).contains("Question")
        assert_that(field_names).contains("OptionA")
        assert_that(field_names).contains("OptionB")
        assert_that(field_names).contains("OptionC")
        assert_that(field_names).contains("OptionD")
        assert_that(field_names).contains("CorrectAnswer")
        assert_that(field_names).contains("Explanation")
        assert_that(field_names).contains("CardType")
        assert_that(field_names).contains("Topic")
        assert_that(field_names).contains("Problem")
        assert_that(field_names).contains("Difficulty")
        assert_that(field_names).contains("Tags")

    def test_mcq_model_has_12_fields(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model
        Then it has exactly 12 fields
        """
        factory = AnkiModelFactory()

        assert_that(factory.mcq_model.fields).is_length(12)

    def test_basic_model_has_template(self):
        """
        Given an AnkiModelFactory
        When accessing basic_model
        Then it has at least one template
        """
        factory = AnkiModelFactory()

        assert_that(factory.basic_model.templates).is_not_empty()

    def test_mcq_model_has_template(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model
        Then it has at least one template
        """
        factory = AnkiModelFactory()

        assert_that(factory.mcq_model.templates).is_not_empty()

    def test_basic_model_template_content(self):
        """
        Given an AnkiModelFactory
        When accessing basic_model template
        Then it has front and back format with correct placeholders
        """
        factory = AnkiModelFactory()

        template = factory.basic_model.templates[0]
        assert_that("qfmt" in template).is_true()
        assert_that("afmt" in template).is_true()
        assert_that(template["qfmt"]).contains("{{Front}}")
        assert_that(template["afmt"]).contains("{{Back}}")

    def test_mcq_model_template_content(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model template
        Then it has question, options, and answer placeholders
        """
        factory = AnkiModelFactory()

        template = factory.mcq_model.templates[0]
        assert_that("qfmt" in template).is_true()
        assert_that("afmt" in template).is_true()
        assert_that(template["qfmt"]).contains("{{Question}}")
        assert_that(template["qfmt"]).contains("{{OptionA}}")
        assert_that(template["afmt"]).contains("{{CorrectAnswer}}")
        assert_that(template["afmt"]).contains("{{Explanation}}")

    def test_basic_model_has_css(self):
        """
        Given an AnkiModelFactory
        When accessing basic_model
        Then it has CSS styling
        """
        factory = AnkiModelFactory()

        assert_that(factory.basic_model.css).is_not_none()
        assert_that(factory.basic_model.css).is_not_empty()

    def test_mcq_model_has_css(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model
        Then it has CSS styling
        """
        factory = AnkiModelFactory()

        assert_that(factory.mcq_model.css).is_not_none()
        assert_that(factory.mcq_model.css).is_not_empty()


class TestGenerateId:
    """Tests for _generate_id method."""

    def test_generate_id_returns_int(self):
        """
        Given a text string
        When _generate_id is called
        Then an integer is returned
        """
        factory = AnkiModelFactory()

        result = factory._generate_id("test text")

        assert_that(result).is_instance_of(int)

    def test_generate_id_consistent(self):
        """
        Given the same input text
        When _generate_id is called twice
        Then the same ID is returned
        """
        factory = AnkiModelFactory()

        id1 = factory._generate_id("test text")
        id2 = factory._generate_id("test text")

        assert_that(id1).is_equal_to(id2)

    def test_generate_id_different_for_different_input(self):
        """
        Given different input texts
        When _generate_id is called
        Then different IDs are returned
        """
        factory = AnkiModelFactory()

        id1 = factory._generate_id("text one")
        id2 = factory._generate_id("text two")

        assert_that(id1).is_not_equal_to(id2)

    def test_generate_id_uses_md5(self):
        """
        Given a text string
        When _generate_id is called
        Then the ID is based on MD5 hash
        """
        factory = AnkiModelFactory()
        import hashlib

        text = "test content"
        expected = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        result = factory._generate_id(text)

        assert_that(result).is_equal_to(expected)

    def test_generate_id_handles_unicode(self):
        """
        Given unicode text
        When _generate_id is called
        Then an integer is returned without error
        """
        factory = AnkiModelFactory()

        result = factory._generate_id("Unicode: \u4e2d\u6587 \u65e5\u672c\u8a9e")

        assert_that(result).is_instance_of(int)

    def test_generate_id_handles_empty_string(self):
        """
        Given an empty string
        When _generate_id is called
        Then an integer is returned
        """
        factory = AnkiModelFactory()

        result = factory._generate_id("")

        assert_that(result).is_instance_of(int)


class TestModelIds:
    """Tests for model ID generation."""

    def test_basic_model_has_id(self):
        """
        Given an AnkiModelFactory
        When accessing basic_model
        Then it has a numeric ID
        """
        factory = AnkiModelFactory()

        assert_that(factory.basic_model.model_id).is_not_none()
        assert_that(factory.basic_model.model_id).is_instance_of(int)

    def test_mcq_model_has_id(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model
        Then it has a numeric ID
        """
        factory = AnkiModelFactory()

        assert_that(factory.mcq_model.model_id).is_not_none()
        assert_that(factory.mcq_model.model_id).is_instance_of(int)

    def test_models_have_different_ids(self):
        """
        Given an AnkiModelFactory
        When comparing model IDs
        Then basic and MCQ models have different IDs
        """
        factory = AnkiModelFactory()

        assert_that(factory.basic_model.model_id).is_not_equal_to(factory.mcq_model.model_id)

    def test_model_ids_are_consistent(self):
        """
        Given two AnkiModelFactory instances
        When comparing model IDs
        Then IDs are consistent across instances
        """
        factory1 = AnkiModelFactory()
        factory2 = AnkiModelFactory()

        assert_that(factory1.basic_model.model_id).is_equal_to(factory2.basic_model.model_id)
        assert_that(factory1.mcq_model.model_id).is_equal_to(factory2.mcq_model.model_id)


class TestTemplateStructure:
    """Tests for template structure."""

    def test_basic_template_name(self):
        """
        Given an AnkiModelFactory
        When accessing basic_model template
        Then it has the correct name
        """
        factory = AnkiModelFactory()

        template = factory.basic_model.templates[0]
        assert_that(template["name"]).is_equal_to("Card 1")

    def test_mcq_template_name(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model template
        Then it has the correct name
        """
        factory = AnkiModelFactory()

        template = factory.mcq_model.templates[0]
        assert_that(template["name"]).is_equal_to("MCQ Card")

    def test_basic_template_shows_metadata(self):
        """
        Given an AnkiModelFactory
        When accessing basic_model template
        Then metadata placeholders are present
        """
        factory = AnkiModelFactory()

        qfmt = factory.basic_model.templates[0]["qfmt"]

        assert_that(qfmt).contains("{{CardType}}")
        assert_that(qfmt).contains("{{Topic}}")
        assert_that(qfmt).contains("{{Problem}}")
        assert_that(qfmt).contains("{{Difficulty}}")

    def test_mcq_template_shows_all_options(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model template
        Then all four option placeholders are present
        """
        factory = AnkiModelFactory()

        qfmt = factory.mcq_model.templates[0]["qfmt"]

        assert_that(qfmt).contains("{{OptionA}}")
        assert_that(qfmt).contains("{{OptionB}}")
        assert_that(qfmt).contains("{{OptionC}}")
        assert_that(qfmt).contains("{{OptionD}}")

    def test_mcq_answer_template_shows_correct_answer(self):
        """
        Given an AnkiModelFactory
        When accessing mcq_model answer template
        Then correct answer and explanation placeholders are present
        """
        factory = AnkiModelFactory()

        afmt = factory.mcq_model.templates[0]["afmt"]

        assert_that(afmt).contains("{{CorrectAnswer}}")
        assert_that(afmt).contains("{{Explanation}}")
