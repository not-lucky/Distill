#!/usr/bin/env python3
"""
Python Compilation Script for LLM2Deck.
Renders markdown to sanitized HTML, shuffles MCQ options, generates deterministic IDs,
and compiles the stage 3 JSON data into Anki (.apkg) files using genanki.
"""

import sys
import os
import json
import hashlib
import random
import re
import argparse
import markdown
import bleach
import genanki

# Whitelist of allowed HTML tags and attributes as per §6.3
ALLOWED_TAGS = [
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
    "img",
]

ALLOWED_ATTRIBUTES = {
    "*": ["class"],
    "a": ["href", "title", "target"],
    "img": ["src", "alt", "title"],
}

# Catppuccin Mocha theme CSS stylesheet (§6.3)
CARD_CSS = """
:root {
  --ctp-rosewater: #f5e0dc;
  --ctp-flamingo: #f2cdcd;
  --ctp-pink: #f5c2e7;
  --ctp-mauve: #cba6f7;
  --ctp-red: #f38ba8;
  --ctp-maroon: #eba0ac;
  --ctp-peach: #fab387;
  --ctp-yellow: #f9e2af;
  --ctp-green: #a6e3a1;
  --ctp-teal: #94e2d5;
  --ctp-sky: #89dceb;
  --ctp-sapphire: #74c7ec;
  --ctp-blue: #89b4fa;
  --ctp-lavender: #b4befe;
  --ctp-text: #cdd6f4;
  --ctp-subtext1: #bac2de;
  --ctp-subtext0: #a6adc8;
  --ctp-overlay2: #9399b2;
  --ctp-overlay1: #7f849c;
  --ctp-overlay0: #6c7086;
  --ctp-surface2: #585b70;
  --ctp-surface1: #45475a;
  --ctp-surface0: #313244;
  --ctp-base: #1e1e2e;
  --ctp-mantle: #181825;
  --ctp-crust: #11111b;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: var(--ctp-base);
  color: var(--ctp-text);
  margin: 0;
  padding: 10px;
}

.card {
  background-color: var(--ctp-base);
  color: var(--ctp-text);
  padding: 24px;
  max-width: 750px;
  margin: 16px auto;
  border-radius: 12px;
  border: 1px solid var(--ctp-surface0);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  text-align: left;
}

/* Card metadata styling */
.card-type {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--ctp-mauve);
  background-color: var(--ctp-surface0);
  padding: 4px 10px;
  border-radius: 20px;
  margin-bottom: 8px;
  border: 1px solid var(--ctp-surface1);
}

.source {
  font-size: 0.85rem;
  color: var(--ctp-subtext0);
  margin-bottom: 12px;
  font-weight: 500;
}

hr {
  border: 0;
  height: 1px;
  background: var(--ctp-surface1);
  margin: 20px 0;
}

.question, .cloze-text, .answer, .explanation {
  font-size: 1.05rem;
  line-height: 1.6;
}

.explanation {
  margin-top: 20px;
  font-size: 0.95rem;
  color: var(--ctp-subtext1);
  background-color: var(--ctp-surface0);
  padding: 14px 18px;
  border-left: 4px solid var(--ctp-blue);
  border-radius: 4px;
}

.cloze {
  color: var(--ctp-blue) !important;
  font-weight: bold !important;
}

/* MCQ Options styling */
.options {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option {
  padding: 12px 16px;
  background-color: var(--ctp-surface0);
  border: 1px solid var(--ctp-surface1);
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 1rem;
}

.option-letter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background-color: var(--ctp-surface2);
  border-radius: 50%;
  font-weight: bold;
  font-size: 0.85rem;
  color: var(--ctp-text);
  flex-shrink: 0;
}

/* MCQ Answer Revealed Styling */
.options.answer-revealed .option {
  opacity: 0.6;
}

.correct-answer-badge {
  display: inline-block;
  margin-top: 14px;
  padding: 6px 14px;
  background-color: rgba(166, 227, 161, 0.12);
  border: 1px solid var(--ctp-green);
  color: var(--ctp-green);
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.9rem;
}

/* Typography, lists & formatting */
h1, h2, h3, h4, h5, h6 {
  color: var(--ctp-lavender);
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

h1 { font-size: 1.5rem; }
h2 { font-size: 1.35rem; }
h3 { font-size: 1.2rem; }

p {
  margin-top: 0;
  margin-bottom: 1em;
}

ul, ol {
  margin-top: 0;
  margin-bottom: 1em;
  padding-left: 24px;
}

li {
  margin-bottom: 0.4em;
}

a {
  color: var(--ctp-blue);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

/* Monospace code styling */
pre, code {
  font-family: "JetBrains Mono", "Fira Code", "Courier New", Courier, monospace;
}

code {
  background-color: var(--ctp-surface1);
  color: var(--ctp-peach);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

pre {
  background-color: var(--ctp-surface0);
  border: 1px solid var(--ctp-surface1);
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

pre code {
  background-color: transparent;
  color: var(--ctp-text);
  padding: 0;
  border-radius: 0;
  font-size: 0.9em;
}

/* Tables styling */
table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
  font-size: 0.95rem;
}

th, td {
  border: 1px solid var(--ctp-surface1);
  padding: 10px 14px;
  text-align: left;
}

th {
  background-color: var(--ctp-surface0);
  color: var(--ctp-blue);
  font-weight: 600;
}

tr:nth-child(even) {
  background-color: rgba(255, 255, 255, 0.02);
}

/* Mobile adjustments */
@media (max-width: 600px) {
  .card {
    padding: 16px;
    margin: 8px auto;
  }
  .option {
    padding: 10px 12px;
  }
}
"""

