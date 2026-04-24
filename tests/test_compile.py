import os
import sys
import json
import tempfile
import zipfile
import hashlib
import subprocess

# Ensure the project root is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from src.compile import (
    generate_id,
    reset_id_registry,
    normalize_tag,
    render_markdown,
    shuffle_mcq_options,
    build_tags,
    compile_deck,
)


def test_generate_id_deterministic():
    """1. Test that the same input always produces the same ID."""
    reset_id_registry()
    id1 = generate_id("deck_name_1")
    id2 = generate_id("deck_name_1")
    assert id1 == id2


def test_generate_id_52bit_range():
    """2. Test that the generated ID is a positive integer under 2^53 - 1 (JS safe integer ceiling)."""
    reset_id_registry()
    for name in ["deck1", "modelA", "random_test_string", "nested::deck::path"]:
        val = generate_id(name)
        assert val > 0
        assert val < 2**53 - 1


def test_generate_id_different_inputs():
    """3. Test that different names produce different IDs."""
    reset_id_registry()
    id1 = generate_id("deck_name_1")
    id2 = generate_id("deck_name_2")
    assert id1 != id2


def test_generate_id_collision_resolution():
    """4. Test that if a collision occurs, the ID is incremented by 1 and a warning is logged."""
    reset_id_registry()

    # Calculate the ID that "test_collision" would generate
    h = hashlib.md5("test_collision".encode("utf-8")).hexdigest()
    expected_val = int(h[:13], 16)

    # Pre-register this expected value to force a collision
    import src.compile

    src.compile.used_ids.add(expected_val)

    # Generate the ID. It should resolve the collision by incrementing by 1
    new_val = generate_id("test_collision")
    assert new_val == expected_val + 1


def test_shuffle_mcq_options_correctness():
    """5. Test that the correct answer text maps correctly to the new letter after shuffling."""
    options = ["Choice A", "Choice B", "Choice C"]
    correct_answer = "B"  # corresponds to "Choice B"

    # Run multiple times to ensure randomness works and correct text remains mapped
    for _ in range(20):
        shuffled, new_correct_letter = shuffle_mcq_options(options, correct_answer)

        # New letter to index
        new_idx = ord(new_correct_letter.upper()) - ord("A")
        assert shuffled[new_idx] == "Choice B"


def test_shuffle_mcq_options_padding():
    """6. Test that 2 or 3 choices are padded to exactly 4 with empty strings."""
    options = ["Opt1", "Opt2"]
    shuffled, new_letter = shuffle_mcq_options(options, "A")
    assert len(shuffled) == 4
    assert shuffled[0] != ""
    assert shuffled[1] != ""
    assert shuffled[2] == ""
    assert shuffled[3] == ""


def test_shuffle_mcq_preserves_all_options():
    """7. Test that all original option texts are preserved in the shuffled options."""
    options = ["Choice X", "Choice Y", "Choice Z"]
    shuffled, new_letter = shuffle_mcq_options(options, "C")

    active_opts = [o for o in shuffled if o != ""]
    assert set(active_opts) == set(options)


def test_render_markdown_code_blocks():
    """8. Test that markdown fenced code blocks are formatted into HTML <pre><code> structures."""
    markdown_text = "Here is some code:\n```python\ndef test():\n    return True\n```"
    html = render_markdown(markdown_text)

    assert "<pre>" in html
    assert "<code" in html
    assert "def test():" in html
    assert 'class="language-python"' in html


def test_render_markdown_sanitization():
    """9. Test that tags outside the whitelist (e.g. <script>) are stripped."""
    malicious_text = "Good text <script>alert(1)</script> <iframe src='google.com'></iframe> **Bold**"
    html = render_markdown(malicious_text)

    assert "<script>" not in html
    assert "<iframe>" not in html
    assert "<strong>Bold</strong>" in html


def test_tag_injection():
    """10. Verify hierarchical tags are correctly generated and normalized."""
    card = {"card_type": "Trade Off", "tags": ["tag_a", "tag b"]}
    topic_data = {"topic": "Topic A", "difficulty": "Easy", "title": "Title Z"}

    tags = build_tags(card, topic_data, source="Source file", subject="Subject dir")

    # Check taxonomy tags normalized properly
    assert "topic::TopicA" in tags
    assert "difficulty::Easy" in tags
    assert "type::TradeOff" in tags
    assert "source::Sourcefile" in tags
    assert "subject::Subjectdir" in tags
    # Check card tag normalized properly
    assert "tag_a" in tags
    assert "tagb" in tags


