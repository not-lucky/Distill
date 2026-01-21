# REFACTORING.md - LLM2Deck Improvement Opportunities

## Priority 1: Critical Architecture Issues

### 1.1 Configuration Duplication and Inconsistency
**Location:** `src/config/__init__.py` + `src/config/loader.py`

**Problem:** Two parallel configuration systems exist:
- Legacy module-level constants in `src/config/__init__.py` (hardcoded paths, env vars)
- Modern Pydantic-based `AppConfig` in `src/config/loader.py`

This creates confusion about which configuration source is authoritative. `DATABASE_PATH`, `CEREBRAS_KEYS_FILE_PATH`, etc. are defined in both places with different resolution logic.

**Refactoring:**
- Deprecate all module-level constants in `src/config/__init__.py`
- Route all config access through `load_config()` -> `AppConfig`
- Update all imports across the codebase to use the unified config

### 1.2 Generator Assumes Repository Always Exists
**Location:** `src/generator.py:CardGenerator.process_question()`

**Problem:** `process_question()` unconditionally calls `self.repository.create_initial_problem()` on line 122, but `repository` can be `None` in dry-run mode. The dry-run check exists in `Orchestrator` but `CardGenerator` lacks awareness.

**Refactoring:**
- Add explicit dry-run flag to `CardGenerator`
- Guard all repository calls with `if self.repository is not None`
- Or extract a `NullRepository` pattern for dry-run mode

### 1.3 Hardcoded System Prompts
**Location:** `src/providers/openai_compatible.py` (lines 124, 172, 195)

**Problem:** System prompts like "You are a helpful assistant that generates Anki cards in JSON format." are hardcoded in multiple places (also in `cerebras.py`).

**Refactoring:**
- Move system prompts to configurable templates in `src/data/prompts/`
- Allow per-subject or per-mode system prompt customization

---

## Priority 2: Code Quality and Maintainability

### 2.1 Inconsistent Return Types in Providers
**Location:** `src/providers/base.py`, `src/providers/openai_compatible.py`

**Problem:** Method return types are inconsistent:
- `generate_initial_cards()` returns `str` (empty string on failure)
- `combine_cards()` returns `Optional[str]` (None on failure)
- `format_json()` returns `Optional[Dict[str, Any]]`

This asymmetry forces callers to handle different failure modes differently.

**Refactoring:**
- Standardize all methods to return `Optional[T]` with `None` indicating failure
- Or use a `Result[T, E]` pattern consistently (like `task_runner.py`)

### 2.2 Prompt Loader Backward Compatibility Overhead
**Location:** `src/prompts.py`

**Problem:** Module-level constants like `INITIAL_PROMPT_TEMPLATE = prompts.initial` are evaluated eagerly at import time, loading all prompt files even when not needed. This contradicts the "lazy-loading" claim in the docstring.

**Refactoring:**
- Remove module-level constant exports
- Force callers to use `prompts.initial`, `prompts.combine`, etc. directly
- Or implement true lazy loading with `__getattr__` at module level

### 2.3 Mixed Async Patterns in `setup.py`
**Location:** `src/setup.py:initialize_providers()`

**Problem:** `initialize_providers()` is async, but most provider initialization is synchronous. The only async part is `load_keys()`. This creates unnecessary complexity.

