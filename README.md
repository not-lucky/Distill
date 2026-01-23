# LLM2Deck

<p align="center">
  <strong>Generate high-quality Anki flashcards using multiple LLMs in parallel</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#usage">Usage</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#development">Development</a>
</p>

---

LLM2Deck is a powerful tool that generates comprehensive Anki flashcard decks by orchestrating multiple Large Language Models in parallel. It uses a two-stage generation process: first, multiple LLMs generate cards independently, then a "combiner" model synthesizes the best elements into a final, polished deck.

## Features

- **Parallel LLM Generation** — Query multiple providers simultaneously (Cerebras, OpenRouter, NVIDIA NIM, Google Gemini, and more)
- **Two-Stage Quality Pipeline** — Generate → Combine workflow produces higher-quality cards than single-model approaches
- **Built-in Subjects** — LeetCode algorithms, Computer Science fundamentals, and Physics concepts ready to go
- **Custom Subjects** — Define your own subjects with custom prompts and question sets
- **Multiple Card Formats** — Standard Q&A and Multiple Choice Question (MCQ) modes
- **Beautiful Cards** — Catppuccin-themed styling with syntax highlighting for code
- **Full Traceability** — SQLite database tracks all runs, provider outputs, and final cards
- **Caching** — Intelligent response caching to avoid redundant API calls
- **Anki Export** — Direct conversion to `.apkg` format ready for import

## Installation

### Prerequisites

- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** package manager (recommended)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/LLM2Deck.git
cd LLM2Deck

# Install dependencies with uv
uv sync

# Or with pip
pip install -e .
```

### API Keys

Create JSON files at the project root for each provider you want to use:

| Provider | Key File | Format |
|----------|----------|--------|
| Cerebras | `api_keys.json` | `{"keys": ["key1", "key2"]}` |
| OpenRouter | `openrouter_apikeys.json` | `{"keys": ["key1"]}` |
| NVIDIA NIM | `nvidia_keys.json` | `{"keys": ["key1"]}` |
| Google GenAI | `google_genai_keys.json` | `{"keys": ["key1"]}` |
| Canopywave | `canopywave_keys.json` | `{"keys": ["key1"]}` |
| Baseten | `baseten_keys.json` | `{"keys": ["key1"]}` |

You can also set key file paths via environment variables:
- `CEREBRAS_KEYS_FILE_PATH`
- `OPENROUTER_KEYS_FILE_PATH`
- `NVIDIA_KEYS_FILE_PATH`
- `GOOGLE_GENAI_KEYS_FILE_PATH`

## Quick Start

```bash
# Generate LeetCode flashcards (default)
uv run main.py generate

# Generate CS concept cards in MCQ format
uv run main.py generate cs mcq

# Convert generated JSON to Anki package
uv run main.py convert leetcode_anki_deck_20260109T154055.json

# Import the .apkg file into Anki!
```

## Usage

### Commands Overview

```bash
uv run main.py <command> [options]

Commands:
  generate    Generate flashcards from LLM providers
  convert     Convert JSON deck to Anki .apkg format
  merge       Merge archived JSON files for a subject
  export-md   Export JSON cards to Markdown format
  cache       Cache management (clear, stats)
  query       Query database for runs, problems, cards, and statistics
```

### Generate Cards

```bash
# Basic usage
uv run main.py generate                          # LeetCode standard (default)
uv run main.py generate <subject>                # Specific subject
uv run main.py generate <subject> mcq            # MCQ format
uv run main.py generate cs mcq --label "test"    # With run label

# Built-in subjects: leetcode, cs, physics
# Custom subjects: defined in config.yaml

# Options
--label TEXT     Optional label for this run (stored in database)
--dry-run        Show what would be done without making API calls
--no-cache       Bypass cache lookup (still stores new results)
```

**Examples:**

```bash
# Generate LeetCode algorithm cards
uv run main.py generate leetcode

# Generate Computer Science MCQs with a label
uv run main.py generate cs mcq --label "exam-prep"

# Preview generation without API calls
uv run main.py generate physics --dry-run
```

### Convert to Anki

```bash
uv run main.py convert <json_file> [options]

Options:
  --mode MODE      Override auto-detected mode (leetcode, cs, physics, *_mcq)
  --output FILE    Custom output filename
  --dry-run        Preview without writing files
```

**Examples:**

```bash
# Auto-detect mode from filename
uv run main.py convert leetcode_anki_deck_20260109T154055.json

# Specify output file
uv run main.py convert cs_cards.json --output my_cs_deck.apkg

