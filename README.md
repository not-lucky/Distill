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
Use `uv` to create a virtual environment and sync python dependencies:
```bash
uv venv
uv pip install -r requirements.txt
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

```yaml
# Default prompt overrides for stages
defaults:
  generation: |
    You are a world-class educator. Extract concepts...
  synthesis: |
    You are a senior technical editor. Consolidate and merge...

# Subject presets mapping. 
# Match directly via CLI argument (e.g. `node src/cli.js run leetcode`).
subjects:
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

  javascript:
    generation: |
      Special Guidelines for JavaScript:
      - Predict execution output (closures, scopes, event loop queues)
    categories:
      - name: "Basics"
        topics:
          - "Closures"
          - "Event Loop"
```

---

## How to Run

LLM2Deck exposes a command-line interface:

### Run Pipeline Generation
Generate flashcards for a configured subject preset or local folder:
```bash
# Run a preset subject defined in prompts.yaml
node src/cli.js run leetcode --card-type standard

# Run ingestion on a custom directory of local documents
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
Execute unit tests or test coverage using Vitest:
```bash
# Run tests
npm run test

# Check code coverage
npm run coverage
```
