# LLM2Deck

![Version](https://img.shields.io/badge/version-0.1.2-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

LLM2Deck generates high-quality Anki flashcards using multiple LLMs in parallel. It supports LeetCode problems, Computer Science concepts, and Physics topics, with both standard Q&A and MCQ formats.

## Features

- **Multi-Provider Architecture**: Run multiple LLM providers in parallel, then combine results for comprehensive coverage
- **Supported Providers**: Cerebras, NVIDIA, OpenRouter, Gemini (Web API), Google GenAI, Canopywave, Baseten, Google Antigravity, and G4F (experimental)
- **Three Subjects**:
  - **LeetCode**: Algorithm problems with code, complexity analysis, and approaches
  - **CS**: Deep-dive Computer Science concept cards
  - **Physics**: Definitions, formulas, and concept explanations
- **MCQ Support**: Multiple choice questions with shuffled options and explanations
- **Category-Based Organization**: Numbered hierarchical decks (e.g., `LeetCode::001 Binary Search::001 Two Sum`)
- **Rich Formatting**: Syntax highlighting (Catppuccin theme) and Markdown rendering
- **Database Tracking**: SQLite database stores all runs, provider outputs, and generated cards

## Prerequisites

- Python >= 3.12
- `uv` (recommended for dependency management)

## Installation

```bash
git clone <repository_url>
cd LLM2Deck
uv sync
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```ini
CONCURRENT_REQUESTS=5

# Custom key file paths (optional)
# CEREBRAS_KEYS_FILE_PATH=api_keys.json
# NVIDIA_KEYS_FILE_PATH=nvidia_keys.json
# OPENROUTER_KEYS_FILE_PATH=openrouter_keys.json
# GEMINI_CREDENTIALS_FILE_PATH=python3ds.json
# GOOGLE_GENAI_KEYS_FILE_PATH=google_genai_keys.json
# CANOPYWAVE_KEYS_FILE_PATH=canopywave_keys.json
# BASETEN_KEYS_FILE_PATH=baseten_keys.json

# Enable Gemini Web API (requires browser cookies)
# ENABLE_GEMINI=true
```

### API Keys

API keys are stored in JSON files at the project root:

| Provider     | File                     | Format                                              |
|--------------|--------------------------|-----------------------------------------------------|
| Cerebras     | `api_keys.json`          | `[{"api_key": "..."}]`                              |
| NVIDIA       | `nvidia_keys.json`       | `["key1", ...]` or `[{"api_key": "..."}]`           |
| OpenRouter   | `openrouter_keys.json`   | `[{"data": {"key": "..."}}]`                        |
| Gemini (Web) | `python3ds.json`         | `[{"Secure_1PSID": "...", "Secure_1PSIDTS": "..."}]`|
| Google GenAI | `google_genai_keys.json` | `["key1", ...]` or `[{"api_key": "..."}]`           |
| Canopywave   | `canopywave_keys.json`   | `["key1", ...]` or `[{"api_key": "..."}]`           |
| Baseten      | `baseten_keys.json`      | `["key1", ...]` or `[{"api_key": "..."}]`           |
| G4F          | N/A                      | No keys required (experimental)                     |

**Notes:**
- **Gemini (Web)**: Reverse-engineered browser cookies. Requires `ENABLE_GEMINI=true`.
- **Google GenAI**: Official Google API (recommended over Gemini Web).
- **Google Antigravity**: Local proxy, no authentication required.
- **G4F**: Uses [gpt4free](https://github.com/xtekky/gpt4free) for free model access.

### Questions

Questions are defined in `src/data/questions.json` using a categorized structure:

```json
{
    "leetcode": {
        "Binary Search": ["Binary Search", "Search a 2D Matrix"],
        "Two Pointers": ["Valid Palindrome", "3Sum"]
    },
    "cs": ["Linked List, implementation..."],
    "physics": ["Zeeman effect (normal)", "Zeeman effect (anomalous)"]
}
```

This generates numbered hierarchical Anki decks:
```
LeetCode
├── 001 Binary Search
│   ├── 001 Binary Search
│   └── 002 Search a 2D Matrix
└── 002 Two Pointers
    ├── 001 Valid Palindrome
    └── 002 3Sum
```

## Usage

### Generate Cards

```bash
# Default (LeetCode standard)
uv run main.py

# Specific subject
uv run main.py leetcode
uv run main.py cs
uv run main.py physics

# MCQ mode
uv run main.py physics mcq
uv run main.py cs mcq

# With label
uv run main.py leetcode --label="binary-search-practice"
```

Output: timestamped JSON file (e.g., `leetcode_anki_deck_20251227T140625.json`)

### Create Anki Package

```bash
# Auto-detect mode from filename
uv run convert_to_apkg.py leetcode_anki_deck_20251227T140625.json

# Explicit mode
uv run convert_to_apkg.py output.json --mode physics_mcq
```

**Valid modes:** `leetcode`, `cs`, `physics`, `leetcode_mcq`, `cs_mcq`, `physics_mcq`, `mcq`

### Utilities

```bash
# Merge archived JSON files
uv run merge_anki_json.py leetcode

# Export to Markdown
uv run json_to_md.py
```

## Project Structure

```
LLM2Deck/
├── main.py                    # Entry point for card generation
├── src/
│   ├── cli.py                 # CLI argument parsing
│   ├── orchestrator.py        # Main orchestration logic
│   ├── generator.py           # CardGenerator for parallel generation
│   ├── setup.py               # Provider initialization
│   ├── database.py            # SQLite schema and operations
│   ├── repositories.py        # Repository pattern for DB operations
│   ├── models.py              # Pydantic models for cards
│   ├── questions.py           # Question loading utilities
│   ├── prompts.py             # PromptLoader with lazy loading
│   ├── queries.py             # Database query utilities
│   ├── exceptions.py          # Custom exception hierarchy
│   ├── task_runner.py         # Async task execution
│   ├── types.py               # TypedDict and type definitions
│   ├── config/
│   │   ├── __init__.py        # Paths and env vars
│   │   ├── subjects.py        # SubjectRegistry configuration
│   │   ├── keys.py            # Unified API key loading
│   │   ├── loader.py          # Config file loading
│   │   ├── models.py          # Model constants
│   │   └── modes.py           # Mode configuration
│   ├── providers/
│   │   ├── base.py            # LLMProvider abstract base
│   │   ├── registry.py        # ProviderRegistry factory
│   │   ├── openai_compatible.py  # Shared base with tenacity retry
│   │   ├── cerebras.py        # Cerebras (native SDK)
│   │   ├── nvidia.py          # NVIDIA NIM
│   │   ├── openrouter.py      # OpenRouter
│   │   ├── google_genai.py    # Official Google GenAI
│   │   ├── google_antigravity.py  # Google Antigravity proxy
│   │   ├── gemini.py          # Gemini Web API (cookies)
│   │   ├── canopywave.py      # Canopywave
│   │   ├── baseten.py         # Baseten
│   │   └── g4f_provider.py    # G4F (experimental)
│   ├── anki/
│   │   ├── generator.py       # DeckGenerator
│   │   ├── models.py          # Anki note models
│   │   ├── renderer.py        # Markdown → HTML
│   │   └── styles.py          # Catppuccin CSS
│   └── data/
│       ├── prompts/           # Markdown prompt templates
│       └── questions.json     # Target questions
└── llm2deck.db                # SQLite database (generated)
```

## Architecture

The system uses a two-stage generation process:

1. **Parallel Generation**: Multiple providers generate initial cards simultaneously
2. **Combination**: First provider merges all results into a final, comprehensive deck

**Key patterns:**
- `ProviderRegistry` for dynamic provider initialization (factory pattern)
- `RunRepository` for database abstraction (repository pattern)
- Tenacity-based retry logic for resilient API calls
- `PromptLoader` for lazy prompt template loading

See `CLAUDE.md` for detailed architecture documentation.

## License

MIT License - see [LICENSE](LICENSE) for details.
