# Refactoring Backlog

## Priority 1 - Architectural Issues

### Provider Initialization Logic Split
- **Files:** `src/setup.py:49-166`, `src/providers/registry.py`
- **Problem:** Provider initialization logic is split between `registry.py` and `setup.py`. The `initialize_providers` function manually iterates through the registry and contains hardcoded special handling for `gemini_webapi`.
- **Why it matters:** Adding a new provider requires modifying `setup.py` if it needs special handling, violating the Open/Closed Principle.
- **Fix:** Refactor `ProviderRegistry` to fully encapsulate instantiation logic. Move Gemini-specific logic into its own factory/adapter.

### Global Database State
- **File:** `src/database.py:30-31, 156-178`
- **Problem:** Module relies on global `_engine` and `_SessionLocal` initialized via `init_database()`.
- **Why it matters:** Makes unit testing difficult (state persists between tests). Hard to manage multiple database connections.
- **Fix:** Use dependency injection or a `DatabaseManager` singleton class. Pass session factory to repositories instead of global `get_session()`.

### Hardcoded Key Paths
- **File:** `src/config/keys.py:54-79`
- **Problem:** Paths to key files (`CEREBRAS_KEYS_FILE_PATH`, etc.) are hardcoded constants.
- **Why it matters:** Users cannot configure key storage locations without modifying code.
- **Fix:** Move key file paths into `config.yaml` or allow environment variable overrides.

---

## Priority 2 - Code Smells

### Complex Configuration Loading
- **File:** `src/config/loader.py:160-253`
- **Problem:** Many manual `_parse_*` functions extract values from dictionaries.
- **Why it matters:** Boilerplate-heavy and error-prone.
- **Fix:** Use Pydantic models for configuration loading with automatic type validation and defaults.

### Long CLI Handlers with Mixed Concerns
- **File:** `src/cli.py:173-318`
- **Problem:** Handler functions (`handle_generate`, `handle_convert`, `handle_merge`) mix argument parsing, logging, stdout printing, and business logic.
- **Why it matters:** Hard to test and maintain.
- **Fix:** Extract business logic into dedicated service classes (`MergeService`, `ExportService`). CLI handlers should only parse args and call services.

### Anki Card Generation Duplication
- **File:** `src/anki/generator.py:138-172, 192-212`
- **Problem:** `_add_mcq_card` and `_add_basic_card` share similar logic for creating `genanki.Note` objects and handling tags.
- **Why it matters:** Code duplication increases maintenance burden.
- **Fix:** Abstract note creation into a helper method that takes the model and fields.

---

## Priority 3 - Consistency & Cleanup

### Logging vs Printing Inconsistency
- **File:** `src/cli.py:192, 194, 196`
- **Problem:** CLI uses `print()` for some status updates but `logger` for others.
- **Why it matters:** `print` output cannot be captured or silenced by logging configuration.
- **Fix:** Standardize on `logger` or the `rich` console from `src/logging_config.py` for all user output.

### Legacy Argument Normalization
- **File:** `src/cli.py:26-51`
- **Problem:** `normalize_legacy_args` exists to support old CLI syntax.
- **Why it matters:** Adds complexity and maintains two ways of doing the same thing.
- **Fix:** Deprecate old syntax with a warning, plan removal in future version.

### JSON Parsing Retry Logic
- **File:** `src/providers/openai_compatible.py:263-277`
- **Problem:** The `format_json` method implements its own retry loop for JSON parsing.
- **Why it matters:** Inconsistent with network request retries that use `tenacity`.
- **Fix:** Use `tenacity` for JSON parsing retries for consistent backoff behavior.

---

## Priority 4 - Tech Debt

### Reverse-Engineered Gemini API
- **File:** `src/setup.py:131-160`
- **Problem:** Uses `gemini_webapi` which relies on an unofficial API.
- **Why it matters:** Unstable dependency, may break without notice.
- **Fix:** Migrate to official API if available, or isolate into a strict `LLMProvider` adapter.

### Error Swallowing in Task Runner
- **File:** `src/task_runner.py:57-59`
- **Problem:** Task runner catches `Exception`, logs it, and returns `None`.
- **Why it matters:** Forces callers to handle `None` checks, may obscure systemic failures.
- **Fix:** Return a Result object (Success/Failure) or collect exceptions and raise `BatchExecutionError`.
