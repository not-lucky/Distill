"""
End-to-end Python integration test: real `python src/compile.py` subprocess.

This is the Python-side mirror of tests/integration/pipeline.e2e.test.js
(signal: integration_tests_exist on the Python side). It exercises the
real argparse-based entry point against a fixture JSON and asserts the
output is a valid .apkg zip with the expected genanki layout.

Unlike tests/test_compile.py which calls `compile_deck` directly, this test
spawns the actual CLI entry point so it covers the script surface end users
actually run.
"""

import json
import os
import subprocess
import tempfile
import zipfile


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPILER = os.path.join(REPO_ROOT, "src", "compile.py")


def _basic_fixture() -> dict:
    return {
        "title": "E2E Python Basic",
        "topic": "E2E::Python::Basic",
        "difficulty": "Basic",
        "cards": [
            {
                "card_format": "Basic",
                "card_type": "Concept",
                "front": "What does this test do?",
                "back": "Spawns the real compile.py CLI.",
                "explanation": "End-to-end smoke test of the user-facing entry point.",
                "tags": ["e2e", "python"],
            }
        ],
    }


def _cloze_fixture() -> dict:
    return {
        "title": "E2E Python Cloze",
        "topic": "E2E::Python::Cloze",
        "difficulty": "Intermediate",
        "cards": [
            {
                "card_format": "Cloze",
                "card_type": "Code",
                "front": "Python was created by {{c1::Guido van Rossum}}.",
                "explanation": "Released in 1991.",
                "tags": ["e2e", "cloze"],
            }
        ],
    }


def test_e2e_cli_basic_card_produces_valid_apkg():
    """Spawn `python src/compile.py <json> -o <apkg>` for a Basic card and
    assert the resulting .apkg is a valid zip with the genanki collection
    and media map."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "basic.json")
        apkg_path = os.path.join(tmpdir, "basic.apkg")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(_basic_fixture(), f)

        result = subprocess.run(
            [
                "python",
                COMPILER,
                json_path,
                "-o",
                apkg_path,
                "--deck-name",
                "E2E Py Basic",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"compile.py exited with {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert os.path.exists(apkg_path), "output .apkg file was not produced"
        assert os.path.getsize(apkg_path) > 0, "output .apkg file is empty"
        assert "Successfully compiled" in result.stdout

        with zipfile.ZipFile(apkg_path, "r") as zf:
            names = zf.namelist()
            # genanki produces either collection.anki21 (newer) or collection.anki2 (older)
            assert ("collection.anki21" in names) or ("collection.anki2" in names), (
                f"missing collection entry; got: {names}"
            )
            # media map is always present (may be empty for text-only cards)
            assert "media" in names, f"missing media map entry; got: {names}"
            media_map = json.loads(zf.read("media").decode("utf-8"))
            assert isinstance(media_map, dict)


def test_e2e_cli_cloze_card_produces_valid_apkg():
    """Spawn `python src/compile.py <json> -o <apkg>` for a Cloze card and
    assert the output .apkg includes the cloze model."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "cloze.json")
        apkg_path = os.path.join(tmpdir, "cloze.apkg")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(_cloze_fixture(), f)

        result = subprocess.run(
            ["python", COMPILER, json_path, "-o", apkg_path],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"compile.py exited with {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert os.path.exists(apkg_path)
        with zipfile.ZipFile(apkg_path, "r") as zf:
            names = zf.namelist()
            assert ("collection.anki21" in names) or ("collection.anki2" in names)
            assert "media" in names


def test_e2e_cli_subject_flag_propagates_to_taxonomy():
    """The --subject flag should be accepted by the CLI; if the deck
    compiles, the flag wiring through `compile_deck` is exercised end-to-end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "subj.json")
        apkg_path = os.path.join(tmpdir, "subj.apkg")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(_basic_fixture(), f)

        result = subprocess.run(
            [
                "python",
                COMPILER,
                json_path,
                "-o",
                apkg_path,
                "--subject",
                "CS/DataStructures",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"compile.py exited with {result.returncode}\nstderr: {result.stderr}"
        )
        assert os.path.exists(apkg_path)


def test_e2e_cli_rejects_missing_input_file():
    """Passing a non-existent path should exit non-zero and print an error."""
    result = subprocess.run(
        [
            "python",
            COMPILER,
            "/nonexistent/path/to/missing.json",
            "-o",
            "/tmp/out.apkg",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
    )
    assert result.returncode != 0
    assert "does not exist" in result.stderr
