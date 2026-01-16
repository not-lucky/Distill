# LLM2Deck Refactoring Plan

## Summary

This document outlines a comprehensive refactoring plan for LLM2Deck. The codebase has grown organically and now has ~4,167 lines across 20+ Python files. The main issues are:

- **Massive provider duplication** (~1,200 lines, 9 providers with near-identical code)
- **Dead code** in critical paths
- **Scattered configuration** across multiple files
- **No test coverage**
- **Tight coupling** between components

---

## Priority 1: Critical (Fix Immediately)

### 1.1 Remove Dead Code in `src/generator.py`

**File:** `src/generator.py:209-247`

**Issue:** Lines 209-247 are unreachable (after a `return` statement). This is a copy-paste artifact that references a non-existent `save_archival` function.

**Action:** Delete lines 209-247.

**Impact:** Removes confusion and potential maintenance errors.

---

### 1.2 Fix Bare `except:` Clause

**File:** `src/generator.py:105-106`

```python
except:
    card_count = None
```

**Action:** Replace with `except (json.JSONDecodeError, KeyError, TypeError):` or at minimum `except Exception:`.

**Impact:** Prevents swallowing unexpected errors silently.

---

## Priority 2: High (Major Code Reduction)

### 2.1 Create `OpenAICompatibleProvider` Base Class

**Files affected:**
- `src/providers/cerebras.py` (149 lines)
- `src/providers/nvidia.py` (155 lines)
- `src/providers/openrouter.py` (~150 lines)
- `src/providers/canopywave.py` (144 lines)
- `src/providers/baseten.py` (131 lines)
- `src/providers/google_antigravity.py` (142 lines)

**Issue:** 6 providers share 80%+ identical code:
- Same `__init__` pattern (api_keys iterator, model name)
- Same `_make_request` logic (retry loop, error handling)
- Identical `generate_initial_cards` implementation
- Identical `combine_cards` implementation
- Only differences: base_url, client instantiation, provider-specific parameters

**Action:** Create a mid-level abstract class:

```python
# src/providers/openai_compatible.py
class OpenAICompatibleProvider(LLMProvider):
    """Base class for providers using OpenAI-compatible APIs."""

    def __init__(self, api_keys, model: str, base_url: str, **kwargs):
        self.api_key_iterator = api_keys
        self.model_name = model
        self.base_url = base_url
        self.extra_config = kwargs

    @property
    def model(self) -> str:
        return self.model_name

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=next(self.api_key_iterator),
            base_url=self.base_url,
            timeout=self.extra_config.get("timeout", 120.0)
        )

    async def _make_request(self, messages, json_schema, max_retries=5) -> Optional[str]:
        # Centralized retry logic with exponential backoff
        # Centralized JSON block stripping
        pass

    async def generate_initial_cards(self, question, json_schema, prompt_template=None) -> str:
        # Standard implementation - subclasses can override
        pass

    async def combine_cards(self, question, combined_inputs, json_schema, combine_prompt=None) -> Optional[Dict]:
        # Standard implementation - subclasses can override
        pass
```

**Result:** Each provider reduces to ~20-30 lines:

```python
# src/providers/nvidia.py (after refactor)
class NvidiaProvider(OpenAICompatibleProvider):
    def __init__(self, api_keys, model: str):
        super().__init__(
            api_keys=api_keys,
            model=model,
            base_url="https://integrate.api.nvidia.com/v1",
            timeout=900.0
        )

    @property
    def name(self) -> str:
        return "llm2deck_nvidia"
```

**Estimated reduction:** ~600 lines removed across 6 providers.

---

### 2.2 Consolidate Key Loading in `src/setup.py`

**File:** `src/setup.py` (289 lines)

**Issue:** 7 nearly identical `load_*_keys()` functions, each ~20 lines. The only differences are:
- File path
- JSON extraction path (`["api_key"]` vs `["data"]["key"]`)

**Action:** Create a unified key loader:

```python
# src/config/keys.py
from dataclasses import dataclass
from typing import Callable, List
from pathlib import Path

@dataclass
class KeyConfig:
    path: Path
    extractor: Callable[[list], List[str]]

KEY_CONFIGS = {
    "cerebras": KeyConfig(
        path=CEREBRAS_KEYS_FILE_PATH,
        extractor=lambda data: [item["api_key"] for item in data]
    ),
    "openrouter": KeyConfig(
        path=OPENROUTER_KEYS_FILE,
        extractor=lambda data: [item["data"]["key"] for item in data]
    ),
    "nvidia": KeyConfig(
        path=NVIDIA_KEYS_FILE,
        extractor=lambda data: data if isinstance(data[0], str) else [item["api_key"] for item in data]
    ),
    # ... etc
}

async def load_keys(provider_name: str) -> List[str]:
    """Load and shuffle API keys for any provider."""
    config = KEY_CONFIGS.get(provider_name)
    if not config or not config.path.exists():
        logger.warning(f"{provider_name} keys file not found")
        return []

    with open(config.path) as f:
        data = json.load(f)

    keys = config.extractor(data)
    shuffle(keys)
    return keys
```

**Estimated reduction:** ~100 lines removed.

---

### 2.3 Create Provider Registry

**File:** New `src/providers/registry.py`

**Issue:** Adding a provider requires:
1. Creating the provider file
2. Importing in `src/setup.py`
3. Adding key loading logic
4. Adding instantiation code

**Action:** Create a registry pattern:

```python
# src/providers/registry.py
PROVIDER_REGISTRY: Dict[str, Type[LLMProvider]] = {}

def register_provider(name: str):
    """Decorator to register providers."""
    def decorator(cls):
        PROVIDER_REGISTRY[name] = cls
        return cls
    return decorator

# Usage in provider files:
@register_provider("nvidia")
class NvidiaProvider(OpenAICompatibleProvider):
    ...
```

**Benefits:**
- New providers auto-register
- `initialize_providers()` becomes data-driven
- Provider enable/disable via config file

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

| Metric | Before | After (Projected) |
|--------|--------|-------------------|
| Total lines | ~4,167 | ~2,800 |
| Provider code | ~1,200 | ~400 |
| setup.py | 289 | ~80 |
| Files to touch when adding provider | 2-3 | 1 |
| Test coverage | 0% | 60%+ |
