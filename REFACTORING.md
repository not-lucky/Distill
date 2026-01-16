# LLM2Deck Refactoring Priorities

## P0 - Critical (Bugs & Dead Code)

- [ ] **Dead/unreachable code** - `src/generator.py:209-248`
  - Lines 209-248 are exact duplicates of lines 134-207, completely unreachable after `return` on line 196/207
  - **Fix**: Delete lines 209-248

- [ ] **Undefined function call** - `src/generator.py:243`
  - Calls `save_archival()` which doesn't exist anywhere in the codebase
  - **Fix**: Part of dead code removal above

- [ ] **OpenRouter provider always returns None** - `src/providers/openrouter.py:56-57`
  - Missing `return` statement in `_make_request` method
  - **Fix**: Add `return response_content` after the content check

- [ ] **Bare `except:` clause** - `src/generator.py:105`
  - Catches all exceptions silently, hides bugs
  - **Fix**: Use `except json.JSONDecodeError:`

## P1 - High (Code Duplication)

- [ ] **6 nearly identical key loading functions** - `src/setup.py:22-144`
  - `load_cerebras_keys`, `load_openrouter_keys`, `load_nvidia_keys`, `load_canopywave_keys`, `load_baseten_keys`, `load_google_genai_keys`
  - Only difference is JSON key path extraction
  - **Fix**: Create single generic function:
    ```python
    async def load_api_keys(file_path: Path, extractor: Callable) -> List[str]
    ```

- [ ] **Duplicated retry logic in all providers** - `src/providers/*.py`
  - Every provider implements its own `_make_request` with retry logic
  - Inconsistent retry counts: Cerebras (7), Nvidia (5), Canopywave (5), Baseten (3), OpenRouter (3), G4F (3)
  - **Fix**: Move to base class with configurable `max_retries`, `retry_delay`

- [ ] **Duplicated `generate_initial_cards` / `combine_cards` methods** - `src/providers/*.py`
  - Nearly identical implementation across all providers (except Gemini)
  - Same template application and JSON handling
  - **Fix**: Use template method pattern in base class, providers only override `_call_api()`

## P2 - Medium (Architecture)

- [ ] **Confusing model file names** - `src/models.py` vs `src/anki/models.py`
  - `src/models.py` contains Pydantic schemas for card data
  - `src/anki/models.py` contains Genanki note type definitions
  - **Fix**: Rename to `src/card_schemas.py` and `src/anki/note_types.py`

- [ ] **Fragile database session management** - `src/generator.py`, `src/database.py`
  - Manual `get_session()` / `session.close()` calls throughout
  - `session_scope()` context manager exists in database.py but is never used
  - **Fix**: Replace all manual session handling with `with session_scope() as session:`

- [ ] **Massive commented-out code blocks** - `src/setup.py:178-274`
  - ~100 lines of commented provider configurations mixed with active code
  - Hard to read, unclear which providers are actually active
  - **Fix**: Remove comments, use config file or environment variables for provider selection

- [ ] **Magic numbers scattered across providers** - All provider files
  - `max_retries`: 3, 5, 7 with no consistency
  - `temperature`: 0.4, 0.7 hardcoded
  - Sleep durations: 1, 2 seconds
  - **Fix**: Create `ProviderConfig` dataclass with sensible defaults

## P3 - Low (Code Quality)

- [ ] **Split logging utilities** - `src/logging_config.py`, `src/logging_utils.py`
  - Two separate files for related logging functionality
  - **Fix**: Merge into single `src/logging.py` module

- [ ] **Empty tests directory** - `tests/`
  - No tests exist
  - **Fix**: Add at least smoke tests for core functionality

- [ ] **Inconsistent type hints** - Throughout codebase
  - `run_id: str = None` should be `run_id: Optional[str] = None`
  - Some functions have hints, others don't
  - **Fix**: Run `mypy` and fix all type errors

- [ ] **Unused import** - `src/generator.py:22`
  - `console` is imported from `src/logging_utils` but never used
  - **Fix**: Remove the import

- [ ] **Hardcoded localhost URL** - `src/providers/google_antigravity.py:17`
  - `"http://127.0.0.1:8317/v1"` hardcoded
  - **Fix**: Move to environment variable or config

- [ ] **Broad exception in database** - `src/database.py:195`
  - `except Exception:` without specific error handling
  - **Fix**: Use specific exception types or re-raise

- [ ] **Test file in root** - `g4f_test.py`
  - Test file in project root instead of `tests/` directory
  - **Fix**: Move to `tests/test_g4f.py`

---

## Validation Commands

```bash
# Check Python syntax
uv run python -m py_compile src/generator.py

# Run linter (if available)
uv run ruff check src/

# Type checking (if configured)
uv run mypy src/
```

## Suggested Refactoring Order

1. **P0 first** - Fix bugs and remove dead code (quick wins, prevents issues)
2. **P1 key loaders** - Reduces setup.py from ~150 lines to ~50
3. **P1 provider base** - Biggest impact, eliminates most duplication
4. **P2 as needed** - Address during feature work
5. **P3 ongoing** - Fix incrementally
