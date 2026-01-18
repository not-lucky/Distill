# LLM2Deck Refactoring Priorities

Technical debt and code quality improvements, ordered by priority.

---

## High Priority

### 1. Provider Factory Pattern
**Location:** `src/setup.py:51-183`

**Current State:**
The `initialize_providers` function is a 130+ line monolith that repeats the same pattern for every provider:
1. Check if enabled in config
2. Load API keys
3. Instantiate provider
4. Handle errors

This violates the Open/Closed Principle - adding a new provider requires modifying this function.

**Proposed Solution:**
- Create a `ProviderRegistry` that maps provider names to their classes
- Define a `ProviderFactory` that instantiates providers from config
- Each provider registers itself with metadata (required keys, config path)

```python
# Example structure
PROVIDER_REGISTRY = {
    "cerebras": (CerebrasProvider, "cerebras_keys.json"),
    "openrouter": (OpenRouterProvider, "openrouter_keys.json"),
}

def initialize_providers(config: dict) -> list[LLMProvider]:
    providers = []
    for name, enabled in config.get("providers", {}).items():
        if not enabled:
            continue
        cls, key_file = PROVIDER_REGISTRY[name]
        keys = load_keys(key_file)
        providers.append(cls(api_keys=iter(keys)))
    return providers
```

---

### 2. Database Abstraction Leakage
**Location:** `src/orchestrator.py:64-80, 149-158`

**Current State:**
`Orchestrator` directly manages database sessions and calls low-level DB functions (`init_database`, `create_run`, `update_run`). This mixes orchestration concerns with persistence.

**Proposed Solution:**
- Extend the existing `CardRepository` (or create `RunRepository`) to handle run lifecycle
- Orchestrator should only interact with repositories, never with raw sessions
- Use dependency injection for the repository

---

## Medium Priority

### 3. Anki Generator Single Responsibility
**Location:** `src/anki/generator.py:125-160`

**Current State:**
`DeckGenerator` handles:
- File I/O (loading JSON)
- Deck structure logic (naming, hierarchy)
- HTML content rendering (inside `_add_mcq_card`)

**Proposed Solution:**
- Extract `CardRenderer` class for HTML generation
- Move JSON loading to a separate utility or caller responsibility
- Keep `DeckGenerator` focused solely on deck structure

---

### 4. Unified Provider Retry Logic
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

### 5. Externalize Hardcoded Configuration
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

### 6. Prompt Loading Consolidation
**Location:** `src/prompts.py`

**Current State:**
Prompt loading logic is spread across multiple functions. The directory is configurable via env var but defaulting logic is duplicated.

**Proposed Solution:**
- Create a `PromptLoader` class with caching
- Single source of truth for prompt directory resolution
- Lazy loading with validation

---

## Low Priority

### 7. CLI Legacy Argument Shim
**Location:** `src/cli.py:292-303`

**Current State:**
The `main` function contains inline logic to convert old CLI syntax to new subcommand syntax for backward compatibility.

**Proposed Solution:**
- Extract to `normalize_legacy_args(argv: list[str]) -> list[str]`
- Keep main() clean and focused on Typer app invocation

---

### 8. Variable Naming Consistency
**Locations:** Various

**Current State:**
Some generic variable names remain:
- `q` instead of `question`
- `res` instead of `response` or `result`

**Proposed Solution:**
- Rename during related refactoring work
- Not worth a dedicated pass, but fix opportunistically

---

### 9. Test Coverage Gaps
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

- [x] Repository pattern for database operations (`src/repository.py`)
- [x] Centralized model constants (`src/config/models.py`)
- [x] Extracted concurrency logic (`src/concurrency.py`)
- [x] Custom exceptions hierarchy (`src/exceptions.py`)
- [x] TypedDict annotations for complex types
- [x] JSON utility extraction (`src/utils/json_utils.py`)
