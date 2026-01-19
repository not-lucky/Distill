# LLM2Deck Refactoring Priorities

Technical debt and code quality improvements, ordered by priority.

---

## Completed

Items moved here after completion:

- [x] CLI legacy argument shim - extracted `normalize_legacy_args()` (`src/cli.py`)
- [x] Variable naming consistency - resolved opportunistically (no instances found)
- [x] Test coverage gaps - added Orchestrator unit tests (`tests/test_orchestrator.py`)
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
