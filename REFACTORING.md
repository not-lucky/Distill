# LLM2Deck Refactoring Priorities

Technical debt and code quality improvements, ordered by priority.

---

## Low Priority

### 1. CLI Legacy Argument Shim
**Location:** `src/cli.py:292-303`

**Current State:**
The `main` function contains inline logic to convert old CLI syntax to new subcommand syntax for backward compatibility.

**Proposed Solution:**
- Extract to `normalize_legacy_args(argv: list[str]) -> list[str]`
- Keep main() clean and focused on Typer app invocation

---

### 2. Variable Naming Consistency
**Locations:** Various

**Current State:**
Some generic variable names remain:
- `q` instead of `question`
- `res` instead of `response` or `result`

**Proposed Solution:**
- Rename during related refactoring work
- Not worth a dedicated pass, but fix opportunistically

---

### 3. Test Coverage Gaps
**Location:** `tests/`

**Current State:**
Some core modules lack comprehensive unit tests, particularly:
- `src/orchestrator.py`
- `src/generator.py`

**Proposed Solution:**
- Add unit tests with mocked providers
- Focus on error handling paths
- Address during related refactoring

---

## Completed

Items moved here after completion:

- [x] Externalized hardcoded configuration - removed `DEFAULT_MODELS` dict (`src/config/models.py`, `src/config/loader.py`)
- [x] Prompt loading consolidation - created `PromptLoader` class with lazy loading (`src/prompts.py`)
- [x] Unified provider retry logic with tenacity (`src/providers/base.py`, `src/providers/openai_compatible.py`, `src/providers/cerebras.py`)
- [x] Anki generator SRP - extracted `load_card_data()` (`src/anki/generator.py`)
- [x] Database abstraction in orchestrator (`src/repositories.py:RunRepository`, `src/orchestrator.py`)
- [x] Provider factory pattern (`src/providers/registry.py`, `src/setup.py`)
- [x] Repository pattern for database operations (`src/repositories.py`)
- [x] Centralized model constants (`src/config/models.py`)
- [x] Extracted concurrency logic (`src/concurrency.py`)
- [x] Custom exceptions hierarchy (`src/exceptions.py`)
- [x] TypedDict annotations for complex types
- [x] JSON utility extraction (`src/utils/json_utils.py`)
