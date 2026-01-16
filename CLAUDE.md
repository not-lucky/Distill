# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM2Deck is a tool that generates high-quality Anki flashcards using Large Language Models. It supports three subjects (LeetCode, Computer Science, Physics) with both standard Q&A and MCQ formats. The system uses multiple LLM providers in parallel to generate diverse card perspectives, then combines them into a final deck.

## Common Commands

### Development Setup
```bash
# Install dependencies using uv (recommended)
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Running Card Generation
```bash
# Generate cards (default: LeetCode standard mode)
uv run main.py

# Generate with specific subject and type
uv run main.py <subject> [mcq] [--label=<name>]
# Examples:
uv run main.py leetcode          # LeetCode standard cards
uv run main.py cs mcq            # CS multiple choice questions
uv run main.py physics           # Physics standard cards
uv run main.py leetcode --label="binary-search-practice"
```

### Converting to Anki Packages
```bash
# Auto-detect mode from filename
uv run convert_to_apkg.py leetcode_anki_deck_20260101T131901.json

# Explicit mode specification
uv run convert_to_apkg.py output.json --mode cs_mcq
```

### Utility Commands
```bash
# Merge archived JSON files for a subject
uv run merge_anki_json.py leetcode

# Export cards to Markdown format
uv run json_to_md.py
```

## Architecture

### Core Generation Flow

The system follows a two-stage generation process:

1. **Parallel Generation**: Multiple LLM providers generate initial card sets simultaneously for the same question
2. **Combination**: A combiner provider merges all results into a final, comprehensive deck

This architecture ensures diverse perspectives and comprehensive coverage by leveraging multiple models.

### Provider System

All LLM providers inherit from `LLMProvider` (src/providers/base.py) and implement two key methods:

- `generate_initial_cards()`: Create initial card sets from a question
- `combine_cards()`: Merge multiple card sets into a final result

**Provider initialization** (`src/setup.py`):
- Loads API keys from JSON files in the project root
- Creates provider instances with cyclic key rotation
- Returns a list of active providers (first provider is used as combiner)

**Adding a new provider**:
1. Create a new file in `src/providers/` implementing `LLMProvider`
2. Add key loading logic to `src/setup.py`
3. Add provider instantiation in `initialize_providers()`
4. Update `.env` and key file documentation

### Database Integration

The system uses SQLite (llm2deck.db) to track all generation runs, problems, provider results, and individual cards.

**Key tables**:
- `runs`: Tracks each execution with mode, subject, status, and statistics
- `problems`: Individual questions processed within a run
- `provider_results`: Raw output from each LLM provider before combination
- `cards`: Final individual cards extracted from combined results

**Database workflow**:
1. `main.py` creates a Run entry at startup
2. For each question, a Problem entry is created
3. Each provider's output is saved as a ProviderResult
4. Final combined cards are saved to both Problem.final_result and individual Card entries
5. Run is updated with completion statistics

Use `src/queries.py` for filtering and retrieving data. The database enables analysis of provider performance, historical comparisons, and debugging failed generations.

### Subject Configuration

Subject-specific settings are centralized in `src/config/subjects.py` using `SubjectRegistry`:

```python
SubjectRegistry.get_config(subject_name, is_mcq=False)
```

Returns a `SubjectConfig` with:
- `prompt_template`: Subject-specific generation prompt
- `target_model`: Pydantic model defining card structure
- `target_questions`: Questions to process (from src/data/questions.json)

### Question Organization

Questions in `src/data/questions.json` use a **categorized dictionary format**:

```json
{
  "leetcode": {
    "Binary Search": ["Binary Search", "Search a 2D Matrix"],
    "Two Pointers": ["Valid Palindrome", "3Sum"]
  },
  "cs": {
    "Data Structures": ["Linked List, implementation..."],
    "Algorithms": ["Merge Sort"]
  }
}
```

This structure enables **numbered hierarchical decks** in Anki:
```
LeetCode::001 Binary Search::001 Binary Search
LeetCode::001 Binary Search::002 Search a 2D Matrix
LeetCode::002 Two Pointers::001 Valid Palindrome
```

The indexing is handled by `get_indexed_questions()` in `src/questions.py`, which returns tuples of `(category_index, category_name, problem_index, question)`.

### Anki Package Generation

The conversion from JSON to .apkg happens in `src/anki/`:

- **generator.py**: `DeckGenerator` reads JSON, creates genanki decks with proper hierarchy
- **models.py**: Defines Anki note models (card templates) for each mode
- **renderer.py**: Converts Markdown to HTML with syntax highlighting
- **styles.py**: CSS styling (Catppuccin theme for code blocks)

Mode auto-detection in `convert_to_apkg.py` parses the filename prefix (e.g., `cs_mcq_anki_deck_*.json` → `cs_mcq` mode).

## Key Files and Patterns

### Entry Points
- **main.py**: Primary entry point for card generation. Coordinates provider initialization, question processing, and database tracking.
- **convert_to_apkg.py**: CLI for JSON → Anki package conversion with mode auto-detection.
- **src/setup.py**: Provider initialization and API key management. Modify this to enable/disable specific providers.

### Configuration
- **.env**: Environment variables (CONCURRENT_REQUESTS, ENABLE_GEMINI, custom key file paths)
- **src/config/__init__.py**: Path resolution and environment loading
- **src/data/questions.json**: Source questions organized by category

### Generation Logic
- **src/generator.py**: `CardGenerator` orchestrates parallel generation and combining
- **src/prompts.py**: Prompt template loading utilities
- **src/data/prompts/**: Markdown files containing subject-specific prompts (initial*.md, combine*.md)

### Utilities
- **src/utils.py**: `save_final_deck()` for JSON export, filename sanitization
- **src/queries.py**: Database query utilities for filtering runs, problems, and cards
- **src/logging_config.py**: Logging setup with Rich console output

## Important Notes

### Provider Configuration
Most providers in `src/setup.py` are commented out by default. The active configuration uses `GoogleAntigravityProvider`. To use other providers (Cerebras, NVIDIA, Google GenAI, etc.), uncomment the relevant sections and ensure API keys are configured.

### API Key Formats
Different providers use different JSON key formats. See README.md table for exact format specifications. Keys are stored in JSON files at the project root (not in version control).

### Database Location
The SQLite database `llm2deck.db` is created at the project root. All generation history is preserved here, enabling historical analysis via `src/queries.py`.

### Concurrent Request Limit
Set via `CONCURRENT_REQUESTS` in .env (default: 8). Controls how many questions are processed in parallel during generation.

### Mode Naming Convention
Mode identifiers follow the pattern: `<subject>` for standard cards, `<subject>_mcq` for multiple choice questions. This affects prompt selection, model selection, and filename generation.