# Global ID collision tracking registry
generated_ids = {}
used_ids = set()


def reset_id_registry():
    """Resets the ID registry. Helpful for unit tests."""
    global generated_ids, used_ids
    generated_ids.clear()
    used_ids.clear()


def generate_id(name: str) -> int:
    """
    Generates a deterministic 52-bit positive integer by hashing the input name
    using MD5, taking the first 13 hex characters, and parsing as base-16.
    If the name has already been registered, returns the same ID.
    Resolves hash value collisions by incrementing by 1 and logging a warning.
    """
    global generated_ids, used_ids
    # Coerce to string to avoid errors on None or non-string inputs
    name_str = str(name)
    if name_str in generated_ids:
        return generated_ids[name_str]

    h = hashlib.md5(name_str.encode("utf-8")).hexdigest()
    # First 13 hex characters = 52 bits. Fits safely under JS 2^53 - 1 ceiling
    # and satisfies Anki's requirements for positive 64-bit integer IDs.
    val = int(h[:13], 16)

    # Collision resolution for different names hashing to the same value
    if val in used_ids:
        orig_val = val
        while val in used_ids:
            val += 1
        print(
            f"Warning: ID collision detected for '{name_str}' (computed: {orig_val}). Incremented to {val}.",
            file=sys.stderr,
        )

    used_ids.add(val)
    generated_ids[name_str] = val
    return val


def normalize_tag(value: str) -> str:
    """Normalizes tag value by stripping all whitespace characters."""
    if not isinstance(value, str):
        return ""
    # Strip all whitespace characters to conform to Anki's space-separated tags format
    return re.sub(r"\s+", "", value)


def render_markdown(text: str, inline: bool = False) -> str:
    """
    Converts markdown text to HTML, then sanitizes it against the allowed whitelist.
    If inline is True, strips wrapping <p> tags from the output.
    """
    if not isinstance(text, str):
        return ""

    # Convert markdown to HTML using fenced_code and tables extensions
    html = markdown.markdown(text, extensions=["fenced_code", "tables"])

    # Sanitize HTML using bleach
    sanitized = bleach.clean(
        html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True
    )

    if inline:
        # Strip wrapping <p> and </p> tags only if it is a single paragraph,
        # preventing slicing off outer tags from multi-paragraph structures.
        s = sanitized.strip()
        if s.startswith("<p>") and s.endswith("</p>") and s.count("<p>") == 1:
            s = s[3:-4].strip()
        return s

    return sanitized


def shuffle_mcq_options(
    options: list[str], correct_answer: str
) -> tuple[list[str], str]:
    """
    Shuffles MCQ options while preserving the correct answer index mapping.
    Pads options list with fewer than 4 choices with empty strings.
    Returns: (shuffled_options, new_correct_answer_letter)
    """
    # Enforce safe type handling for choices list
    if not isinstance(options, (list, tuple)):
        options = []
    else:
        options = [str(o) for o in options if o is not None]

    # Enforce safe type handling for correct answer letter
    if not isinstance(correct_answer, str):
        correct_answer = "A"

    # Map correct answer letter to index (A->0, B->1, C->2, D->3)
    correct_letter = correct_answer.upper()
    correct_idx = ord(correct_letter) - ord("A")

    # Fallback to first option if the correct index is out of bounds
    if correct_idx < 0 or correct_idx >= len(options):
        correct_idx = 0

    # Bundle each option with its original index to prevent loss of correct answer mapping
    # when options contain duplicate values (standard list.index() would only find the first one).
    indexed_options = list(enumerate(options))
    random.shuffle(indexed_options)

    shuffled_texts = []
    new_correct_idx = 0
    for new_idx, (orig_idx, text) in enumerate(indexed_options):
        if orig_idx == correct_idx:
            new_correct_idx = new_idx
        shuffled_texts.append(text)

    # Pad to exactly 4 choices since MCQ card templates strictly expect OptionA through OptionD
    while len(shuffled_texts) < 4:
        shuffled_texts.append("")

    # Map new index back to letter
    new_correct_answer_letter = chr(ord("A") + new_correct_idx)

    return shuffled_texts, new_correct_answer_letter


