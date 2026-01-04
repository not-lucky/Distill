# LLM2Deck

LLM2Deck is a powerful tool designed to generate high-quality Anki decks using Large Language Models (LLMs). It automates the creation of study materials for LeetCode problems, Computer Science concepts, and Physics topics, ensuring rich, formatted output with support for standard Q&A and Multiple Choice Questions (MCQs).

## Features

- **Multi-Provider Support**: Seamlessly integrates with Cerebras, NVIDIA, and Google Gemini.
- **Multiple Modes**:
    - **LeetCode Mode** (Default): Generates detailed cards for algorithmic problems (Code, Complexity, approaches).
    - **CS Mode**: Generates deep-dive cards for Computer Science concepts.
    - **Physics Mode**: Generates extensive cards for Physics concepts (Definitions, Formulas, Concepts).
- **MCQ Support**: Generates high-quality Multiple Choice Questions with shuffled options and detailed explanations.
- **Rich Formatting**: Supports code syntax highlighting (Catppuccin theme) and Markdown rendering in Anki cards.
- **Modular Architecture**: Clean, extensible design with separate concerns for logic, styles, and data.
- **Automated Export**: Converts generated JSON data directly into importable Anki Package (`.apkg`) files.

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
   Using `uv` (recommended):
   ```bash
   uv sync
   ```

## Configuration

### Environment Variables
Create a `.env` file in the root directory. You can use the following template:

```ini
# Configuration
CONCURRENT_REQUESTS=10

# Custom Key File Paths (Optional)
# CEREBRAS_KEYS_FILE_PATH=api_keys.json
# OPENROUTER_KEYS_FILE_PATH=openrouter_keys.json
# NVIDIA_KEYS_FILE_PATH=nvidia_keys.json
# GEMINI_CREDENTIALS_FILE_PATH=google_secret.json
```

### API Keys
The project uses JSON files to manage API keys.
*   **Cerebras**: `api_keys.json` (`[{"api_key": "..."}]`)
*   **NVIDIA**: `nvidia_keys.json` (`["key1", "key2"]`)
*   **Gemini**: `python3ds.json` (Cookie JSON)

### Subject Configuration
Subject-specific settings (prompts, models, target questions) are configured in `src/config/subjects.py`.
Questions and Prompts are externalized in `src/data/`.

## Usage

### 1. Generating Cards (JSON)

Use `main.py` to generate the raw card data in JSON format.

**Standard Mode:**
```bash
# Default (LeetCode)
uv run main.py

# Computer Science
uv run main.py cs

# Physics
uv run main.py physics
```

**MCQ Mode:**
Append `mcq` to generate multiple choice questions.
```bash
# Physics MCQs (Targeting "Very Hard" difficulty)
uv run main.py physics mcq

# CS MCQs
uv run main.py cs mcq
```
*Output will be saved as JSON files (e.g., `physics_mcq_anki_deck_<timestamp>.json`).*

### 2. Creating Anki Packages (.apkg)

Use `convert_to_apkg.py` to convert the generated JSON into an importable Anki package.

**Syntax:**
```bash
uv run convert_to_apkg.py <input_json_file> --mode <mode>
```

**Examples:**
```bash
# Convert Physics MCQs
uv run convert_to_apkg.py physics_mcq_anki_deck_20251226.json --mode physics_mcq

# Convert LeetCode Deck
uv run convert_to_apkg.py leetcode_anki_deck_20251226.json --mode leetcode
```
*Successfully created .apkg files can be directly imported into Anki.*

### 3. Archiving to Markdown (Optional)
To save your Anki cards as readable Markdown files:
```bash
uv run json_to_md.py
```

## Project Structure

```
LLM2Deck/
├── src/
│   ├── anki/               # Anki generation logic (Modular)
│   │   ├── generator.py    # Deck generation logic
│   │   ├── models.py       # Genanki model definitions
│   │   ├── renderer.py     # Markdown to HTML rendering
│   │   └── styles.py       # CSS themes
│   ├── config/             # Configuration & Registry
│   ├── data/               # Externalized Data
│   │   ├── prompts/        # Markdown prompt templates
│   │   └── questions.json  # Target questions list
│   ├── providers/          # LLM Provider integrations
│   └── ...
├── convert_to_apkg.py      # CLI tool for Anki package creation
├── main.py                 # Entry point for card generation
└── README.md
```
