# LLM2Deck Refactoring Priorities

Technical debt and code quality improvements, ordered by priority.

---

## Medium Priority

### 1. Unified Provider Retry Logic
**Location:** `src/providers/`

**Current State:**
- `OpenAICompatibleProvider` has its own retry loop in `_make_request`
- `CerebrasProvider` uses native SDK but implements a separate retry mechanism
- Base class `LLMProvider` defines retry constants but no shared implementation

**Proposed Solution:**
- Create a `RetryMixin` or move retry logic to abstract base class
- Use `tenacity` library for consistent exponential backoff
- All providers inherit the same retry behavior

---

### 2. Externalize Hardcoded Configuration
**Location:** `src/config/models.py:9-18`

**Current State:**
Model names are hardcoded as Python constants:
```python
CEREBRAS_MODEL = "llama-3.3-70b"
OPENROUTER_MODEL = "deepseek/deepseek-chat-v3-0324"
```

**Proposed Solution:**
- Move model defaults to `config.yaml`
- Load models from config with fallback to defaults
- Treat configuration as data, not code

---

### 3. Prompt Loading Consolidation
**Location:** `src/prompts.py`

**Current State:**
Prompt loading logic is spread across multiple functions. The directory is configurable via env var but defaulting logic is duplicated.

**Proposed Solution:**
- Create a `PromptLoader` class with caching
- Single source of truth for prompt directory resolution
- Lazy loading with validation

---

## Low Priority

### 4. CLI Legacy Argument Shim
**Location:** `src/cli.py:292-303`

**Current State:**
The `main` function contains inline logic to convert old CLI syntax to new subcommand syntax for backward compatibility.

**Proposed Solution:**
- Extract to `normalize_legacy_args(argv: list[str]) -> list[str]`
- Keep main() clean and focused on Typer app invocation

---

### 5. Variable Naming Consistency
**Locations:** Various

**Current State:**
Some generic variable names remain:
- `q` instead of `question`
- `res` instead of `response` or `result`

**Proposed Solution:**
- Rename during related refactoring work
- Not worth a dedicated pass, but fix opportunistically

---

### 6. Test Coverage Gaps
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

- [x] Anki generator SRP - extracted `load_card_data()` (`src/anki/generator.py`)
- [x] Database abstraction in orchestrator (`src/repositories.py:RunRepository`, `src/orchestrator.py`)
- [x] Provider factory pattern (`src/providers/registry.py`, `src/setup.py`)
- [x] Repository pattern for database operations (`src/repositories.py`)
- [x] Centralized model constants (`src/config/models.py`)
- [x] Extracted concurrency logic (`src/concurrency.py`)
- [x] Custom exceptions hierarchy (`src/exceptions.py`)
- [x] TypedDict annotations for complex types
- [x] JSON utility extraction (`src/utils/json_utils.py`)
