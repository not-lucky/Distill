# Refactoring Backlog

Prioritized list of refactoring opportunities for LLM2Deck.

---

## Priority 1: Critical ✅ COMPLETED

High-impact, foundational improvements that should be addressed first.

### 1. ✅ Standardize Logging
**Location:** `src/orchestrator.py`

Replaced `print()` statements with `logger` calls to unify output handling.

### 2. ✅ Refactor `CardGenerator.process_question`
**Location:** `src/generator.py`

Extracted helper methods from the 160-line function:
- `_save_provider_results()` - saves valid results to DB
- `_post_process_cards()` - strips spaces, adds metadata
- `_generate_initial_cards()` - parallel provider calls
- `_combine_results()` - combines provider outputs

### 3. ✅ Implement Repository Pattern for Database
**Location:** `src/repositories.py` (new), `src/generator.py`, `src/orchestrator.py`

Created `CardRepository` class to decouple database operations from business logic:
- `create_initial_problem()`
- `save_provider_result()`
- `update_problem_failed()`
- `save_final_result()`

---

## Priority 2: High ✅ COMPLETED

Code quality improvements that reduce duplication and improve maintainability.

### 4. ✅ Extract JSON Utilities
**Location:** `src/utils.py`

Extracted `strip_json_block()` function from `openai_compatible.py` to shared `utils.py`.

### 5. ✅ Centralize Model Constants
**Location:** `src/config/models.py` (new)

Created centralized model constants file with:
- `DEFAULT_MODELS` - default model for each provider
- `MODELS_WITH_REASONING_EFFORT` - models supporting reasoning_effort param
- `supports_reasoning_effort()` - helper function

Updated providers to use these constants.

### 6. ✅ Improve Type Annotations
**Location:** `src/types.py` (new), `src/generator.py`

Created `src/types.py` with TypedDict definitions:
- `CardData` - structure for Anki cards
- `MCQCardData` - structure for MCQ cards
- `CardResult` - return type for `process_question()`
- `ProviderResultData` - provider result structure

Updated `CardGenerator.process_question()` return type.

---

## Priority 3: Medium

Maintainability improvements for long-term code health.

### 7. Custom Exception Hierarchy
**Location:** `src/exceptions.py`

Add specific exceptions to replace `None` returns.

```python
class LLM2DeckError(Exception): ...
class GenerationError(LLM2DeckError): ...
class CombineError(LLM2DeckError): ...
class ProviderError(LLM2DeckError): ...
```

### 8. Extract Concurrency Logic
**Location:** `src/orchestrator.py:119-148`

`process_question_with_semaphore` closure mixes concurrency with business logic.

```python
# Proposed: src/task_runner.py
class TaskRunner:
    def __init__(self, max_concurrent: int): ...
    async def run_all(self, tasks: List[Callable]): ...
```

### 9. Move Business Logic from CLI
**Location:** `src/cli.py`

Mode detection from filenames belongs in domain layer, not CLI.

```python
# Move to src/utils.py or src/config/modes.py
def detect_mode_from_filename(filename: str) -> str: ...
```

---

## Priority 4: Low

Nice-to-have improvements for future iterations.

### 10. Declarative Subject Configuration
**Location:** `src/config/subjects.py`

Move subject definitions to YAML for easier editing.

```yaml
# subjects.yaml
leetcode:
  deck_prefix: "LeetCode"
  deck_prefix_mcq: "LeetCode MCQ"
  prompts:
    initial: "prompts/leetcode_initial.md"
    combine: "prompts/leetcode_combine.md"
```

### 11. Prompt Path Configuration
**Location:** `src/prompts.py`

Hardcoded paths should be configurable or use resource discovery.

### 12. Provider Result Validation
**Location:** Various

Add Pydantic models for raw LLM responses before database insertion.

```python
class ProviderResponse(BaseModel):
    cards: List[CardData]

    @validator('cards')
    def validate_cards(cls, v): ...
```

---

## Notes

- Items within each priority level are roughly ordered by impact
- P1 items block testability improvements
- P2 items prevent code duplication
- Consider tackling P1 items as a batch for maximum impact