**Refactoring:**
- Make key loading synchronous (it's just file I/O)
- Convert `initialize_providers()` to sync, or
- Clearly separate async vs sync initialization

### 2.4 Subject Registry Recreates Config on Every Call
**Location:** `src/config/subjects.py:SubjectRegistry`

**Problem:** `SubjectRegistry.__init__()` calls `load_config()` on every instantiation. Creating multiple registry instances reloads and re-parses the YAML config file.

**Refactoring:**
- Cache config at module level, or
- Accept config as constructor parameter with fallback to `load_config()`
- Use singleton pattern for `SubjectRegistry`

---

## Priority 3: Missing Error Handling and Validation

### 3.1 Silent Failures in Provider Initialization
**Location:** `src/setup.py:initialize_providers()` line 68

**Problem:** Provider initialization failures are logged as warnings but silently swallowed. The orchestrator may proceed with fewer providers than expected without explicit indication.

**Refactoring:**
- Return initialization errors alongside providers
- Add a `--strict` mode that fails fast on any provider error
- Log summary: "Initialized 3/5 providers, 2 failed"

### 3.2 No Validation of Questions Data
**Location:** `src/questions.py`, `src/config/subjects.py`

**Problem:** Questions loaded from JSON files are not validated. Malformed questions (e.g., empty strings, null values) can cause runtime errors during generation.

**Refactoring:**
- Add Pydantic models for question data
- Validate questions at load time
- Provide clear error messages for invalid questions

### 3.3 Unhandled Database Session Leaks
**Location:** `src/repositories.py`

**Problem:** Each repository method opens a new session via `session_scope()`. If multiple operations need to be atomic, there's no transaction grouping.

**Refactoring:**
- Add optional `session` parameter to repository methods for explicit transaction control
- Or expose `session_scope()` at repository level for batch operations

---

## Priority 4: Performance and Scalability

### 4.1 Sequential Prompt Loading
**Location:** `src/prompts.py:PromptLoader`

**Problem:** Each prompt is loaded from disk on first access. For custom subjects with many prompts, this creates N disk reads during initialization.

**Refactoring:**
- Batch-load all prompts from a subject directory
- Consider embedding prompts as package resources

### 4.2 No Connection Pooling for Providers
**Location:** `src/providers/openai_compatible.py:_get_client()`

**Problem:** `_get_client()` creates a new `AsyncOpenAI` client for every request. This prevents HTTP connection reuse.

**Refactoring:**
- Cache client instances per API key
- Use connection pooling at the provider level
- Reuse client across multiple requests

### 4.3 Task Runner Creates Results in Completion Order
**Location:** `src/task_runner.py:run_all()`

**Problem:** `run_all()` appends results in completion order, not input order. `run_all_ordered()` exists but isn't used by the orchestrator.

**Refactoring:**
- Remove `run_all()` if order matters (which it does for reproducibility)
- Or document when to use each variant

---

## Priority 5: Testing and Observability

### 5.1 Fixtures Rely on Deprecated Patterns
**Location:** `tests/conftest.py` lines 65-70

**Problem:** `SubjectRegistry.get_config()` is called as a static method, but it's an instance method.

**Refactoring:**
- Update fixtures to instantiate `SubjectRegistry()` properly
- Add type hints to fixtures

### 5.2 No Structured Logging
**Location:** Throughout the codebase

**Problem:** Log messages are string-formatted, making it hard to query/aggregate logs. No correlation IDs for tracking a generation run across logs.

**Refactoring:**
- Add structured logging with JSON output option
- Include `run_id` in all log messages during a run
- Use `logging.LoggerAdapter` with extra context

### 5.3 Metrics and Instrumentation
**Problem:** No observability into:
- Provider response times
- API error rates by provider
- Card generation success rates

**Refactoring:**
- Add optional metrics collection (prometheus-style or simple counters)
- Expose run statistics via CLI command

---

## Priority 6: Minor Cleanup

### 6.1 Dead Code: `ENABLE_GEMINI` Environment Variable
**Location:** `src/config/__init__.py`, `src/setup.py`

**Problem:** `ENABLE_GEMINI` env var support is deprecated but still implemented. It adds complexity to `initialize_providers()`.

**Refactoring:**
- Remove `ENABLE_GEMINI` support entirely
- Document migration path in changelog

### 6.2 Unused Type Aliases
**Location:** `src/types.py`

**Problem:** `CardData`, `MCQCardData`, `ProviderResultData` TypedDicts are defined but not used anywhere in the codebase.

**Refactoring:**
- Either use these types to annotate relevant code
- Or remove unused definitions

### 6.3 Inconsistent Naming: `strip_json_block` vs `strip_json_markers`
**Location:** `src/utils.py`, `src/config/loader.py`

**Problem:** Config uses `strip_json_markers` but utility function is `strip_json_block`.

**Refactoring:**
- Align naming across config and implementation

### 6.4 Magic Numbers in Anki Generator
**Location:** `src/anki/generator.py`

**Problem:** `category_index:03d` format assumes < 1000 categories. Options padded to 4 without constant.

**Refactoring:**
- Extract format strings as constants
- Document or make configurable

---

## Implementation Notes

When implementing these refactorings:
1. Add tests before changing behavior
2. Use deprecation warnings for breaking API changes
3. Update `CLAUDE.md` if architectural patterns change
4. Keep each refactoring as a separate commit for easy review/revert
