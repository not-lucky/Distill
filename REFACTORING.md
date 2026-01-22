# Refactoring Opportunities

This document outlines potential improvements to the LLM2Deck codebase, organized by priority.

---

## Priority 1: High Impact, Low Risk (COMPLETED)

### 1.1 Consolidate Pydantic Problem Models - DONE

**Files:** `src/models.py`

**Status:** Implemented. Created `BaseProblem` class that `LeetCodeProblem`, `CSProblem`, `PhysicsProblem`, and `GenericProblem` inherit from.

---

### 1.2 Remove Deprecated Global Database State - DONE

**Files:** `src/database.py`

**Status:** Implemented. Removed `_engine` and `_SessionLocal` globals. Added deprecation warnings to wrapper functions. Updated call sites in `tests/conftest.py`, `src/queries.py`, and `src/repositories.py` to use `DatabaseManager` directly.

---

### 1.3 Dynamic Prompt Loading - DONE

**Files:** `src/prompts.py`, `src/providers/*.py`

**Status:** Implemented. Module-level constants now use `__getattr__` with deprecation warnings. All providers updated to use `prompts` singleton instead of importing deprecated constants. Added deprecation warning to `load_prompt()` function.

---

## Priority 2: Medium Impact, Medium Risk

### 2.1 Data-Driven Subject Configuration

**Files:** `src/config/subjects.py`

**Issue:** `_get_builtin_config()` (lines 92-146) contains multiple hardcoded dictionaries (`questions_map`, `default_prefixes`, `config_map`) that map subject names to resources. This violates the Open/Closed principle.

**Recommendation:** Move built-in subject definitions to a configuration file (YAML or JSON) or a data structure within the module, using the same format as custom subjects.

```yaml
# Example: subjects could be defined uniformly
subjects:
  leetcode:
    builtin: true
    deck_prefix: "LeetCode"
    model: LeetCodeProblem
    questions: "src/data/questions.json#leetcode"
```

---

### 2.2 Consolidate Database CRUD Functions into Repositories

**Files:** `src/database.py`, `src/repositories.py`

**Issue:** `database.py` contains CRUD functions (`create_run`, `update_run`, `create_problem`, etc.) that are called by the repositories. This creates a two-layer abstraction where the repositories are thin wrappers.

**Recommendation:** Merge CRUD logic directly into repository classes, making repositories the single point of data access.

---

### 2.3 Simplify Provider Initialization Logic

**Files:** `src/setup.py`

**Issue:** `initialize_providers()` has complex conditional logic for determining combiner/formatter roles (lines 77-105). The `also_generate` flag adds additional complexity.

**Recommendation:** Consider a more explicit configuration approach where provider roles are declared upfront rather than inferred from matching.

---

## Priority 3: Lower Impact, Larger Scope

### 3.1 Extract CLI Handlers to Service Layer

**Files:** `src/cli.py`

**Issue:** CLI handlers (`handle_convert`, `handle_merge`, `handle_export_md`) contain business logic mixed with argument parsing. The `handle_generate` function imports `Orchestrator` inline.

**Recommendation:** Extract handler logic into dedicated service classes (partially done with `MergeService`, `ExportService`). Apply the same pattern to `convert` and `generate` commands.

---

### 3.2 Standardize Error Types

**Files:** `src/exceptions.py`, `src/providers/base.py`

**Issue:** Error types are split between `src/exceptions.py` and `src/providers/base.py` (retry-related errors). This creates inconsistency in where to find error classes.

**Recommendation:** Consolidate all custom exceptions in `src/exceptions.py` or create a clear hierarchy (e.g., `exceptions/` package with submodules for providers, generation, etc.).

---

### 3.3 Remove Backward Compatibility Shims

**Files:** `src/config/subjects.py:205-215`, `src/prompts.py:181-197`, `src/database.py:259-288`

**Issue:** Multiple backward-compatible functions and constants exist for legacy code support. These add maintenance burden.

**Recommendation:** After confirming no external dependencies, remove:
- `get_subject_config()` convenience function
- `load_prompt()` function
- Module-level prompt constants (`INITIAL_PROMPT_TEMPLATE`, etc.)
- Global `init_database()`, `get_session()`, `session_scope()` wrappers

---

### 3.4 Type Annotation Improvements

**Files:** Various

