# LLM2Deck

LLM2Deck is a powerful tool designed to generate high-quality Anki decks using Large Language Models (LLMs). It automates the creation of study materials for LeetCode problems and Computer Science concepts, supporting multiple LLM providers and ensuring rich, formatted output.

## Features

- **Multi-Provider Support**: Seamlessly integrates with Cerebras, NVIDIA, and Google Gemini.
- **Dual Modes**: 
    - **LeetCode Mode** (Default): Generates cards for algorithmic problems.
    - **CS Mode**: Generates cards for fundamental Computer Science concepts.
- **Rich Formatting**: Supports code syntax highlighting and Markdown rendering in Anki cards.
- **Automated Export**: Converts generated JSON data directly into importable Anki Package (`.apkg`) files.
- **Markdown Archival**: Converts Anki cards to Markdown files for readable archiving.

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
   Or using pip:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Environment Variables
Create a `.env` file in the root directory. You can use the following template:

```ini
# Configuration
CONCURRENT_REQUESTS=14
ENABLE_GEMINI=False

# Custom Key File Paths (Optional - defaults shown)
# CEREBRAS_KEYS_FILE_PATH=api_keys.json
# OPENROUTER_KEYS_FILE_PATH=openrouter_keys.json
# NVIDIA_KEYS_FILE_PATH=nvidia_keys.json
# GEMINI_CREDENTIALS_FILE_PATH=python3ds.json
```

### API Keys
The project uses JSON files to manage API keys. Ensure you have the necessary files in your root directory based on the providers you intend to use.

**Cerebras** (`api_keys.json`):
```json
[
  { "api_key": "your_cerebras_key_here" }
]
```

**NVIDIA** (`nvidia_keys.json`):
```json
[
  "your_nvidia_key_here"
]
```
*Note: A list of objects with an "api_key" field is also supported.*

**Gemini** (`python3ds.json`):
```json
[
  {
    "Secure_1PSID": "...",
    "Secure_1PSIDTS": "..."
  }
]
```

## Usage

### Generating Cards

**Run in LeetCode Mode (Default):**
This generates cards based on problems defined in `src/questions.py` (`QUESTIONS` list).
```bash
uv run main.py
```

**Run in CS Mode:**
This generates cards based on concepts defined in `src/questions.py` (`CS_QUESTIONS` list).
```bash
uv run main.py cs
```
*Output will be saved as JSON files (e.g., `leetcode_anki_deck_...json`).*

### Creating Anki Packages (`.apkg`)

After generating the JSON deck, convert it to an Anki importable package:
```bash
uv run convert_to_apkg.py
```
This script will process the generated JSON files and create `.apkg` files in the root directory.

### Archiving to Markdown

To save your Anki cards as readable Markdown files:
```bash
uv run json_to_md.py
```
This will read the JSON decks and output Markdown files to `anki_cards_markdown/`.

## Project Structure

- `src/`: Core source code.
    - `generator.py`: Main logic for calling LLMs and processing responses.
    - `providers/`: Integration logic for different LLM APIs.
    - `questions.py`: Definitions of problems and concepts to generate cards for.
    - `prompts.py`: System prompts for the LLMs.
- `anki_cards_archival/`: Directory where generated JSON decks are stored.
- `anki_cards_markdown/`: Directory for Markdown exports.
