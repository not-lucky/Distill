"""
genanki Model construction for Distill.

Defines the three card layouts (Basic, Cloze, MCQ) with deterministic IDs and
the shared Catppuccin Mocha CSS theme. The Basic and Cloze templates use the
standard Anki question/answer format; the MCQ template embeds a small
JavaScript snippet to highlight the correct option when the answer is revealed.
"""

import genanki

from .ids import generate_id
from .styles import CARD_CSS


def _basic_template() -> dict:
    return {
        "name": "Basic Card",
        "qfmt": (
            '<div class="card-type">{{CardType}}</div>\n'
            '<div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>\n'
            "<hr>\n"
            '<div class="question">{{Front}}</div>'
        ),
        "afmt": (
            '<div class="card-type">{{CardType}}</div>\n'
            '<div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>\n'
            "<hr>\n"
            '<div class="question">{{Front}}</div>\n'
            '<hr id="answer">\n'
            '<div class="answer">{{Back}}</div>\n'
            '<div class="explanation">{{Explanation}}</div>'
        ),
    }


def _cloze_template() -> dict:
    return {
        "name": "Cloze Card",
        "qfmt": (
            '<div class="card-type">{{CardType}}</div>\n'
            '<div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>\n'
            "<hr>\n"
            '<div class="cloze-text">{{cloze:Front}}</div>'
        ),
        "afmt": (
            '<div class="card-type">{{CardType}}</div>\n'
            '<div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>\n'
            "<hr>\n"
            '<div class="cloze-text">{{cloze:Front}}</div>\n'
            '<hr id="answer">\n'
            '<div class="explanation">{{Explanation}}</div>'
        ),
    }


def _mcq_template() -> dict:
    return {
        "name": "MCQ Card",
        "qfmt": (
            '<div class="card-type">{{CardType}}</div>\n'
            '<div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>\n'
            "<hr>\n"
            '<div class="question">{{Front}}</div>\n'
            '<div class="options">\n'
            '    <div class="option" data-option="A"><span class="option-letter">A</span> {{OptionA}}</div>\n'
            '    <div class="option" data-option="B"><span class="option-letter">B</span> {{OptionB}}</div>\n'
            "    {{#OptionC}}\n"
            '    <div class="option" data-option="C"><span class="option-letter">C</span> {{OptionC}}</div>\n'
            "    {{/OptionC}}\n"
            "    {{#OptionD}}\n"
            '    <div class="option" data-option="D"><span class="option-letter">D</span> {{OptionD}}</div>\n'
            "    {{/OptionD}}\n"
            "</div>"
        ),
        "afmt": (
            '<div class="card-type">{{CardType}}</div>\n'
            '<div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>\n'
            "<hr>\n"
            '<div class="question">{{Front}}</div>\n'
            '<div class="options answer-revealed">\n'
            '    <div class="option" data-option="A"><span class="option-letter">A</span> {{OptionA}}</div>\n'
            '    <div class="option" data-option="B"><span class="option-letter">B</span> {{OptionB}}</div>\n'
            "    {{#OptionC}}\n"
            '    <div class="option" data-option="C"><span class="option-letter">C</span> {{OptionC}}</div>\n'
            "    {{/OptionC}}\n"
            "    {{#OptionD}}\n"
            '    <div class="option" data-option="D"><span class="option-letter">D</span> {{OptionD}}</div>\n'
            "    {{/OptionD}}\n"
            "</div>\n"
            '<hr id="answer">\n'
            '<div class="correct-answer-badge">✓ Correct Answer: {{CorrectAnswer}}</div>\n'
            '<div class="explanation">{{Explanation}}</div>\n'
            "<script>\n"
            "  (function() {\n"
            '    var correct = "{{CorrectAnswer}}".trim();\n'
            '    var container = document.querySelector(".options.answer-revealed");\n'
            "    if (!container) return;\n"
            '    var options = container.querySelectorAll(".option");\n'
            "    options.forEach(function(opt) {\n"
            '      if (opt.getAttribute("data-option") === correct) {\n'
            '        opt.style.borderColor = "var(--ctp-green)";\n'
            '        opt.style.backgroundColor = "rgba(166, 227, 161, 0.15)";\n'
            '        opt.style.opacity = "1";\n'
            '        var letter = opt.querySelector(".option-letter");\n'
            "        if (letter) {\n"
            '          letter.style.backgroundColor = "var(--ctp-green)";\n'
            '          letter.style.color = "var(--ctp-base)";\n'
            "        }\n"
            "      }\n"
            "    });\n"
            "  })();\n"
            "</script>"
        ),
    }


def create_models() -> tuple[genanki.Model, genanki.Model, genanki.Model]:
    """
    Creates and returns the three genanki Model objects (Basic, Cloze, MCQ)
    with deterministic IDs and the Catppuccin Mocha CSS theme.
    """
    basic_model = genanki.Model(
        generate_id("Distill Basic Model"),
        "Distill Basic Model",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
            {"name": "Explanation"},
            {"name": "CardType"},
            {"name": "Topic"},
            {"name": "Problem"},
            {"name": "Difficulty"},
            {"name": "Tags"},
        ],
        templates=[_basic_template()],
        css=CARD_CSS,
    )

    cloze_model = genanki.Model(
        generate_id("Distill Cloze Model"),
        "Distill Cloze Model",
        fields=[
            {"name": "Front"},
            {"name": "Explanation"},
            {"name": "CardType"},
            {"name": "Topic"},
            {"name": "Problem"},
            {"name": "Difficulty"},
            {"name": "Tags"},
        ],
        templates=[_cloze_template()],
        css=CARD_CSS,
        model_type=genanki.Model.CLOZE,
    )

    mcq_model = genanki.Model(
        generate_id("Distill MCQ Model"),
        "Distill MCQ Model",
        fields=[
            {"name": "Front"},
            {"name": "OptionA"},
            {"name": "OptionB"},
            {"name": "OptionC"},
            {"name": "OptionD"},
            {"name": "CorrectAnswer"},
            {"name": "Explanation"},
            {"name": "CardType"},
            {"name": "Topic"},
            {"name": "Problem"},
            {"name": "Difficulty"},
            {"name": "Tags"},
        ],
        templates=[_mcq_template()],
        css=CARD_CSS,
    )

    return basic_model, cloze_model, mcq_model