**Specific improvements:**
- `src/orchestrator.py:139` - Use `Tuple[int, str, int, str]` type alias for question metadata
- `src/generator.py:203` - `model_class: Type[BaseModel]` default should not be `LeetCodeProblem`
- `src/types.py` - Define and use `CardResult` type more consistently

---

### 3.5 DRY Up Task Runner Methods

**Files:** `src/task_runner.py`

**Issue:** `run_all()` and `run_all_ordered()` (lines 63-134) have duplicated logic for semaphore-based concurrency and request delay handling.

**Recommendation:** Extract shared logic into a private method, or unify into a single method with an `ordered` parameter.

---

### 3.6 Lazy Question Loading

**Files:** `src/questions.py`

**Issue:** Line 71 loads questions at module import time (`QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS = load_questions()`). This causes file I/O during import and makes testing harder.

**Recommendation:** Use lazy loading pattern (e.g., `cached_property` or a singleton loader similar to `PromptLoader`).

---

### 3.7 DRY Up Config Validation Functions

**Files:** `src/config/loader.py`

**Issue:** `get_combiner_config()` (lines 206-243) and `get_formatter_config()` (lines 246-283) have nearly identical validation logic for provider existence, enabled status, and model matching.

**Recommendation:** Extract common validation into a shared helper function.

```python
def _validate_provider_reference(
    config: AppConfig,
    provider_name: str,
    model: str,
    role: str  # "Combiner" or "Formatter"
) -> None:
    # Common validation logic
```

---

### 3.8 Deterministic MCQ Option Shuffling

**Files:** `src/anki/generator.py`

**Issue:** `_shuffle_options()` (line 182) uses `random.shuffle()` without seeding, producing non-deterministic output between runs for the same input.

**Recommendation:** Either seed the random generator with a deterministic value (e.g., hash of question content), or make shuffling optional/configurable.

---

### 3.9 Remove Usage of Deprecated Prompt Constants

**Files:** `src/providers/openai_compatible.py`

**Issue:** Lines 20-21 import deprecated module-level constants (`INITIAL_PROMPT_TEMPLATE`, `COMBINE_PROMPT_TEMPLATE`).

**Recommendation:** After implementing dynamic prompt loading (1.3), update this file to use the `prompts` singleton or accept templates as constructor parameters.

---

### 3.10 Provider Registry Conditional Complexity

**Files:** `src/providers/registry.py`

**Issue:** `create_provider_instances()` (lines 104-182) has multiple conditional branches for different provider types (`multi_model`, `uses_base_url`, `key_name`, etc.).

**Recommendation:** Consider a strategy pattern or builder pattern where each `ProviderSpec` knows how to construct its own instances, reducing the central function complexity.

---

### 3.11 Anki Generator Hash Function

**Files:** `src/anki/generator.py`

**Issue:** `_generate_id()` (line 53) uses MD5 for ID generation. While not a security concern here, MD5 is deprecated for cryptographic use.

**Recommendation:** Use a non-cryptographic hash (e.g., `hash()` or `xxhash`) or document that MD5 is intentionally used for deterministic ID generation only.

---

## Priority 4: Code Quality & Testing

### 4.1 Add Integration Tests for Provider Workflow

**Issue:** The provider initialization -> generation -> combination flow lacks integration tests.

**Recommendation:** Add tests that mock LLM responses and verify the full workflow.

---

### 4.2 Configuration Schema Validation

**Issue:** Configuration errors are only caught at runtime when `load_config()` is called.

**Recommendation:** Add a CLI command (`llm2deck config validate`) or pre-flight check to validate configuration before running generation.

---

### 4.3 Centralize Magic Strings

**Files:** Various

**Issue:** Status strings like `"running"`, `"completed"`, `"failed"` are used as literals throughout the codebase.

**Recommendation:** Create an enum or constants module for status values.

```python
class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

---

### 4.4 Improve Dry Run Consistency

**Files:** `src/orchestrator.py`, `src/cli.py`, `src/generator.py`

**Issue:** Dry run logic is scattered across multiple files with varying levels of implementation.

**Recommendation:** Consider a `DryRunContext` or similar pattern to centralize dry run behavior.

---

## Notes

- Priority 1 items can be addressed independently with minimal risk
- Priority 2 items require more careful planning and may affect multiple modules
- Priority 3 items are quality-of-life improvements that can be addressed incrementally
- Priority 4 items focus on code quality and testing infrastructure
