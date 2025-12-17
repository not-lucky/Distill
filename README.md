# Python 3DS Anki Generator

**Python 3DS Anki Generator** is a sophisticated automated pipeline designed to transform the "Python Data Structures" (pythonds3) online textbook into high-quality, active-recall Anki flashcards. By leveraging advanced web scraping, AI-powered cognitive processing, and programmatic deck generation, this tool enables students and developers to master data structures and algorithms through efficient spaced repetition.

The project addresses the challenge of converting passive reading material into active learning resources. It automates the extraction of concepts, code snippets, and theoretical knowledge, synthesizing them into atomic flashcards that adhere to learning science principles.

## Features

- **Automated Content Extraction**:
  - Uses `zendriver` and `selenium` to navigate and scrape content from Runestone Academy.
  - Handles dynamic content loading and infinite scrolling automatically.
  - Captures full-page screenshots for visual context processing.

- **AI-Powered Knowledge Synthesis**:
  - Utilizes **Google Gemini 2.5 Pro** to analyze educational content.
  - Implements a "Cognitive Architect" persona to deconstruct complex topics.
  - Generates atomic, question-driven flashcards based on "Desirable Difficulty" and "Active Recall" principles.
  - De-duplicates and refines content to ensure high-quality learning materials.

- **Professional Anki Deck Generation**:
  - Creates `.apkg` packages ready for import into Anki.
  - **Syntax Highlighting**: Automatically highlights Python code snippets using `pygments`.
  - **Beautiful Theming**: Applies the **Catppuccin** color palette (Latte & Mocha) for a modern, eye-friendly aesthetic.
  - **Hierarchical Organization**: Structures decks by Chapter and Section (e.g., `Pythonds3::Chapter 3::3.3 Unordered List`).

- **Robust Tooling**:
  - Built with `uv` for fast, reliable Python dependency management.
  - Asynchronous processing for high-performance scraping and API interaction.

## Installation

This project uses `uv` for dependency management and workflow execution.

### Prerequisites

- **Python 3.12+**
- **uv** (Universal Python Packaging)
- **Google Gemini API Key**

### Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/python3ds.git
    cd python3ds
    ```

2.  **Initialize Project & Install Dependencies**
    Use `uv` to sync the project environment. This will create a virtual environment and install all locked dependencies.
    ```bash
    uv sync
    ```

3.  **Configure API Keys**
    The project requires Google Gemini API keys.
    > **Note**: Currently, API keys are configured within the `z.py` script. For security, it is recommended to replace the hardcoded keys with environment variables in a production setting.

    To set up your environment variables (recommended):
    ```bash
    export GEMINI_API_KEY="your_api_key_here"
    ```

## Usage

The pipeline consists of three main stages: Scraping, Processing, and Generation.

### 1. Scrape Content
Run the scraper to navigate the textbook URLs and capture screenshots.
```bash
uv run main.py
```
*This will save screenshots to the `screenshots/` directory.*

### 2. Process with AI
Run the AI processor to analyze the screenshots and generate JSON card data.
```bash
uv run z.py
```
*This will process images in `screenshots/`, query the Gemini API, and aggregate the results into `python3ds.json`.*

### 3. Generate Anki Package
Convert the generated JSON data into an Anki package file (`.apkg`).
```bash
uv run python3ds_anki.py python3ds.json
```
*This will create `pythonds3_anki.apkg` in the current directory.*

### 4. Import into Anki
Open Anki and import the generated `pythonds3_anki.apkg` file.

## Directory Structure

```text
python3ds/
├── main.py                 # Web scraper script (Selenium/Zendriver)
├── z.py                    # AI processing and aggregation script
├── python3ds_anki.py       # Anki deck generator script
├── python3ds.json          # Intermediate JSON data containing card definitions
├── pythonds3_anki.apkg     # Final generated Anki package
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # Locked dependencies
├── screenshots/            # Directory for captured web pages
├── output/                 # Intermediate Markdown output from AI
├── final_output/           # Refined output
└── README.md               # Project documentation
```

## File Documentation

### `main.py`
**Purpose**: Handles the web scraping of the Runestone Academy textbook.
- **`take_screenshots()`**: The main async function.
  - Initializes a `zendriver` browser instance.
  - Iterates through `URLS_TO_SCRAPE`.
  - Implements smart scrolling logic to ensure all dynamic content (like lazy-loaded images or code blocks) is rendered.
  - Captures full-page screenshots and saves them to `screenshots/`.
- **Dependencies**: `zendriver`, `asyncio`, `os`.

### `z.py`
**Purpose**: The core AI processing engine. It manages the interaction with the Gemini API to extract knowledge and synthesize flashcards.
- **`GeminiProcessor` Class**:
  - Manages API key rotation (cycling through a list of keys to handle rate limits).
  - **`process_image(image_path)`**: Sends the screenshot to Gemini 2.5 Pro with a detailed system prompt ("Cognitive Architect"). It handles retries and saves the output.
- **`actual_main()`**:
  - Aggregates all individual Markdown/JSON files generated by the processor.
  - Sorts the content based on Chapter/Section numbers.
  - Compiles everything into a single `python3ds.json` file.
- **Prompts**: Contains extensive system instructions defining the "4-Step Refinement Process" for card generation.

### Pipeline Stages & Auxiliary Scripts
The project employs a multi-stage refinement pipeline to ensure high-quality output.

- **`x.py` / `y.py.py`**:
  - **Purpose**: Initial generation and expansion stages. These scripts are variations of the main processing logic, likely used for different passes (e.g., initial extraction vs. card quantity expansion).
  - **Functionality**: Similar to `z.py`, they process images/markdown and interact with the Gemini API to generate or refine Anki cards.

- **`zz.py` (Structure Corrector)**:
  - **Purpose**: Fixes hierarchical metadata.
  - **Logic**: Reads the `toc.png` (Table of Contents) image and the generated JSON. It uses a "Structural Validator" persona to cross-reference the content with the TOC, ensuring every card has the correct `Chapter` and `Section` metadata.
  - **Input/Output**: Processes files from `final_output/` and saves to `final_final_output/`.

- **`zzz.py` (Context Injector)**:
  - **Purpose**: Enhances card self-sufficiency.
  - **Logic**: Uses a "Lead Cognitive Architect" persona to embed verbatim context (code snippets, text) directly into the `front` of the cards. This ensures cards are solvable without external dependencies.
  - **Input/Output**: Processes files from `final_final_output/` and saves to `final_final_final_output/`.

- **`test.py`**:
  - **Purpose**: A simple utility script to verify that your Google Gemini API key is working correctly.
  - **Usage**: Run `uv run test.py` to check your connection.

### `python3ds_anki.py`
**Purpose**: Converts the structured JSON data into a ready-to-use Anki package.
- **`AnkiDeckGenerator` Class**:
  - **`__init__`**: Loads the JSON data.
  - **`create_models()`**: Defines the Anki Note Model, including the CSS for the **Catppuccin** theme and syntax highlighting.
  - **`format_code_blocks(text)`**: Parses Markdown code blocks and converts them to HTML with `pygments` syntax highlighting classes.
  - **`process_cards()`**: Iterates through the data, creates hierarchical decks, and adds notes.
  - **`generate_package()`**: Exports the final `.apkg` file.

## Configuration

### Environment Variables
While the current codebase may contain hardcoded keys for testing, the recommended configuration is via environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Google Gemini API Key | `AIzaSy...` |

### `pyproject.toml`
Defines the project metadata and dependencies.
```toml
[project]
name = "python3ds"
version = "0.1.0"
dependencies = [
    "genanki>=0.13.1",
    "google-genai>=1.33.0",
    "pillow>=11.3.0",
    "pygments>=2.19.2",
    "selenium>=4.35.0",
    "zendriver>=0.14.0",
]
```

## Development Workflow

To contribute or modify the project:

1.  **Environment Setup**:
    ```bash
    uv venv
    source .venv/bin/activate
    uv sync
    ```

2.  **Linting & Formatting**:
    Ensure code quality before committing.
    ```bash
    uv run ruff check .
    uv run ruff format .
    ```

3.  **Testing**:
    Run specific modules to verify functionality.
    ```bash
    uv run python3ds_anki.py --validate python3ds.json
    ```

## Troubleshooting

- **Browser Crashes in `main.py`**:
  - Ensure you have a compatible Chrome/Chromium browser installed.
  - Try running in headless mode by modifying `zendriver.start(headless=True)`.

- **API Rate Limits**:
  - If `z.py` fails with 429 errors, increase the `sleep` time in the retry logic or add more API keys to the rotation pool.

- **Anki Import Issues**:
  - If cards look broken, ensure you are using a recent version of Anki that supports the CSS features used (Flexbox, CSS variables).

## Version History

- **0.1.0**: Initial release.
    - Complete pipeline implementation (Scraping -> AI Processing -> Anki Generation).
    - Support for Catppuccin theming and syntax highlighting.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

## Credits

- **Content Source**: [Runestone Academy - Python Data Structures](https://runestone.academy/ns/books/published/pythonds3/index.html)
- **Theme**: [Catppuccin](https://github.com/catppuccin/catppuccin)
