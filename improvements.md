# LLM2Deck Improvement Plan

This document outlines potential features, refactors, and improvements for the LLM2Deck project.

## 🚀 Priority 1: Reliability & Usability

- [ ] **Unified Configuration System**
    - **Current State**: Settings are scattered across `.env`, `src/config.py`, and `src/setup.py`.
    - **Improvement**: Move all configuration to a single `config.yaml` or robust `.env` handling using `pydantic-settings`.
        - Centralize model names and API keys.
        - Add validation for configuration values.

- [ ] **Enhanced CLI with `Typer`**
    - **Improvement**: Use `Typer` for a robust CLI experience.
        - `uv run llm2deck generate --mode cs --topic "Operating Systems"`
        - `uv run llm2deck stats` (show generation stats from DB).
    - Add `--help` flags and proper error reporting.

- [ ] **Retry Logic for API Calls**
    - **Improvement**: Implement `tenacity` for extensive retry logic with exponential backoff for rate limits.

## 📊 Priority 2: Data Persistence & State Management

- [ ] **Database Integration (SQLite)**
    - **Current State**: JSON files scattered in directories. specific state tracking is difficult.
    - **Improvement**: Implement a lightweight SQLite database (using **SQLModel** or **SQLAlchemy**).
        - **Tables**: `Questions` (status: pending, generated), `Cards` (content, metadata), `Runs` (logs, costs).
        - Allows easy resuming of interrupted runs (just query `status != 'completed'`).
        - Enables complex querying/filtering for deck generation (e.g., "Create a deck with only 'Hard' DP problems generated in the last week").

- [ ] **Resume Capability**
    - **Improvement**: Leverage the new database to skip already completed questions automatically.

## � Priority 3: User Interface & Output

- [ ] **TUI (Text User Interface) Dashboard**
    - **Current State**: Continuous scrolling text log (using `Rich` currently, but linear).
    - **Improvement**: Build a full TUI using **Textual** or advanced **Rich** Live displays.
        - **Layout**:
            - **Header**: Project status, active configuration.
            - **Main Panel**: Progress bars for each concurrent worker.
            - **Side Panel**: Real-time cost estimation, token usage stats.
            - **Footer**: Active keybinds (e.g., 'q' to quit, 'p' to pause).
        - Allows "monitoring" the agent's work with better visibility than a scrolling log.

- [ ] **Logging Enhancements**
    - **Improvement**: Keep file-based logging for debugging (`debug.log`), but keep the terminal output clean and dashboard-like.

## 🛠 Priority 4: Code Quality & Naming

- [ ] **Variable Naming Refactor**
    - **Current State**: Presence of generic names (e.g., `q`, `res`, `data`).
    - **Improvement**: Enforce descriptive naming conventions.
        - `q` -> `question_context` or `problem_statement`
        - `res` -> `llm_provider_response`
        - `combiner` -> `card_merging_service`
    - Rename Providers to be more specific:
        - `GeminiProvider` -> `GoogleGeminiProvider`
        - `NvidiaProvider` -> `NIMProvider` (if using NIMs)
        - Ensure consistent interface naming (`generate_cards` vs `process_question`).

- [ ] **Standardized Error Handling**
    - **Improvement**: Define custom exceptions hierarchy (`LLM2DeckError`, `ProviderAuthError`, `ContextLimitExceeded`).

- [ ] **Type Hints & Linting**
    - **Improvement**: Enforce `mypy` strict mode and use `ruff` for all formatting/linting rules.

## 🧠 Priority 5: Advanced Prompt Engineering

- [ ] **Dynamic Prompt Routing**
    - **Current State**: Hardcoded prompt maps in `main.py`.
    - **Improvement**:
        - **Directory Structure**: Create `src/templates/{domain}/{style}.j2` (e.g., `src/templates/physics/conceptual.j2`, `src/templates/cs/algorithm_deep_dive.j2`).
        - **Configuration**: Allow mapping topics to prompt templates in `config.yaml`.
        - **Fallback**: Intelligent fallback if a specific topic template doesn't exist.

- [ ] **Prompt Versioning**
    - **Improvement**: Track prompt versions in the Database to see which version produced better cards over time.

## ✨ Priority 6: Content Features

- [ ] **Duplicate Detection**
    - **Improvement**: Use local embedding models (`sentence-transformers`) to detect and merge duplicate cards semantically.

- [ ] **Content Validation**
    - **Improvement**: Automated checks for "As an AI" refusals, empty fields, or broken formatting.

- [ ] **Rich Media**
    - **Improvement**: Automate diagram generation for CS concepts using image generation APIs.

## 📚 Priority 7: Documentation

- [ ] **Comprehensive Documentation Site**
    - **Current State**: Single README.
    - **Improvement**: Use **MkDocs** or **Sphinx** to generate a static documentation site.
        - **API Reference**: Auto-generated from docstrings.
        - **Architecture Guide**: Mermaid diagrams explaining the Provider -> Generator -> Combiner flow.
        - **Configuration Guide**: Detailed explanation of every environment variable.
        - **Prompting Guide**: How to write custom Jinja2 templates for the system.

- [ ] **Docstrings**
    - **Improvement**: Add Google-style docstrings to every public function and class.