def build_tags(
    card: dict, topic_data: dict, source: str = None, subject: str = None
) -> list[str]:
    """
    Builds the set of tags for the note including card-level tags and hierarchical taxonomy tags:
    - topic::<normalized_topic_name>
    - difficulty::<normalized_difficulty_level>
    - type::<normalized_card_type>
    - source::<normalized_source_file_name>
    - subject::<normalized_folder_path>
    """
    # Safe handling if card or topic_data are not dicts
    if not isinstance(card, dict):
        card = {}
    if not isinstance(topic_data, dict):
        topic_data = {}

    tags_list = []

    # 1. Topic Tag
    topic = topic_data.get("topic", "DefaultTopic")
    tags_list.append(f"topic::{normalize_tag(topic)}")

    # 2. Difficulty Tag
    difficulty = topic_data.get("difficulty", "Unknown")
    tags_list.append(f"difficulty::{normalize_tag(difficulty)}")

    # 3. Type Tag
    card_type = card.get("card_type", "Concept")
    tags_list.append(f"type::{normalize_tag(card_type)}")

    # 4. Source Tag
    if source:
        # Use provided source name
        tags_list.append(f"source::{normalize_tag(source)}")
    else:
        # Fallback to title
        title = topic_data.get("title", "DefaultTitle")
        tags_list.append(f"source::{normalize_tag(title)}")

    # 5. Subject Tag
    if subject:
        tags_list.append(f"subject::{normalize_tag(subject)}")

    # 6. Card-level tags
    card_tags = card.get("tags", [])
    if isinstance(card_tags, list):
        for tag in card_tags:
            if tag:
                tags_list.append(normalize_tag(str(tag)))

    # Dedup tags list while preserving relative order
    unique_tags = []
    for tag in tags_list:
        if tag and tag not in unique_tags:
            unique_tags.append(tag)

    return unique_tags


def _load_json_data(json_data, source: str = None) -> tuple[list, str]:
    """
    Loads and normalizes JSON input into a list of topic dictionaries.
    Handles both file paths and in-memory data structures.
    Returns: (topics_list, resolved_source_name)
    """
    if isinstance(json_data, str):
        with open(json_data, "r", encoding="utf-8") as f:
            data = json.load(f)
        # If source is not explicitly specified, derive it from the input filename
        if not source:
            base = os.path.basename(json_data)
            source = os.path.splitext(base)[0]
    else:
        data = json_data

    # Wrap in a list if it is a single dictionary (object) to normalize processing
    # of both single-topic and multi-topic merged JSON data structures.
    topics = data if isinstance(data, list) else [data]
    return topics, source


def _resolve_deck_name(topics: list, deck_name: str = None) -> str:
    """
    Determines the deck name. If not explicitly specified by CLI arguments,
    defaults to the topic name for single-topic runs, or a generic name for multi-topic runs.
    """
    if deck_name:
        return deck_name
    if len(topics) == 1 and isinstance(topics[0], dict):
        return topics[0].get("topic", "LLM2Deck Compiled")
    return "LLM2Deck Compiled"


