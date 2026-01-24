# TODO: Resume Failed Runs Implementation

## Phase 1: Repository Layer ✅
- [x] Add `get_successful_questions_for_run()` to `src/queries.py`
- [x] Add `load_existing_run()` to `RunRepository`
- [x] Add `get_processed_questions()` to `RunRepository`
- [x] Add `get_existing_results()` to `RunRepository`
- [x] Add `update_run_status()` to `RunRepository`
- [x] Add `set_run_id()` method to `RunRepository` for resume mode

## Phase 2: Orchestrator Changes ✅
- [x] Add `resume_run_id` parameter to `Orchestrator.__init__`
- [x] Add `initialize_for_resume()` method
- [x] Modify `initialize()` to handle resume mode
- [x] Add logic to filter out already-processed questions in `run()`
- [x] Merge existing results with new results in `save_results()`

## Phase 3: CLI Changes ✅
- [x] Add `--resume` argument to generate parser
- [x] Update `handle_generate()` to pass resume_run_id
- [x] Add validation for resume mode (run exists, valid status)
- [x] Add helpful error messages

## Phase 4: Testing ✅
- [x] Create `tests/unit/test_resume.py`
- [x] Test `load_existing_run()` returns correct run
- [x] Test `get_processed_questions()` returns correct set
- [x] Test filtering removes already-processed questions
- [x] Test partial run ID matching
- [x] Test validation errors (wrong status, not found)
- [x] Create `tests/integration/test_resume_integration.py`
- [x] Test full resume workflow

## Phase 5: Documentation ✅
- [x] Update README.md with resume examples
- [x] Update AGENTS.md with resume command

## Verification ✅
- [x] Run all tests: `uv run pytest tests/unit/test_resume.py -v`
- [x] Run integration tests: `uv run pytest tests/integration/test_resume_integration.py -v`
- [x] Check types: `ty check src/`
