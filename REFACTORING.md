# LLM2Deck Refactoring Plan

## Summary

This document outlines a comprehensive refactoring plan for LLM2Deck. The codebase has grown organically and now has ~4,167 lines across 20+ Python files. The main issues are:

- **Massive provider duplication** (~1,200 lines, 9 providers with near-identical code)
- **Dead code** in critical paths
- **Scattered configuration** across multiple files
- **No test coverage**
- **Tight coupling** between components

---

## Priority 1: Critical (Fix Immediately) - COMPLETED

### 1.1 ~~Remove Dead Code in `src/generator.py`~~ DONE

**File:** `src/generator.py:209-247`

**Issue:** Lines 209-247 were unreachable (after a `return` statement). This was a copy-paste artifact that referenced a non-existent `save_archival` function.

**Action:** ~~Delete lines 209-247.~~ Deleted 40 lines of dead code.

**Impact:** Removes confusion and potential maintenance errors.

---

### 1.2 ~~Fix Bare `except:` Clause~~ DONE

**File:** `src/generator.py:105-106`

**Issue:** Was catching all exceptions silently:
```python
except:
    card_count = None
```

**Action:** ~~Replace with `except (json.JSONDecodeError, KeyError, TypeError):`~~ Fixed.

**Impact:** Prevents swallowing unexpected errors silently.

---

## Priority 2: High (Major Code Reduction) - COMPLETED

### 2.1 ~~Create `OpenAICompatibleProvider` Base Class~~ DONE

**Files affected:**
- `src/providers/cerebras.py` (149 → 163 lines, kept separate due to native SDK)
- `src/providers/nvidia.py` (155 → 29 lines)
- `src/providers/openrouter.py` (~150 → 22 lines)
- `src/providers/canopywave.py` (144 → 23 lines)
- `src/providers/baseten.py` (131 → 23 lines)
- `src/providers/google_antigravity.py` (142 → 23 lines)

**New file:** `src/providers/openai_compatible.py` (233 lines) - shared base class

**Result:** Provider files now only define:
- `__init__` with provider-specific config
- `name` property
- Optional `_get_extra_request_params()` for custom params

**Actual reduction:** ~400 lines removed from individual providers.

---

### 2.2 ~~Consolidate Key Loading in `src/setup.py`~~ DONE

**Files changed:**
- `src/setup.py` (289 → 150 lines)
- **New:** `src/config/keys.py` (117 lines) - unified key loader

**Result:** Single `load_keys(provider_name)` function replaces 7 separate functions.

**Actual reduction:** ~140 lines removed (net: 289 → 150 + 117 = 267 total, but much cleaner).

---

### 2.3 Create Provider Registry

**Status:** Deferred to Priority 3 (not critical for functionality)

---

## Priority 3: Medium (Improve Maintainability)

### 3.1 Unify Subject Configuration

**Files affected:**
- `src/config/subjects.py`
- `src/anki/generator.py` (hardcoded prefixes)
- `src/generator.py` (mode-based prompt selection)

**Issue:** Subject-specific logic is scattered:
- `SubjectRegistry` defines prompts and models
- `DeckGenerator._get_prefix()` has hardcoded switch for deck names
- `CardGenerator` has hardcoded mode-to-prompt mapping

**Action:** Centralize all subject config:

```python
# src/config/subjects.py
@dataclass
class SubjectConfig:
    name: str
    deck_prefix: str
    initial_prompt: str
    combine_prompt: str
    model_class: Type[BaseModel]
    questions: Dict[str, List[str]]

SUBJECTS = {
    "leetcode": SubjectConfig(
        name="leetcode",
        deck_prefix="LeetCode",
        initial_prompt=INITIAL_LEETCODE_PROMPT,
        combine_prompt=COMBINE_LEETCODE_PROMPT,
        model_class=LeetCodeProblem,
        questions=load_questions("leetcode")
    ),
    # ...
}
```

**Benefits:**
- Adding a subject requires only updating this one file
- No more hardcoded switch statements

---

### 3.2 Refactor `main.py` Entry Point

**File:** `main.py` (157 lines)

**Issue:** Main file mixes CLI parsing, orchestration, and async execution.

**Action:**
1. Extract CLI argument parsing to `src/cli.py`
2. Create `src/orchestrator.py` for the main execution flow
3. Keep `main.py` minimal (just entry point)

