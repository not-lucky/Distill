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

## Priority 3: Medium (Improve Maintainability) - COMPLETED

### 3.1 ~~Unify Subject Configuration~~ DONE

**Files changed:**
- `src/config/subjects.py` - Added `name`, `combine_prompt`, `deck_prefix`, `deck_prefix_mcq` fields to `SubjectConfig`
- `src/generator.py` - Now accepts `combine_prompt` parameter instead of mode-based selection
- `src/anki/generator.py` - Now accepts `deck_prefix` parameter instead of mode-based switch

**Result:** All subject-specific configuration is now centralized in `SubjectConfig`. Adding a new subject requires updating only `src/config/subjects.py`.

---

### 3.2 ~~Refactor `main.py` Entry Point~~ DONE

**Files created:**
- `src/orchestrator.py` - Class-based `Orchestrator` for the main execution flow
- `src/cli.py` - Unified CLI with argparse subcommands

**Files changed:**
- `main.py` - Reduced to minimal entry point (8 lines)

**Result:** Clean separation of concerns with CLI parsing, orchestration, and execution in separate modules.

---

### 3.3 ~~Move Utility Scripts~~ DONE

**Integrated into CLI:**
- `json_to_md.py` -> `llm2deck export-md`
- `merge_anki_json.py` -> `llm2deck merge`
- `convert_to_apkg.py` -> `llm2deck convert`

**Moved test scripts:**
- `g4f_test.py` -> `tests/experiments/g4f_test.py`
- `verify_google_genai.py` -> `tests/experiments/verify_google_genai.py`

**Added:**
- `[project.scripts]` entry point in `pyproject.toml` for `llm2deck` command

**Result:** Single unified CLI with subcommands. Old-style syntax (`main.py leetcode mcq`) still works via backward compatibility.

---

## Priority 4: Low (Nice to Have) - COMPLETED

### 4.1 ~~Add Test Coverage~~ DONE

**Files created:**
```
tests/
├── conftest.py                   # Shared pytest fixtures
├── test_config.py                # SubjectRegistry and SubjectConfig tests
├── test_generator.py             # CardGenerator unit tests
├── test_integration.py           # Integration test with real Cerebras API
├── test_providers/
│   ├── __init__.py
│   └── test_cerebras.py          # CerebrasProvider unit tests
└── test_anki/
    ├── __init__.py
    └── test_generator.py         # DeckGenerator unit tests
```

**Test configuration added to `pyproject.toml`:**
- pytest and pytest-asyncio dependencies
- asyncio_mode = "auto"
- Markers for integration tests

**Run tests:**
```bash
uv run pytest tests/ -v                    # All tests
uv run pytest tests/ -v -m "not integration"  # Unit tests only
uv run pytest tests/ -v -m integration     # Integration tests only
```

---

### 4.2 ~~Improve Error Handling~~ DONE

**Files created:**
- `src/exceptions.py` - Custom exception hierarchy

**Exception classes:**
- `LLM2DeckError` - Base exception
- `ProviderError` - Base for provider errors
- `APIKeyError` - Missing/invalid API keys
- `GenerationError` - Card generation failures
- `CombinationError` - Card combination failures
- `JSONParseError` - JSON parsing failures
- `ConfigurationError` - Configuration issues
- `SubjectError` - Invalid subject configuration
- `DatabaseError` - Database operation failures

**Standardized retry behavior:**
- Added constants to `LLMProvider` base class:
  - `DEFAULT_MAX_RETRIES = 5`
  - `DEFAULT_JSON_PARSE_RETRIES = 3`
  - `DEFAULT_RETRY_DELAY = 1.0`
- Updated `CerebrasProvider` and `OpenAICompatibleProvider` to use these constants

---

### 4.3 ~~Configuration File~~ DONE

**Files created:**
- `config.yaml` - Unified configuration file
- `src/config/loader.py` - Configuration loader with dataclasses

**Configuration structure:**
```yaml
providers:
  cerebras:
    enabled: true
    model: "gpt-oss-120b"
    reasoning_effort: "high"
  # ... other providers

generation:
  concurrent_requests: 8
  max_retries: 5
  json_parse_retries: 3

database:
  path: "llm2deck.db"
```

**Updated:**
- `src/setup.py` now reads from `config.yaml` via `load_config()`
- Providers are enabled/disabled through config file instead of code comments

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
| setup.py | 289 | 183 | -106 lines |
| generator.py | 248 | 207 | -41 lines |
| Files to touch when adding provider | 2-3 | 1 | Improved |
| Test coverage | 0% | 32 tests | Implemented |

### Progress Summary

- **Priority 1 (Critical):** COMPLETED
- **Priority 2 (High):** COMPLETED (except provider registry, deferred)
- **Priority 3 (Medium):** COMPLETED
- **Priority 4 (Low):** COMPLETED