# Force MCQ mode
uv run main.py convert cards.json --mode cs_mcq
```

### Merge Archives

Combine multiple JSON files from different runs into a single deck:

```bash
uv run main.py merge <subject>

# Preview merge operation
uv run main.py merge leetcode --dry-run
```

### Export to Markdown

Convert archived JSON cards to readable Markdown format:

```bash
uv run main.py export-md [options]

Options:
  --source DIR    Source directory with JSON files
  --target DIR    Target directory for Markdown output
  --dry-run       Preview without writing files
```

### Cache Management

```bash
# View cache statistics
uv run main.py cache stats

# Clear all cached responses
uv run main.py cache clear
```

### Query Database

Inspect runs, problems, provider results, and cards in the database:

```bash
# List recent runs
uv run main.py query runs
uv run main.py query runs --subject leetcode --status completed --limit 10

# Show details for a specific run (supports partial ID)
uv run main.py query run abc12345

# List problems
uv run main.py query problems --run abc12345
uv run main.py query problems --status success --search "binary"

# List provider results
uv run main.py query providers --run abc12345 --success
uv run main.py query providers --provider cerebras

# Search cards
uv run main.py query cards --search "binary search"
uv run main.py query cards --type Algorithm --limit 20

# Show global statistics
uv run main.py query stats
uv run main.py query stats --subject leetcode

# Output formats
uv run main.py query runs --format json      # JSON output
uv run main.py query runs --format table     # Table output (default)
```

## Configuration

### config.yaml

The main configuration file controls all aspects of LLM2Deck:

```yaml
# Global defaults for all providers
defaults:
  timeout: 120.0              # Request timeout in seconds
  temperature: 0.4            # Sampling temperature
  max_tokens: null            # Max tokens (null = API default)
  max_retries: 5              # Retry attempts for API requests
  json_parse_retries: 5       # Retries for JSON parsing
  retry_delay: 1.0            # Base delay between retries

# Provider Configuration
providers:
  cerebras:
    enabled: true
    model: "gpt-oss-120b"
    reasoning_effort: "high"

  openrouter:
    enabled: false
    model: "xiaomi/mimo-v2-flash:free"

  nvidia:
    enabled: false
    model: "moonshotai/kimi-k2-thinking"
    timeout: 900
    max_tokens: 16384

  google_genai:
    enabled: false
    model: "gemini-3-flash-preview"
    thinking_level: "high"
    temperature: 1.0

  google_antigravity:
    enabled: true
    models:
      - "gemini-3-pro-preview"
      - "gemini-claude-opus-4-5-thinking"
    timeout: 900

# Generation Settings
generation:
  concurrent_requests: 7      # Max parallel API requests
  request_delay: 1            # Delay between starting requests
  max_retries: 10

  # Combiner merges outputs from all generators
  combiner:
    provider: google_antigravity
    model: gemini-claude-opus-4-5-thinking
    also_generate: true       # Also use as generator

  # Optional formatter for JSON output
  formatter:
    provider: cerebras
    model: gpt-oss-120b
    also_generate: false

# Subject Settings
subjects:
  leetcode:
    enabled: true
  cs:
    enabled: true
  physics:
    enabled: false

  # Custom subject example
  # my_subject:
  #   enabled: true
  #   deck_prefix: "MySubject"
  #   prompts_dir: "prompts/my_subject"
  #   questions_file: "data/my_questions.json"

# Paths
paths:
  archival_dir: "anki_cards_archival"
  markdown_dir: "anki_cards_markdown"
  timestamp_format: "%Y%m%dT%H%M%S"

# Database
database:
  path: "llm2deck.db"
```

### Provider Configuration

Each provider supports these common options:

| Option | Description | Default |
|--------|-------------|---------|
| `enabled` | Whether to use this provider | `false` |
| `model` | Model identifier | Provider-specific |
| `timeout` | Request timeout (seconds) | `120.0` |
| `temperature` | Sampling temperature | `0.4` |
| `max_tokens` | Maximum output tokens | API default |
| `max_retries` | Retry attempts | `5` |

Provider-specific options:
- **Cerebras**: `reasoning_effort` (low/medium/high)
- **Google GenAI**: `thinking_level` (low/medium/high)
- **G4F**: `provider_name` (LMArena, etc.)

### Adding Custom Subjects

1. **Create prompt templates:**

```bash
mkdir -p prompts/my_subject
```

Create `prompts/my_subject/initial.md`:
```markdown
You are an expert tutor on {question}.

Generate comprehensive Anki cards covering:
- Key concepts
- Examples
- Common misconceptions