def test_compile_basic_card_apkg():
    """11. Test end-to-end compilation of a Basic card type JSON to a valid .apkg file."""
    reset_id_registry()
    data = {
        "title": "Valid Palindrome",
        "topic": "Two Pointers",
        "difficulty": "Easy",
        "cards": [
            {
                "card_format": "Basic",
                "card_type": "Concept",
                "tags": ["string"],
                "front": "What is a **palindrome**?",
                "back": "A sequence that reads the same backward as forward.",
                "explanation": "Example: `racecar`.",
            }
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "basic.json")
        apkg_path = os.path.join(tmpdir, "basic.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        compile_deck(json_path, apkg_path)

        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0

        # Verify Anki zip format integrity
        with zipfile.ZipFile(apkg_path, "r") as zf:
            namelist = zf.namelist()
            assert "collection.anki2" in namelist


def test_compile_cloze_card_apkg():
    """12. Test Cloze card compilation to .apkg."""
    reset_id_registry()
    data = {
        "title": "Valid Palindrome",
        "topic": "Two Pointers",
        "difficulty": "Easy",
        "cards": [
            {
                "card_format": "Cloze",
                "card_type": "Syntax",
                "tags": ["string"],
                "front": "A palindrome is a sequence that reads the {{c1::same}} backward as forward.",
                "explanation": "Example: `racecar`.",
            }
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "cloze.json")
        apkg_path = os.path.join(tmpdir, "cloze.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        compile_deck(json_path, apkg_path)

        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0

        with zipfile.ZipFile(apkg_path, "r") as zf:
            namelist = zf.namelist()
            assert "collection.anki2" in namelist


def test_compile_mcq_card_apkg():
    """13. Test MCQ card compilation to .apkg."""
    reset_id_registry()
    data = {
        "title": "Valid Palindrome",
        "topic": "Two Pointers",
        "difficulty": "Easy",
        "cards": [
            {
                "card_format": "MCQ",
                "card_type": "QA",
                "tags": ["string"],
                "front": "Which of the following is a palindrome?",
                "options": ["hello", "racecar", "world"],
                "correct_answer": "B",
                "explanation": "`racecar` spelled backwards is `racecar`.",
            }
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "mcq.json")
        apkg_path = os.path.join(tmpdir, "mcq.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        compile_deck(json_path, apkg_path)

        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0

        with zipfile.ZipFile(apkg_path, "r") as zf:
            namelist = zf.namelist()
            assert "collection.anki2" in namelist


def test_compile_mixed_cards():
    """14. Test deck compilation containing multiple card types (Basic, Cloze, MCQ) in one run."""
    reset_id_registry()
    data = {
        "title": "Mixed LeetCode Problems",
        "topic": "Mixed Topic",
        "difficulty": "Medium",
        "cards": [
            {
                "card_format": "Basic",
                "card_type": "Concept",
                "tags": ["basic"],
                "front": "Basic front",
                "back": "Basic back",
                "explanation": "Basic explanation",
            },
            {
                "card_format": "Cloze",
                "card_type": "Syntax",
                "tags": ["cloze"],
                "front": "Cloze {{c1::deletion}} here.",
                "explanation": "Cloze explanation",
            },
            {
                "card_format": "MCQ",
                "card_type": "QA",
                "tags": ["mcq"],
                "front": "MCQ front question?",
                "options": ["opt1", "opt2", "opt3", "opt4"],
                "correct_answer": "D",
                "explanation": "MCQ explanation",
            },
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "mixed.json")
        apkg_path = os.path.join(tmpdir, "mixed.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        compile_deck(json_path, apkg_path)

        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0

        with zipfile.ZipFile(apkg_path, "r") as zf:
            namelist = zf.namelist()
            assert "collection.anki2" in namelist


def test_cli_entrypoint():
    """15. Test calling compile.py from the CLI to confirm argument parsing and subprocess execution work."""
    data = {
        "title": "CLI Test Problem",
        "topic": "CLI Topic",
        "difficulty": "Hard",
        "cards": [
            {
                "card_format": "Basic",
                "card_type": "Procedure",
                "tags": ["cli"],
                "front": "Run via CLI",
                "back": "Success",
                "explanation": "Test verification",
            }
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "cli_test.json")
        apkg_path = os.path.join(tmpdir, "cli_test.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        cmd = [
            sys.executable,
            "src/compile.py",
            json_path,
            "-o",
            apkg_path,
            "--deck-name",
            "CLI Customized Deck Name",
            "--subject",
            "CS::Testing",
            "--source",
            "CLI_Test_Suite",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # If there's stderr or returncode is non-zero, print for debugging
        if result.returncode != 0:
            print("CLI execution failed.")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

        assert result.returncode == 0
        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0


def test_render_markdown_empty_or_non_string():
    """16. Verify that render_markdown returns empty string for null/None or non-string inputs."""
    assert render_markdown(None) == ""
    assert render_markdown(123) == ""
    assert render_markdown({"a": 1}) == ""


def test_normalize_tag_empty_or_non_string():
    """17. Verify that normalize_tag returns empty string for null/None or non-string inputs."""
    assert normalize_tag(None) == ""
    assert normalize_tag(123) == ""


def test_normalize_tag_whitespace_variations():
    """18. Verify that tag normalization handles tabs, newlines, and multiple spaces properly."""
    assert normalize_tag("  word1\tword2\nword3  ") == "word1word2word3"


def test_generate_id_none_or_non_string():
    """19. Verify generate_id functions correctly with None or non-string inputs."""
    reset_id_registry()
    id_none = generate_id(None)
    id_empty = generate_id("")
    assert id_none > 0
    assert id_empty > 0
    assert id_none != id_empty


def test_shuffle_mcq_options_empty_or_none_options():
    """20. Verify shuffle_mcq_options handles null options or empty options list safely."""
    shuffled, new_letter = shuffle_mcq_options(None, "A")
    assert len(shuffled) == 4
    assert all(opt == "" for opt in shuffled)
    assert new_letter == "A"

    shuffled2, new_letter2 = shuffle_mcq_options("not a list", "B")
    assert len(shuffled2) == 4
    assert all(opt == "" for opt in shuffled2)
    assert new_letter2 == "A"  # Default correct letter fallback


def test_shuffle_mcq_options_non_string_correct_answer():
    """21. Verify shuffle_mcq_options defaults correctly when correct_answer is not a string."""
    options = ["OptA", "OptB", "OptC"]
    shuffled, new_letter = shuffle_mcq_options(options, None)
    new_idx = ord(new_letter) - ord("A")
    assert shuffled[new_idx] == "OptA"

    shuffled2, new_letter2 = shuffle_mcq_options(options, 123)
    new_idx2 = ord(new_letter2) - ord("A")
    assert shuffled2[new_idx2] == "OptA"


def test_shuffle_mcq_options_duplicate_texts():
    """22. Verify MCQ shuffling resolves correct answer mapping correctly when options contain duplicate values."""
    options = ["duplicate", "duplicate", "different"]
    correct_answer = "B"

    for _ in range(20):
        shuffled, new_letter = shuffle_mcq_options(options, correct_answer)
        new_idx = ord(new_letter) - ord("A")
        assert shuffled[new_idx] == "duplicate"


def test_build_tags_invalid_input_dicts():
    """23. Verify build_tags handles non-dict parameters safely without throwing exceptions."""
    tags = build_tags(None, None)
    assert isinstance(tags, list)
    assert len(tags) > 0


def test_compile_deck_null_cards():
    """24. Verify compile_deck handles JSON data with null or missing cards gracefully."""
    data_null_cards = {
        "title": "Null Cards Problem",
        "topic": "Empty Topic",
        "difficulty": "Easy",
        "cards": None,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        apkg_path = os.path.join(tmpdir, "null_cards.apkg")
        compile_deck(data_null_cards, apkg_path)
        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0


def test_render_markdown_attribute_sanitization():
    """25. Verify that whitelisted HTML tags are kept, but disallowed attributes are stripped."""
    html_input = '<a href="https://example.com" class="my-link" onclick="runHack()" style="color: red">Google</a>'
    html_output = render_markdown(html_input, inline=True)

    assert 'href="https://example.com"' in html_output
    assert 'class="my-link"' in html_output
    assert "onclick" not in html_output
    assert "style" not in html_output


def test_render_markdown_multi_paragraph_inline_no_peel():
    """26. Verify that inline=True does NOT strip outer <p> tags for multi-paragraph content."""
    multi_p_input = "Paragraph 1\n\nParagraph 2"
    html_output = render_markdown(multi_p_input, inline=True)
    assert "<p>Paragraph 1</p>" in html_output
    assert "<p>Paragraph 2</p>" in html_output


def test_compile_deck_unsupported_card_format(capsys):
    """27. Verify that cards with unsupported formats are skipped and log warnings to stderr."""
    data = {
        "title": "Unsupported Format Problem",
        "topic": "Format Topic",
        "difficulty": "Easy",
        "cards": [
            {
                "card_format": "Basic",
                "card_type": "Concept",
                "front": "Valid front",
                "back": "Valid back",
            },
            {
                "card_format": "UnknownFormat",
                "card_type": "Concept",
                "front": "Invalid card format",
                "back": "Should skip",
            },
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        apkg_path = os.path.join(tmpdir, "unsupported_format.apkg")
        compile_deck(data, apkg_path)

        captured = capsys.readouterr()
        assert (
            "Warning: Skipped card with unsupported format 'UnknownFormat'"
            in captured.err
        )
        assert os.path.exists(apkg_path)


def test_compile_multiple_topics_in_list():
    """28. Verify that compiling a list of multiple topic JSON objects runs successfully."""
    reset_id_registry()
    data = [
        {
            "title": "Topic One Title",
            "topic": "Topic One",
            "difficulty": "Easy",
            "cards": [
                {
                    "card_format": "Basic",
                    "card_type": "Concept",
                    "tags": ["tag1"],
                    "front": "Topic 1 Front",
                    "back": "Topic 1 Back",
                    "explanation": "Topic 1 Explanation",
                }
            ],
        },
        {
            "title": "Topic Two Title",
            "topic": "Topic Two",
            "difficulty": "Medium",
            "cards": [
                {
                    "card_format": "Basic",
                    "card_type": "Concept",
                    "tags": ["tag2"],
                    "front": "Topic 2 Front",
                    "back": "Topic 2 Back",
                    "explanation": "Topic 2 Explanation",
                }
            ],
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "multi.json")
        apkg_path = os.path.join(tmpdir, "multi.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        compile_deck(json_path, apkg_path)

        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0

        with zipfile.ZipFile(apkg_path, "r") as zf:
            namelist = zf.namelist()
            assert "collection.anki2" in namelist


def test_compile_empty_topic_list():
    """29. Verify that compiling an empty list runs successfully and writes an empty package."""
    reset_id_registry()
    data = []

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "empty_list.json")
        apkg_path = os.path.join(tmpdir, "empty_list.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        compile_deck(json_path, apkg_path)

        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0


def test_compile_topic_list_with_invalid_items():
    """30. Verify that list elements that are not dicts are skipped gracefully."""
    reset_id_registry()
    data = [
        None,
        12345,
        "not a dict",
        {
            "title": "Valid Topic Title",
            "topic": "Valid Topic",
            "difficulty": "Easy",
            "cards": [
                {
                    "card_format": "Basic",
                    "card_type": "Concept",
                    "tags": ["tag"],
                    "front": "Q",
                    "back": "A",
                    "explanation": "Exp",
                }
            ],
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "invalid_items.json")
        apkg_path = os.path.join(tmpdir, "invalid_items.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        compile_deck(json_path, apkg_path)

        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0


def test_compile_topic_list_missing_cards_field():
    """31. Verify that topic objects with missing or null cards array are tolerated."""
    reset_id_registry()
    data = [
        {
            "title": "No Cards Topic",
            "topic": "No Cards",
            "difficulty": "Easy",
            # cards field is completely missing
        },
        {
            "title": "Null Cards Topic",
            "topic": "Null Cards",
            "difficulty": "Easy",
            "cards": None,
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "missing_cards.json")
        apkg_path = os.path.join(tmpdir, "missing_cards.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        compile_deck(json_path, apkg_path)

        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0


def test_compile_topic_list_custom_deck_name():
    """32. Verify that custom deck name overrides the default deck name for list compilation."""
    reset_id_registry()
    data = [
        {
            "title": "Title",
            "topic": "Topic A",
            "difficulty": "Easy",
            "cards": [],
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "custom_name.json")
        apkg_path = os.path.join(tmpdir, "custom_name.apkg")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        compile_deck(json_path, apkg_path, deck_name="Overridden Deck Name")

        assert os.path.exists(apkg_path)
        assert os.path.getsize(apkg_path) > 0


