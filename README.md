# LLM2Deck

Generate high-quality Anki flashcards using multiple LLMs in parallel.

LLM2Deck runs multiple LLM providers simultaneously, then combines their outputs into comprehensive flashcard decks. It supports LeetCode algorithms, Computer Science concepts, Physics topics, and custom subjects you define.

## Features

- **Parallel LLM Generation** - Query multiple providers at once, combine the best results
- **Built-in Subjects** - LeetCode, CS, Physics with optimized prompts
- **Custom Subjects** - Add your own topics with custom prompts and questions
- **MCQ Support** - Generate multiple-choice questions with explanations
- **Hierarchical Decks** - Organized by category (e.g., `LeetCode::Binary Search::Two Sum`)
- **Rich Formatting** - Syntax highlighting, Markdown, Catppuccin theme
- **Run Tracking** - SQLite database logs all generations

## Quick Start

```bash
# Install
git clone <repo_url> && cd LLM2Deck
uv sync

# Configure providers in config.yaml (see Configuration section)

# Generate cards
uv run main.py generate leetcode          # LeetCode standard cards
uv run main.py generate cs mcq            # CS multiple choice
uv run main.py generate physics           # Physics cards

# Convert to Anki package
uv run main.py convert leetcode_anki_deck_20260107.json
```

## Installation