Output valid JSON matching the schema.
```

Create `prompts/my_subject/combine.md`:
```markdown
You are synthesizing multiple card sets for {question}.

Combine the best elements from each set:
{combined_inputs}

Output a unified set of high-quality cards as valid JSON.
```

2. **Create questions file:**

Create `data/my_questions.json`:
```json
{
  "Category 1": [
    "Question 1",
    "Question 2"
  ],
  "Category 2": [
    "Question 3"
  ]
}
```

3. **Add to config.yaml:**

```yaml
subjects:
  my_subject:
    enabled: true
    deck_prefix: "MySubject"
    prompts_dir: "prompts/my_subject"
    questions_file: "data/my_questions.json"
```

4. **Generate cards:**

```bash
uv run main.py generate my_subject
```

## Architecture

### Generation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Orchestrator                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│   │ Provider │  │ Provider │  │ Provider │   ← Parallel Generation  │
│   │ Cerebras │  │  NVIDIA  │  │  Gemini  │                          │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘                          │
│        │             │             │                                 │
│        └─────────────┴─────────────┘                                 │
│                      │                                               │
│                      ▼                                               │
│              ┌──────────────┐                                        │
│              │   Combiner   │  ← Synthesize best cards               │
│              │   (Gemini)   │                                        │
│              └──────┬───────┘                                        │
│                     │                                                │
│                     ▼                                                │
│              ┌──────────────┐                                        │
│              │  Formatter   │  ← Optional JSON formatting            │
│              │  (Cerebras)  │                                        │
│              └──────┬───────┘                                        │
│                     │                                                │
│                     ▼                                                │
│              ┌──────────────┐                                        │
│              │  Final JSON  │                                        │
│              │   + SQLite   │                                        │
│              └──────────────┘                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
LLM2Deck/
├── main.py                 # Entry point
├── config.yaml             # Runtime configuration
├── src/
│   ├── cli.py              # CLI interface (argparse)
│   ├── orchestrator.py     # Generation workflow coordinator
│   ├── generator.py        # Parallel card generation
│   ├── prompts.py          # PromptLoader - lazy prompt loading
│   ├── models.py           # Pydantic models (LeetCodeProblem, etc.)
│   ├── database.py         # SQLite operations
│   ├── repositories.py     # Database abstraction layer
│   ├── exceptions.py       # Custom exceptions
│   ├── task_runner.py      # Concurrent task execution
│   ├── cache.py            # Response caching
│   ├── config/
│   │   ├── loader.py       # YAML config parsing
│   │   ├── subjects.py     # SubjectRegistry
│   │   ├── keys.py         # API key loading
│   │   ├── models.py       # Config dataclasses
│   │   └── modes.py        # Mode definitions
│   ├── providers/
│   │   ├── base.py         # LLMProvider abstract base
│   │   ├── openai_compatible.py  # Shared implementation
│   │   ├── registry.py     # Provider factory
│   │   ├── cerebras.py     # Cerebras provider
│   │   ├── nvidia.py       # NVIDIA NIM
│   │   ├── openrouter.py   # OpenRouter
│   │   ├── google_genai.py # Google Generative AI
│   │   └── ...             # Other providers
│   ├── anki/
│   │   ├── generator.py    # DeckGenerator
│   │   ├── models.py       # Anki note models
│   │   ├── renderer.py     # Markdown → HTML
│   │   └── styles.py       # Catppuccin theme CSS
│   ├── services/
│   │   ├── merge.py        # MergeService
│   │   └── export.py       # ExportService
│   └── data/
│       ├── prompts/        # Prompt templates
│       └── questions.json  # Built-in questions
├── tests/                  # Test suite
├── anki_cards_archival/    # Archived JSON outputs
└── llm2deck.db             # SQLite database
```

### Card Models

**Standard Cards (Q&A):**
```json
{
  "title": "Two Sum",
  "topic": "Arrays and Hashing",
  "difficulty": "Easy",
  "cards": [
    {
      "card_type": "Concept",
      "tags": ["Arrays", "HashMap"],
      "front": "What is the Two Sum problem?",
      "back": "Given an array and target, find two numbers that sum to target..."
    }
  ]
}
```

**MCQ Cards:**
```json
{
  "title": "Binary Trees",
  "topic": "Data Structures",
  "difficulty": "Medium",
  "cards": [
    {
      "card_type": "Application",
      "tags": ["Trees", "Traversal"],
      "question": "What is the time complexity of BFS on a tree?",
      "options": ["A. O(1)", "B. O(log n)", "C. O(n)", "D. O(n²)"],
      "correct_answer": "C",
      "explanation": "BFS visits each node exactly once..."
    }
  ]
}
```

