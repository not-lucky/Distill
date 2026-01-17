# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM2Deck generates Anki flashcards using multiple LLMs in parallel. It supports three subjects (LeetCode, CS, Physics) with standard Q&A and MCQ formats. The system uses a two-stage process: parallel generation across providers, then combination into a final deck.

## Commands

```bash
# Setup
uv sync

# Generate cards
uv run main.py                              # LeetCode standard (default)
uv run main.py <subject> [mcq] [--label=X]  # subject: leetcode, cs, physics

# Convert to Anki package
uv run convert_to_apkg.py <file>.json       # auto-detects mode from filename
uv run convert_to_apkg.py <file>.json --mode cs_mcq

# Utilities
uv run merge_anki_json.py <subject>         # merge archived JSONs
uv run json_to_md.py                        # export to Markdown
```

## Architecture

### Generation Flow

1. `main.py` initializes providers via `src/setup.py` and creates a database Run
2. For each question, `CardGenerator` (`src/generator.py`) spawns parallel requests to all providers
3. Each provider returns initial cards, saved as `ProviderResult` entries
4. First provider combines all results into final cards
5. Final cards saved to JSON and database (`Problem`, `Card` entries)

### Provider System

**Hierarchy:**
- `LLMProvider` (`src/providers/base.py`) - abstract base defining `generate_initial_cards()` and `combine_cards()`
- `OpenAICompatibleProvider` (`src/providers/openai_compatible.py`) - shared implementation for OpenAI-compatible APIs
- Concrete providers (nvidia, openrouter, canopywave, baseten) extend `OpenAICompatibleProvider`

**Adding a new OpenAI-compatible provider:**
```python
# src/providers/my_provider.py
class MyProvider(OpenAICompatibleProvider):
    def __init__(self, api_keys: Iterator[str], model: str):
        super().__init__(
            model=model,
            base_url="https://api.example.com/v1",
            api_keys=api_keys,
        )

    @property
    def name(self) -> str:
        return "my_provider"
```

Then add initialization in `src/setup.py` and key config in `src/config/keys.py`.

### Subject Configuration

`SubjectRegistry` in `src/config/subjects.py` maps subjects to:
- Prompt templates (from `src/data/prompts/`)
- Pydantic models (card structure validation)
- Questions (from `src/data/questions.json`)

### Question Organization

Questions in `src/data/questions.json` use a categorized format:
```json
{
  "leetcode": {
    "Binary Search": ["Binary Search", "Search a 2D Matrix"],
    "Two Pointers": ["Valid Palindrome", "3Sum"]
  }
}
```

This produces numbered hierarchical Anki decks: `LeetCode::001 Binary Search::001 Binary Search`

### Database

SQLite database `llm2deck.db` tracks:
- `runs` - execution metadata and statistics
- `problems` - individual questions processed
- `provider_results` - raw LLM outputs before combination
- `cards` - final individual cards

Query utilities in `src/queries.py`.

### Anki Generation

`src/anki/` converts JSON to `.apkg`:
- `generator.py` - `DeckGenerator` creates genanki decks with hierarchy
- `models.py` - Anki note models (card templates)
- `renderer.py` - Markdown to HTML with syntax highlighting
- `styles.py` - Catppuccin theme CSS

## Key Files

| Purpose | Files |
|---------|-------|
| Entry points | `main.py`, `convert_to_apkg.py` |
| Provider init | `src/setup.py`, `src/config/keys.py` |
| Generation | `src/generator.py`, `src/prompts.py` |
| Config | `src/config/subjects.py`, `src/data/questions.json` |
| Prompts | `src/data/prompts/*.md` |

## Notes

- Most providers in `src/setup.py` are commented out. Active: `CerebrasProvider`, `GoogleAntigravityProvider`
- API keys stored in JSON files at project root (see README.md for format per provider)
- `CONCURRENT_REQUESTS` env var controls parallel question processing (default: 8)
- Mode naming: `<subject>` for standard, `<subject>_mcq` for MCQ (affects prompts and filenames)