**Requirements:** Python >= 3.12, [uv](https://github.com/astral-sh/uv)

```bash
git clone <repository_url>
cd LLM2Deck
uv sync
```

## Configuration

All configuration is in `config.yaml`.

### Providers

Enable/disable providers and set models:

```yaml
providers:
  cerebras:
    enabled: true
    model: "gpt-oss-120b"
    reasoning_effort: "high"      # Optional: low, medium, high

  openrouter:
    enabled: false
    model: "anthropic/claude-3-opus"

  nvidia:
    enabled: false
    model: "meta/llama-3.1-405b-instruct"
    timeout: 900                  # Optional: request timeout in seconds

  google_genai:
    enabled: false
    model: "gemini-2.0-flash"
    thinking_level: "high"        # Optional: for thinking models

  google_antigravity:
    enabled: true
    models:                       # Multiple models = multiple instances
      - "gemini-3-pro-preview"
      - "gemini-claude-sonnet-4-5-thinking"

  g4f:
    enabled: false
    model: "gpt-4"
    provider_name: "Bing"         # G4F provider name
```

**Available Providers:**

| Provider | API Keys File | Notes |
|----------|--------------|-------|
| `cerebras` | `api_keys.json` | Native SDK |
| `openrouter` | `openrouter_keys.json` | OpenAI-compatible |
| `nvidia` | `nvidia_keys.json` | NVIDIA NIM |
| `google_genai` | `google_genai_keys.json` | Official Google API |
| `google_antigravity` | None | Local proxy, no auth |
| `canopywave` | `canopywave_keys.json` | OpenAI-compatible |
| `baseten` | `baseten_keys.json` | OpenAI-compatible |
| `gemini_webapi` | `python3ds.json` | Browser cookies (experimental) |
| `g4f` | None | gpt4free (experimental) |

### API Keys

Create JSON files at project root:

```json
// api_keys.json (Cerebras)
[{"api_key": "sk-..."}]

// nvidia_keys.json
["nvapi-...", "nvapi-..."]

// openrouter_keys.json
[{"data": {"key": "sk-or-..."}}]

// google_genai_keys.json
["AIza...", "AIza..."]
```

### Generation Settings

```yaml
generation:
  concurrent_requests: 8      # Parallel question processing
  request_delay: 1            # Seconds between requests (rate limiting)
  max_retries: 5              # API retry attempts
  json_parse_retries: 3       # JSON parsing retries

  # Combiner: which model merges outputs from all providers
  combiner:
    provider: google_antigravity
    model: gemini-pro
    also_generate: true       # Also use for initial generation

  # Formatter: separate model for JSON output (optional)
  # Use when combiner is smart but unreliable at JSON
  formatter:
    provider: cerebras
    model: gpt-oss-120b
    also_generate: false      # Only format, don't generate
```

### Subjects

Built-in subjects work out of the box:

```yaml
subjects:
  leetcode:
    enabled: true
  cs:
    enabled: true
  physics:
    enabled: false
```

## Usage

### Generate Cards

```bash
# Basic usage
uv run main.py generate                    # Default: leetcode standard
uv run main.py generate leetcode           # LeetCode problems
uv run main.py generate cs                 # Computer Science concepts
uv run main.py generate physics            # Physics topics

# MCQ mode
uv run main.py generate leetcode mcq       # LeetCode multiple choice
uv run main.py generate cs mcq             # CS multiple choice
uv run main.py generate physics mcq        # Physics multiple choice

# With label (for tracking)
uv run main.py generate leetcode --label "binary-search-batch"

# Custom subject (after configuring in config.yaml)
uv run main.py generate biology
```

**Output:** `{subject}_anki_deck_{timestamp}.json`

### Convert to Anki Package

```bash
# Auto-detect mode from filename
uv run main.py convert leetcode_anki_deck_20260107T143025.json

# Explicit mode
uv run main.py convert output.json --mode cs_mcq

# Custom output filename
uv run main.py convert cards.json -o my_deck.apkg
```

**Valid modes:** `leetcode`, `cs`, `physics`, `leetcode_mcq`, `cs_mcq`, `physics_mcq`, `mcq`

### Merge JSON Files

Combine multiple generation runs:

```bash
# Merge all JSON files in anki_cards_archival/{subject}/
uv run main.py merge leetcode
uv run main.py merge cs
uv run main.py merge physics
```

**Output:** `{subject}_anki_deck_{timestamp}.json`

### Export to Markdown

Convert cards to readable Markdown:

```bash
# Default directories
uv run main.py export-md

# Custom directories
uv run main.py export-md --source ./my_cards --target ./markdown_output
```

## Custom Subjects

Add your own subjects with custom prompts and questions.

### 1. Create Prompt Files

Create a directory with your prompts:

```
prompts/biology/
├── initial.md      # Prompt for initial card generation
└── combine.md      # Prompt for combining results from multiple providers
```

**initial.md example:**
```markdown
You are an expert educator creating Anki flashcards for: **{topic}**

Generate comprehensive flashcards covering:
- Core definitions
- Key concepts
- Practical applications

Return JSON:
{
  "title": "Topic Title",
  "topic": "Category",
  "difficulty": "Basic|Intermediate|Advanced",
  "cards": [
    {
      "card_type": "Concept",
      "tags": ["Tag1"],
      "front": "Question",
      "back": "Answer"
    }
  ]
}
```

**combine.md example:**
```markdown
Review and combine these flashcard sets for **{topic}**:

{cards}

Remove duplicates, improve clarity, ensure completeness.
Return the same JSON format with merged cards.
```

### 2. Create Questions File

```json
{
  "Cell Biology": [
    "Photosynthesis",
    "Cell Division",
    "Mitochondria"
  ],
  "Ecology": [
    "Food Chains",
    "Ecosystems",
    "Biodiversity"
  ]
}
```

### 3. Configure in config.yaml

```yaml
subjects:
  biology:
    enabled: true
    deck_prefix: "Biology"
    deck_prefix_mcq: "Biology_MCQ"           # Optional
    prompts_dir: "prompts/biology"
    questions_file: "data/biology_questions.json"
```

### 4. Generate

```bash
uv run main.py generate biology
uv run main.py generate biology mcq
```

See `src/data/prompts/example/` for template prompts.

## Project Structure

```
LLM2Deck/
├── main.py                 # Entry point
├── config.yaml             # Configuration
├── src/
│   ├── cli.py              # CLI interface
│   ├── orchestrator.py     # Generation workflow
│   ├── generator.py        # Parallel card generation
│   ├── prompts.py          # Prompt loading
│   ├── models.py           # Pydantic card models
│   ├── database.py         # SQLite operations
│   ├── repositories.py     # Database abstraction
│   ├── config/
│   │   ├── loader.py       # YAML config parsing
│   │   ├── subjects.py     # Subject registry
│   │   └── keys.py         # API key loading
│   ├── providers/
│   │   ├── base.py         # Abstract provider
│   │   ├── registry.py     # Provider factory
│   │   ├── cerebras.py     # Cerebras
│   │   ├── openrouter.py   # OpenRouter
│   │   ├── nvidia.py       # NVIDIA NIM
│   │   └── ...             # Other providers
│   ├── anki/
│   │   ├── generator.py    # Deck creation
│   │   ├── renderer.py     # Markdown → HTML
│   │   └── styles.py       # Card CSS
│   └── data/
│       ├── prompts/        # Prompt templates
│       └── questions.json  # Built-in questions
└── llm2deck.db             # SQLite database
```

## How It Works

1. **Parallel Generation**: Each enabled provider generates cards for a question simultaneously
2. **Combination**: The first provider combines all results into a final comprehensive set
3. **Validation**: Pydantic models validate card structure
4. **Storage**: Results saved to JSON and SQLite database
5. **Conversion**: JSON converted to `.apkg` for Anki import

## Environment Variables

Optional overrides:

```bash
LLM2DECK_CONFIG=custom_config.yaml      # Custom config file
LLM2DECK_PROMPTS_DIR=./my_prompts       # Custom prompts directory
CONCURRENT_REQUESTS=16                   # Override concurrent requests
```

## Database

All runs are tracked in `llm2deck.db`:

- `runs` - Generation metadata and statistics
- `problems` - Individual questions processed
- `provider_results` - Raw LLM outputs
- `cards` - Final generated cards

Query with any SQLite client or use `src/queries.py`.

## Testing

The project has comprehensive test coverage with all LLM API calls mocked.

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_generator.py

# Run specific test class
uv run pytest tests/test_cli.py::TestHandleGenerate

# Run tests matching a pattern
uv run pytest -k "test_merge"

# Run with coverage report
uv run pytest --cov=src --cov-report=html

# Run only fast tests (skip slow integration tests)
uv run pytest -m "not slow"
```

**Test Structure:**

```
tests/
├── conftest.py                 # Shared fixtures and mock providers
├── test_models.py              # Pydantic model validation
├── test_generator.py           # CardGenerator tests
├── test_orchestrator.py        # Orchestrator workflow tests
├── test_cli.py                 # CLI argument parsing
├── test_e2e.py                 # End-to-end workflow tests
├── test_config/                # Configuration tests
├── test_providers/             # Provider tests (all mocked)
├── test_anki/                  # Anki generation tests
└── test_services/              # Merge/Export service tests
```

All tests use mocked LLM responses - no API credits are consumed.

## License

MIT