### Database Schema

LLM2Deck tracks all generation data in SQLite:

| Table | Purpose |
|-------|---------|
| `runs` | Execution metadata, timestamps, statistics |
| `problems` | Individual questions processed |
| `provider_results` | Raw LLM outputs before combination |
| `cards` | Final individual cards |
| `cache` | Cached LLM responses |

## Card Styling

Cards are styled with the **Catppuccin** color scheme, automatically adapting to Anki's light/dark mode:

- **Latte** (light) — Clean, readable daytime theme
- **Mocha** (dark) — Easy on the eyes for night study

Features:
- Syntax highlighting for code blocks (Pygments)
- Responsive typography
- Clear visual hierarchy for card types, tags, and metadata

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

### Running Tests

```bash
# All tests (LLM calls are mocked)
uv run pytest

# By category
uv run pytest tests/unit/ -m unit          # Fast, isolated
uv run pytest tests/integration/           # Component interactions
uv run pytest tests/e2e/                   # Full CLI workflows

# Parallel execution
uv run pytest tests/unit/ -n auto

# With coverage
uv run pytest --cov=src --cov-report=html

# Random order (verify isolation)
uv run pytest --random-order

# Check test metrics
uv run python scripts/test-metrics.py
```

### Type Checking

```bash
# Uses 'ty' type checker
ty check src/
```

### Code Quality Targets

- **Test-to-code ratio**: 5:1 for core modules, 2:1 for peripheral
- **Coverage**: 87%+ overall
- **Test count**: 1400+ tests

### Adding a New Provider

1. **Create provider class:**

```python
# src/providers/my_provider.py
from src.providers.openai_compatible import OpenAICompatibleProvider

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

2. **Register in `src/providers/registry.py`**

3. **Add key config in `src/config/keys.py`**

4. **Add to `config.yaml`**

### Project Guidelines

- **Error Handling**: Use custom exceptions from `src/exceptions.py`
- **Async Pattern**: Use `asyncio` for all I/O operations
- **Testing**: Mock all LLM calls, never make real API requests in tests
- **Configuration**: All settings via `config.yaml`, environment variables for secrets

## Troubleshooting

### Common Issues

**"No providers enabled"**
- Check `config.yaml` — at least one provider must have `enabled: true`
- Verify API key files exist and contain valid keys

**"All providers failed"**
- Check API key validity
- Verify network connectivity
- Review `app.log` for detailed error messages

**"JSON parse error"**
- Some models produce invalid JSON — configure a `formatter` provider
- Increase `json_parse_retries` in config

**Rate limiting**
- Increase `request_delay` in generation settings
- Reduce `concurrent_requests`

### Logs

Check `app.log` for detailed execution logs:

```bash
tail -f app.log
```

### Database Queries

Use the built-in query command for easy database inspection:

```bash
# List recent runs with statistics
uv run main.py query runs --limit 5

# Show detailed run statistics
uv run main.py query run <run_id>

# Search cards
uv run main.py query cards --search "binary search"

# Global statistics
uv run main.py query stats
```

Or inspect the SQLite database directly:

```bash
sqlite3 llm2deck.db

# Recent runs
SELECT * FROM runs ORDER BY created_at DESC LIMIT 5;

# Provider success rates
SELECT provider_name, COUNT(*) FROM provider_results GROUP BY provider_name;
```

## Built-in Subjects

### LeetCode (`leetcode`)

Covers NeetCode 150 patterns:
- Arrays and Hashing
- Two Pointers
- Sliding Window
- Stacks
- Binary Search
- Linked Lists
- Trees
- Tries
- Heap/Priority Queue
- Backtracking
- Graphs
- Dynamic Programming
- And more...

Cards include:
- Problem understanding
- Multiple solution approaches (brute force → optimal)
- Code implementations (Python)
- Complexity analysis
- Common pitfalls

### Computer Science (`cs`)

Foundational CS concepts:
- Python fundamentals
- Data structures (stacks, queues, trees, graphs)
- Algorithms (sorting, searching)
- Recursion and dynamic programming
- System design basics

### Physics (`physics`)

Core physics topics:
- Mechanics
- Thermodynamics
- Electromagnetism
- Waves and optics
- Modern physics

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass (`uv run pytest`)
5. Submit a pull request

See [TESTING.md](TESTING.md) for testing guidelines and [AGENTS.md](AGENTS.md) for detailed development documentation.

---

<p align="center">
  Made with ❤️ for spaced repetition learners
</p>
