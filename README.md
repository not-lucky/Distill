# LLM2Deck

LLM2Deck is a powerful tool designed to generate comprehensive Anki cards for LeetCode problems using advanced Large Language Models (LLMs). It leverages multiple providers (like Cerebras and Gemini) to create diverse, high-quality educational content, helping you master algorithms and data structures effectively.

## Features

-   **Multi-LLM Support**: Utilizes Cerebras (Llama/GLM) and Google Gemini for robust content generation.
-   **Comprehensive Coverage**: Generates cards for various solution approaches (Brute Force, DP, Two Pointers, etc.), not just the optimal one.
-   **Structured Anki Decks**: Creates organized decks with hierarchical tags (Topic, Difficulty, Card Type).
-   **Rich Formatting**: Supports Markdown rendering for code blocks, tables, and mathematical notation in Anki cards.
-   **Automated Workflow**: From question list to `.apkg` file with a few commands.

## Prerequisites

-   **Python 3.12+**
-   **uv**: A fast Python package installer and resolver. [Install uv](https://github.com/astral-sh/uv).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/not-lucky/LLM2Deck.git
    cd LLM2Deck
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```

## Configuration

1.  **Environment Variables**:
    Create a `.env` file in the root directory (or rename `.env.example` if available) and configure the following:
    ```env
    API_KEYS_FILE_PATH=api_keys.json
    GEMINI_CREDENTIALS_FILE_PATH=python3ds.json
    CONCURRENT_REQUESTS=5
    ENABLE_GEMINI=True
    ```

2.  **API Keys**:
    Create an `api_keys.json` file in the root directory with your Cerebras API keys:
    ```json
    [
        {"api_key": "your_cerebras_key_1"},
        {"api_key": "your_cerebras_key_2"}
    ]
    ```

3.  **Gemini Credentials** (Optional):
    If `ENABLE_GEMINI` is True, ensure `python3ds.json` (or your configured file) contains valid Gemini authentication cookies/credentials.

## Usage

### 1. Generate Anki Cards

Run the main generation script to process the list of questions defined in `src/config.py` (or `generate_anki_cards_multi.py`).

```bash
uv run generate_anki_cards_multi.py
```
*Alternatively, you can run `uv run main.py` if you are using the modular `src` structure.*

This will:
-   Query the configured LLMs for each question.
-   Combine and structure the responses.
-   Save individual JSON files to `anki_cards_archival/`.
-   Generate a final combined JSON deck file (e.g., `leetcode_anki_deck_YYYYMMDD.json`).

### 2. Convert to Anki Package (.apkg)

Convert the generated JSON deck into an importable Anki package.

```bash
uv run convert_to_apkg.py leetcode_anki_deck_<timestamp>.json -o leetcode_anki.apkg
```

**Options:**
-   `-o, --output`: Specify the output filename (default: `leetcode_anki.apkg`).
-   `--validate`: Validate the JSON schema before processing.

### 3. Import to Anki

1.  Open the Anki desktop application.
2.  Go to **File** > **Import**.
3.  Select the generated `leetcode_anki.apkg` file.
4.  Your cards will be imported under the `LeetCode` deck, organized by Topic and Problem Title.

## Project Structure

-   `generate_anki_cards_multi.py`: Main script for fetching and generating card content.
-   `convert_to_apkg.py`: Utility to convert JSON output to Anki `.apkg` format.
-   `src/`: Modular source code (providers, config, utils).
-   `anki_cards_archival/`: Storage for individual problem JSONs.
-   `api_keys.json`: Configuration for API keys.

## License

[MIT License](LICENSE)
