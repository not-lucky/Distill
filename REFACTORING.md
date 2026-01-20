# Refactoring Priorities

## High Priority

### 1. Provider Code Duplication
**Files:** `src/providers/openai_compatible.py`, `src/providers/cerebras.py`, `src/providers/base.py`

**Issue:** Significant logic duplication between `OpenAICompatibleProvider` and `CerebrasProvider`:
- JSON parsing and retry loop (`DEFAULT_JSON_PARSE_RETRIES`) is duplicated
- Exception handling for `json.JSONDecodeError` is repeated
- Prompt message construction (system + user) is duplicated

**Recommendation:**
- Extract "Request → Parse JSON → Retry" loop into base `LLMProvider` or a `JsonGeneratingProviderMixin`
- Create helper method for building standard system/user message pairs

---

### 2. Hardcoded Gemini Initialization
**File:** `src/setup.py:64-73`

**Issue:** `initialize_providers` contains a hardcoded block for `gemini_webapi`, breaking the open/closed principle. Adding new "special" providers requires modifying this central function.

```python
# Gemini Web API (reverse-engineered) - special case due to different auth
gemini_cfg = config.providers.get("gemini_webapi")
if (gemini_cfg and gemini_cfg.enabled) or ENABLE_GEMINI:
    # ... specific loading logic ...
```

**Recommendation:**
- Refactor `PROVIDER_REGISTRY` to support custom initialization factories
- Allow `initializer_func` in provider spec instead of just `provider_class`
- Move Gemini auth logic into its own module or factory function

---

## Medium Priority

### 3. Brittle Question Loading
**File:** `src/questions.py`

**Issue:** `load_questions()` returns a tuple `(leetcode_questions, cs_questions, physics_questions)`:
- Adding a new subject requires changing return signature and all callers
- Hardcoded keys ("leetcode", "cs", "physics") in the function

**Recommendation:**
- Return `Dict[str, Dict[str, List[str]]]` instead of tuple
- System becomes data-driven: any top-level key in `questions.json` is treated as a subject

---

### 4. Anki Deck Generator Complexity
**File:** `src/anki/generator.py`

**Issue:** `DeckGenerator` handles both data traversal and card formatting:
- `_add_card_to_deck` uses conditionals to dispatch between `_add_mcq_card` and `_add_basic_card`
- Card formatting (HTML generation) mixed with Genanki object creation

**Recommendation:**
- Implement Strategy pattern for card creation
- Create `CardBuilder` interface with `StandardCardBuilder` and `MCQCardBuilder` implementations
- `DeckGenerator` selects builder based on mode and delegates note creation

---

## Low Priority

### 5. Scattered Path Management
**Files:** `src/questions.py`, `src/prompts.py`, `src/config/loader.py`

**Issue:** Path resolution logic duplicated across files:
- `src/questions.py` traverses parent directories to find `questions.json`
- `src/prompts.py` resolves the prompts directory independently

**Recommendation:**
- Create `src/paths.py` module with centralized path constants:
  - `PROJECT_ROOT`
  - `DATA_DIR`
  - `PROMPTS_DIR`
  - `CONFIG_DIR`

---

### 6. Legacy CLI Support
**File:** `main.py`

**Issue:** `normalize_legacy_args` maintains backward compatibility with old CLI syntax.

**Recommendation:**
- Consider deprecation warning for legacy syntax
- Remove in future major version to simplify `main.py`
