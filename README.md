# LLM2Deck

LLM2Deck is a powerful tool designed to generate high-quality Anki decks using Large Language Models (LLMs). It automates the creation of study materials for LeetCode problems, Computer Science concepts, and Physics topics, with support for both standard Q&A and Multiple Choice Questions (MCQs).

## Features

- **Multi-Provider Support**: Integrates with Cerebras, NVIDIA, OpenRouter, and Google Gemini
- **Multiple Modes**:
  - **LeetCode Mode** (Default): Generates detailed cards for algorithmic problems (Code, Complexity, approaches)
  - **CS Mode**: Generates deep-dive cards for Computer Science concepts
  - **Physics Mode**: Generates extensive cards for Physics concepts (Definitions, Formulas, Concepts)
- **MCQ Support**: Generates high-quality Multiple Choice Questions with shuffled options and detailed explanations
- **Category-Based Organization**: LeetCode problems are organized by category with numbered prefixes for proper ordering in Anki (e.g., `LeetCode::001 Binary Search::001 Two Sum`)
- **Rich Formatting**: Supports code syntax highlighting (Catppuccin theme) and Markdown rendering in Anki cards
- **Modular Architecture**: Clean, extensible design with separate concerns for logic, styles, and data
- **Automated Export**: Converts generated JSON data directly into importable Anki Package (`.apkg`) files

## Prerequisites

- Python >= 3.12
- `uv` (recommended for dependency management)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd LLM2Deck
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```ini
# Configuration
CONCURRENT_REQUESTS=5

# Custom Key File Paths (Optional)
# CEREBRAS_KEYS_FILE_PATH=api_keys.json
# OPENROUTER_KEYS_FILE_PATH=openrouter_keys.json
# NVIDIA_KEYS_FILE_PATH=nvidia_keys.json
# GEMINI_CREDENTIALS_FILE_PATH=google_secret.json

# Enable Gemini Provider (disabled by default)
# ENABLE_GEMINI=true
```

### API Keys

The project uses JSON files to manage API keys:

| Provider   | File                  | Format                          |
|------------|----------------------|---------------------------------|
| Cerebras   | `api_keys.json`      | `[{"api_key": "..."}]`          |
| NVIDIA     | `nvidia_keys.json`   | `["key1", "key2", ...]`         |
| OpenRouter | `openrouter_keys.json` | `["key1", "key2", ...]`       |
| Gemini     | `python3ds.json`     | Cookie JSON from browser        |

### Questions Configuration

Questions are defined in `src/data/questions.json`. 

**LeetCode** uses a category-based structure for organized deck generation:

```json
{
    "leetcode": {
        "Binary Search": [
            "Binary Search",
            "Search a 2D Matrix",
            "Koko Eating Bananas"
        ],
        "Two Pointers": [
            "Valid Palindrome",
            "3Sum"
        ]
    },
    "cs": ["Linked List, implementation..."],
    "physics": ["Zeeman effect (normal)", "Zeeman effect (anomalous)"]
}
```

This structure generates Anki decks with numbered hierarchies:
```
LeetCode
├── 001 Binary Search
│   ├── 001 Binary Search
│   ├── 002 Search a 2D Matrix
│   └── 003 Koko Eating Bananas
├── 002 Two Pointers
│   ├── 001 Valid Palindrome
│   └── 002 3Sum
```

## Usage

### 1. Generating Cards (JSON)

Use `main.py` to generate raw card data in JSON format.

**Standard Mode:**
```bash
# Default (LeetCode)
uv run main.py

# Explicit subject
uv run main.py leetcode
uv run main.py cs
uv run main.py physics
```

**MCQ Mode:**
```bash
# Physics MCQs
uv run main.py physics mcq

# CS MCQs
uv run main.py cs mcq

# LeetCode MCQs
uv run main.py leetcode mcq
```

Output is saved as timestamped JSON files (e.g., `leetcode_anki_deck_20251227T140625.json`).

### 2. Creating Anki Packages (.apkg)

Use `convert_to_apkg.py` to convert generated JSON into an importable Anki package.

```bash
uv run convert_to_apkg.py <input_json_file> --mode <mode>
```

**Examples:**
```bash
# Convert LeetCode deck
uv run convert_to_apkg.py leetcode_anki_deck_20251227T140625.json --mode leetcode

# Convert Physics MCQs
uv run convert_to_apkg.py physics_mcq_anki_deck_20251226.json --mode physics_mcq
```

### 3. Merging Archival Cards

If you have multiple generation runs archived, merge them:

```bash
uv run merge_anki_json.py leetcode
uv run merge_anki_json.py cs
```

### 4. Exporting to Markdown (Optional)

Save Anki cards as readable Markdown files:

```bash
uv run json_to_md.py
```

## Project Structure

```
LLM2Deck/
├── src/
│   ├── anki/                 # Anki generation logic
│   │   ├── generator.py      # Deck generation with category support
│   │   ├── models.py         # Genanki model definitions
│   │   ├── renderer.py       # Markdown to HTML rendering
│   │   └── styles.py         # CSS themes (Catppuccin)
│   ├── config/               # Configuration & Registry
│   │   ├── __init__.py       # Main config (paths, env vars)
│   │   └── subjects.py       # Subject-specific settings
│   ├── data/
│   │   ├── prompts/          # Markdown prompt templates
│   │   └── questions.json    # Target questions (categorized)
│   ├── providers/            # LLM Provider integrations
│   │   ├── cerebras.py
│   │   ├── nvidia.py
│   │   ├── openrouter.py
│   │   └── gemini.py
│   ├── generator.py          # Card generation logic
│   ├── questions.py          # Question loading utilities
│   └── prompts.py            # Prompt templates
├── convert_to_apkg.py        # CLI: JSON → Anki package
├── merge_anki_json.py        # CLI: Merge archived JSON files
├── json_to_md.py             # CLI: JSON → Markdown
├── main.py                   # Entry point for card generation
└── README.md
```

## License

MIT License - see [LICENSE](LICENSE) for details.