---

### 3.3 Move Utility Scripts

**Files:**
- `json_to_md.py` (99 lines)
- `merge_anki_json.py` (87 lines)
- `g4f_test.py` (22 lines) - should this be deleted?
- `verify_google_genai.py` (34 lines) - should this be deleted?

**Action:**
- Move to `src/cli/` or `scripts/` directory
- Consider making them subcommands of a unified CLI
- Delete test/verification scripts if no longer needed

---

## Priority 4: Low (Nice to Have)

### 4.1 Add Test Coverage

**Issue:** Zero test files exist.

**Action:** Add tests in `tests/` directory:
```
tests/
  conftest.py
  test_providers/
    test_base.py
    test_openai_compatible.py
  test_generator.py
  test_config.py
  test_anki/
    test_generator.py
```

**Focus areas:**
1. Provider base class methods
2. JSON schema validation
3. Card combination logic
4. Anki deck generation

---

### 4.2 Improve Error Handling

**Files:** All providers

**Issue:**
- Inconsistent retry counts (3 vs 5 vs 7)
- No structured error types
- Failures return `None` with no context

**Action:**
1. Create `src/exceptions.py` with custom exceptions
2. Standardize retry behavior in base class
3. Use structured error responses

---

### 4.3 Configuration File

**Issue:** Settings scattered across `.env`, `src/config/__init__.py`, and hardcoded values.

**Action:** Create unified `config.yaml`:

```yaml
providers:
  nvidia:
    enabled: true
    model: "deepseek-ai/deepseek-v3.2"
    timeout: 900
  cerebras:
    enabled: true
    model: "gpt-oss-120b"
    reasoning_effort: "high"

generation:
  concurrent_requests: 8
  max_retries: 5

subjects:
  leetcode:
    enabled: true
  cs:
    enabled: false
```

---

## Proposed File Structure (After Refactor)

```
LLM2Deck/
├── main.py                    # Minimal entry point
├── config.yaml                # Unified configuration
├── src/
│   ├── cli.py                 # Argument parsing
│   ├── orchestrator.py        # Main execution flow
│   ├── exceptions.py          # Custom exceptions
│   ├── config/
│   │   ├── __init__.py
│   │   ├── subjects.py        # All subject config
│   │   └── keys.py            # Unified key loading
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py            # LLMProvider ABC
│   │   ├── openai_compatible.py  # NEW: shared base
│   │   ├── registry.py        # NEW: provider registry
│   │   ├── cerebras.py        # Minimal (~30 lines)
│   │   ├── nvidia.py          # Minimal (~30 lines)
│   │   └── ...
│   ├── generator.py           # Card generation (cleaned)
│   ├── database.py
│   ├── models.py
│   └── anki/
│       └── ...
├── scripts/                   # Utility scripts
│   ├── json_to_md.py
│   └── merge_anki_json.py
└── tests/
    └── ...
```

---

## Implementation Order

### Phase 1: Quick Wins (Immediate)
1. Delete dead code in `generator.py:209-247`
2. Fix bare except clause
3. Delete unused test files (`g4f_test.py`, `verify_google_genai.py`) if confirmed

### Phase 2: Provider Refactor
1. Create `OpenAICompatibleProvider` base class
2. Refactor one provider (nvidia) as template
3. Refactor remaining 5 OpenAI-compatible providers
4. Handle special providers (Gemini, G4F, GoogleGenAI)

### Phase 3: Configuration
1. Create unified key loader
2. Implement provider registry
3. Centralize subject configuration

### Phase 4: Testing & Polish
1. Add pytest infrastructure
2. Write tests for refactored code
3. Add configuration file support
4. Update documentation

---

## Metrics

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Total lines | ~4,167 | ~3,767 | -400 lines |
| Provider code | ~1,200 | ~948 | -252 lines |
| setup.py | 289 | 150 | -139 lines |
| generator.py | 248 | 207 | -41 lines |
| Files to touch when adding provider | 2-3 | 1 | Improved |
| Test coverage | 0% | 0% | Pending |

### Progress Summary

- **Priority 1 (Critical):** COMPLETED
- **Priority 2 (High):** COMPLETED (except provider registry, deferred)
- **Priority 3 (Medium):** Pending
- **Priority 4 (Low):** Pending
