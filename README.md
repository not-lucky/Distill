# LLM2Deck: Orchestrated Parallel Flashcard Generation

> [!WARNING]
> **WORK IN PROGRESS**: This repository is currently a Work In Progress (WIP) and is not fully functional in its master branch.
> If you require a fully functional and stable version urgently, please use the old version located in the [archived/](file:///home/lucky/stuff/to-del/LLM2Deck/archived) directory.

---

## General Overview

**LLM2Deck** is an orchestrated system designed to convert complex technical study materials (codebases, Textbook chapters, LeetCode algorithms, language specifications) into high-quality, pedagogically optimized Anki flashcards (`.apkg`). 

Rather than relying on a single, expensive LLM prompt that suffers from low detail density and high syntax failures, LLM2Deck uses a **five-stage parallel execution and synthesis pipeline** built in Node.js (ESM), utilizing an SQLite database cache and spawning a Python script for final deck compilation.

---

## How It Works: The Five-Stage Pipeline

```
[Source Material] 
       │
       ├─► [Stage 1: Parallel Generation] (Multi-LLM Raw Text Extraction)
       │
       ├─► [Stage 2: Synthesis] (Frontier LLM Deduplication & Consolidation)
       │
       ├─► [Stage 3: Translation] (Standard JSON Converter)
       │
       ├─► [Stage 4: Schema Enforcement] (Strict AJV Polymorphic Validation & Correction)
       │
       └─► [Stage 5: Anki Compilation] (Python subprocess using genanki & Catppuccin CSS)
```

1. **Stage 1 (Parallel Generation)**: Multiple cheap or fast LLMs query the document chunks in parallel, extracting raw question-and-answer pairs in normal text format to conserve token costs.
2. **Stage 2 (High-Density Synthesis)**: A top-tier frontier model consolidates all raw card sets into a single, high-density, and deduplicated markdown list.
3. **Stage 3 (JSON Translation)**: A reliable model parses the consolidated normal text into a loose JSON list array.
4. **Stage 4 (Schema Enforcement)**: A cost-efficient model corrects the loose JSON to conform strictly to the polymorphic JSON Schema, executing a cheap LLM retry loop if validation fails.
5. **Stage 5 (Compilation)**: Spawns a Python bridge executing `src/compile.py` which uses the `genanki` library to build and compile the deck into Anki `.apkg` format, complete with responsive Catppuccin theme styling and option shuffling for MCQs.

---

## Technical Highlights

- **Hybrid Design**: Core orchestration, async throttling, and AJV schema validation in Node.js (ESM) integrated with Anki deck compilation via Python subprocess spawning.
- **Relational Runs Resumption**: Runs, steps, and API outputs are tracked in a SQLite database. If a run crashes, the system skips already completed questions.
- **SHA256 Caching Layer**: Requests are hashed using `(provider + model + prompts + parameters)` to prevent redundant API fees on unchanged source documents.
- **AJV Strict Validation**: Enforces polymorphic card types (Basic Q&A, Cloze deletions, Multiple Choice Questions) at schema validation level.

---

## Installation & Setup

Ensure you have Node.js (v18+) and Python 3 installed.

### 1. Install Node.js Dependencies
Using `npm` to install packages:
```bash
npm install
```

### 2. Set Up Python Virtual Environment
Use `uv` to sync python dependencies:
```bash
uv sync
```

---

## Configuration & Examples

Everything is configured via external configuration files. Below are structural schemas and examples.

### 1. Main Configuration (`config.yaml`)
Points to API endpoints, concurrency parameters, and custom prompts/keys file paths.

```yaml
# Global defaults and concurrency controls
global:
  concurrency_limit: 8          # Max parallel API requests
  request_delay: 1.0            # Delay (seconds) between starting requests
  default_timeout: 500.0        # Default API request timeout (seconds)
  output_dir: "./output"        # Compiled Anki decks target directory
  cache_db_path: "./llm2deck.db" # Database cache path
  keys_file_path: "./keys.yaml" # Path to API keys configuration
  prompts_file_path: "./prompts.yaml" # Custom prompts configuration path

# Configured LLM providers
providers:
  openai:
    base_url: "https://api.openai.com/v1"
    temperature: 0.3
  cerebras:
    base_url: "https://api.cerebras.ai/v1"
    temperature: 0.2
  ollama_local:
    base_url: "http://localhost:11434/v1"
    temperature: 0.0

# Assignment of models to pipeline stages (provider/model format)
pipeline:
  generation:
    models:
      - "openai/gpt-3.5-turbo"
      - "cerebras/llama3.1-70b"
  synthesis:
    model: "openai/gpt-4o"
  translation:
    model: "openai/gpt-3.5-turbo"
  schema_enforcement:
    model: "openai/gpt-3.5-turbo"
```

### 2. Credentials Storage (`keys.yaml`)
Keeps API keys isolated from primary configurations and version control.

```yaml
openai:
  - "sk-proj-..."
  - "sk-proj-rotate-key-..."
cerebras:
  - "cber-..."
```

### 3. Prompt Overrides & Subjects Mapping (`prompts.yaml`)
Overwrites default prompts for any stage and sets up study subjects with nested topic paths, generation instructions, and additional stage 2 combiner prompts.

Supports two generation modes:
- **Topic Mode** (default): Generates cards systematically from topic names.
- **Document Mode**: Ingests files or directories, digesting their contents directly.

```yaml
# Default prompt overrides for stages
defaults:
  # General default override (acts as fallback)
  generation: |
    You are a world-class educator. Extract concepts...
  # Mode-specific overrides (highly recommended)
  generation_topic: |
    You are a world-class educator... [special guidelines for topic coverages]
  generation_document: |
    You are a world-class document digestion engine... [special guidelines for document coverage]
  synthesis: |
    You are a senior technical editor. Consolidate and merge...

# Subject presets mapping. 
# Match directly via CLI argument (e.g. `node src/cli.js run leetcode`).
subjects:
  # 1. Example Topic Mode subject
  leetcode:
    generation: |
      Special Guidelines for LeetCode:
      - Target Complexity to Constraint mapping
      - Recurrence Relations for Dynamic Programming
    synthesis: |
      Consolidate algorithmic insights. Retain complexity trade-offs.
    categories:
      - name: "Arrays & Hashing"
        topics:
          - "Two Sum"
          - "Group Anagrams"
      - name: "Two Pointers"
        topics:
          - "Valid Palindrome"

  # 2. Example Document Mode subject
  document_notes:
    mode: document
    generation: |
      Focus on extracting clear terminology definitions and syntax details.
    files:
      - "./scratch/doc1.txt"
      - "./scratch/doc2.md"
    # OR configure folder instead:
    # folder: "./scratch/notes"
```

---

## Example Configurations

Ready-to-use example files live in the [`examples/`](examples/) directory at three levels of detail:

| File | Purpose |
|------|---------|
| `examples/config.minimal.yaml`   | One provider, one model per stage, low concurrency. |
| `examples/config.standard.yaml`  | Three providers (OpenAI + Cerebras + local Ollama) with two parallel generation models. |
| `examples/config.full.yaml`      | Every documented option: all 8 `global` keys, per-provider `timeout`/`temperature`, multiple stage-1 models, every pipeline stage commented. |
| `examples/keys.minimal.yaml`     | Single OpenAI key. |
| `examples/keys.standard.yaml`    | OpenAI (two-key rotation) + Cerebras + Ollama placeholder. |
| `examples/keys.full.yaml`        | One entry per provider declared in `config.full.yaml`, mix of single-string and array-of-strings formats. |
| `examples/prompts.minimal.yaml`  | One topic-mode subject, no defaults. |
| `examples/prompts.standard.yaml` | All five `defaults` keys (short) + `leetcode` (topic) and `notes` (document) subjects. |
| `examples/prompts.full.yaml`     | All five `defaults` keys populated with the **verbatim** hard-coded prompts shipped in `src/prompts.js` + fully worked `leetcode` and `notes` subjects. |

The `full` prompts file matches the in-source defaults byte-for-byte, so it is a safe drop-in replacement if you want every option in one place.

To use an example, copy it over the corresponding real file:
```bash
cp examples/config.full.yaml    config.yaml
cp examples/keys.full.yaml      keys.yaml
cp examples/prompts.full.yaml   prompts.yaml
```
Then edit the placeholders (API keys, file paths, subjects) to match your setup.

---

## How to Run

LLM2Deck exposes a command-line interface:

### Run Pipeline Generation
Generate flashcards for a configured subject preset or local folder:
```bash
# Run a preset topic-based subject defined in prompts.yaml
node src/cli.js run leetcode --card-type standard

# Run a preset document digestion subject defined in prompts.yaml
node src/cli.js run document_notes --card-type standard

# Run ingestion on a custom directory of local documents directly
node src/cli.js run ./study_material --card-type mcq
```

### Resume a Run
If a pipeline is interrupted, resume it using its unique Run ID:
```bash
node src/cli.js run leetcode --resume "run-12345"
```

### Compile JSON Manually
Compile a pre-generated structured JSON schema file directly to `.apkg`:
```bash
node src/cli.js compile ./output/LeetCode.json -o ./output/custom_deck.apkg
```

### Cache Management
Clear cache tables or review cache stats:
```bash
# Get stats
node src/cli.js cache stats

# Clear database cache table
node src/cli.js cache clear
```

### Running Tests
Execute unit tests for JavaScript (Vitest) and Python (Pytest):
```bash
# Run all tests (JavaScript + Python)
npm test

# Run JavaScript unit tests only
npm run test:js

# Run Python compilation unit tests only
npm run test:py (or: uv run pytest)

# Check JavaScript test coverage
npm run coverage
```

### Linting & Formatting
Verify code health and styling consistency across JavaScript and Python files:
```bash
# Run all linters (ESLint + Ruff check & format validation)
npm run lint

# Auto-fix and format all files in place
npm run lint:fix
```