def _create_models() -> tuple[genanki.Model, genanki.Model, genanki.Model]:
    """
    Creates and returns the three genanki Model objects (Basic, Cloze, MCQ)
    with deterministic IDs and the Catppuccin Mocha CSS theme.
    """
    basic_model = genanki.Model(
        generate_id("LLM2Deck Basic Model"),
        "LLM2Deck Basic Model",
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
        templates=[
            {
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
        ],
        css=CARD_CSS,
    )

    cloze_model = genanki.Model(
        generate_id("LLM2Deck Cloze Model"),
        "LLM2Deck Cloze Model",
        fields=[
            {"name": "Front"},
            {"name": "Explanation"},
            {"name": "CardType"},
            {"name": "Topic"},
            {"name": "Problem"},
            {"name": "Difficulty"},
            {"name": "Tags"},
        ],
        templates=[
            {
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
        ],
        css=CARD_CSS,
        model_type=genanki.Model.CLOZE,
    )

    mcq_model = genanki.Model(
        generate_id("LLM2Deck MCQ Model"),
        "LLM2Deck MCQ Model",
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
        templates=[
            {
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
        ],
        css=CARD_CSS,
    )

    return basic_model, cloze_model, mcq_model


def _create_note_for_card(
    card: dict,
    topic_data: dict,
    models: tuple[genanki.Model, genanki.Model, genanki.Model],
    deck_name: str,
    source: str = None,
    subject: str = None,
) -> genanki.Note | None:
    """
    Creates a genanki Note for a single card dictionary, selecting the appropriate
    model based on card_format. Returns None for unsupported formats (with a warning).
    """
    basic_model, cloze_model, mcq_model = models

    card_format = card.get("card_format", "Basic")
    card_type = card.get("card_type", "Concept")

    # Extract topic-level metadata
    topic = topic_data.get("topic", "Default Topic")
    title = topic_data.get("title", "Default Title")
    difficulty = topic_data.get("difficulty", "Unknown")

    # Build card and taxonomy tags
    unique_tags = build_tags(card, topic_data, source=source, subject=subject)
    tags_str = " ".join(unique_tags)

    # Generate deterministic GUID based on card front and deck name to allow native update-in-place updates in Anki
    guid = genanki.guid_for(card.get("front", ""), deck_name)

    if card_format == "Basic":
        return genanki.Note(
            model=basic_model,
            fields=[
                render_markdown(card.get("front", "")),
                render_markdown(card.get("back", "")),
                render_markdown(card.get("explanation", "")),
                card_type,
                topic,
                title,
                difficulty,
                tags_str,
            ],
            tags=unique_tags,
            guid=guid,
        )

    if card_format == "Cloze":
        return genanki.Note(
            model=cloze_model,
            fields=[
                render_markdown(card.get("front", "")),
                render_markdown(card.get("explanation", "")),
                card_type,
                topic,
                title,
                difficulty,
                tags_str,
            ],
            tags=unique_tags,
            guid=guid,
        )

    if card_format == "MCQ":
        shuffled_options, new_correct_letter = shuffle_mcq_options(
            card.get("options", []), card.get("correct_answer", "A")
        )
        return genanki.Note(
            model=mcq_model,
            fields=[
                render_markdown(card.get("front", "")),
                render_markdown(shuffled_options[0], inline=True),
                render_markdown(shuffled_options[1], inline=True),
                render_markdown(shuffled_options[2], inline=True),
                render_markdown(shuffled_options[3], inline=True),
                new_correct_letter,
                render_markdown(card.get("explanation", "")),
                card_type,
                topic,
                title,
                difficulty,
                tags_str,
            ],
            tags=unique_tags,
            guid=guid,
        )

    print(
        f"Warning: Skipped card with unsupported format '{card_format}' (front snippet: '{card.get('front', '')[:30]}...').",
        file=sys.stderr,
    )
    return None


def compile_deck(
    json_data,
    output_path: str,
    deck_name: str = None,
    subject: str = None,
    source: str = None,
):
    """
    Main function to parse input JSON, generate notes, and compile to an Anki .apkg package.
    """
    topics, source = _load_json_data(json_data, source)
    deck_name = _resolve_deck_name(topics, deck_name)
    models = _create_models()

    deck_id = generate_id(deck_name)
    deck = genanki.Deck(deck_id, deck_name)

    for topic_data in topics:
        if not isinstance(topic_data, dict):
            continue

        cards = topic_data.get("cards")
        if not isinstance(cards, list):
            cards = []

        for card in cards:
            if not isinstance(card, dict):
                continue
            note = _create_note_for_card(card, topic_data, models, deck_name, source, subject)
            if note is not None:
                deck.add_note(note)

    # Save to file
    pkg = genanki.Package(deck)
    pkg.write_to_file(output_path)
    print(f"Successfully compiled {len(deck.notes)} cards into '{output_path}'")


def main():
    parser = argparse.ArgumentParser(
        description="Compile Stage 3 JSON cards into Anki .apkg deck."
    )
    parser.add_argument("json_file", help="Path to input Stage 3 JSON file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to output .apkg file. Defaults to <json_file_basename>.apkg.",
    )
    parser.add_argument(
        "--deck-name",
        help="Override the deck name. Defaults to the 'topic' field in JSON.",
    )
    parser.add_argument(
        "--subject",
        help="Subject metadata for taxonomy tagging (e.g. 'CS/Algorithms').",
    )
    parser.add_argument(
        "--source", help="Source filename override for taxonomy tagging."
    )

    args = parser.parse_args()

    if not os.path.exists(args.json_file):
        print(
            f"Error: Input JSON file '{args.json_file}' does not exist.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Determine default output path if not specified
    if not args.output:
        base = os.path.splitext(args.json_file)[0]
        args.output = f"{base}.apkg"

    try:
        compile_deck(
            json_data=args.json_file,
            output_path=args.output,
            deck_name=args.deck_name,
            subject=args.subject,
            source=args.source,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Compilation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
