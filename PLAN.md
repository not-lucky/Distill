# Implementation Plan: Resume Failed Runs (Priority 2)

## Overview

Implement the ability to resume a failed or interrupted run, skipping already-processed questions and merging partial results with resumed results.

## Requirements from IMPROVEMENT.md

1. Add `--resume <run_id>` flag to continue from last successful question
2. Store question processing status in database (already exists via `Problem.status`)
3. Skip already-processed questions on resume
4. Merge partial results with resumed results

## Current Architecture Analysis

### Database Schema (Already Supports Resume)

- `Run.status`: "running", "completed", "failed" ✅
- `Problem.status`: "running", "success", "failed", "partial" ✅
- `Problem.question_name`: Stores the question identifier ✅
- `Problem.final_result`: JSON blob with card data ✅

### Key Components to Modify

1. **CLI (`src/cli.py`)**: Add `--resume <run_id>` argument
2. **Orchestrator (`src/orchestrator.py`)**: Add resume logic
3. **RunRepository (`src/repositories.py`)**: Add methods to fetch existing run data
4. **Queries (`src/queries.py`)**: May need new query methods

## Implementation Design

### Phase 1: Database/Repository Layer

Add new methods to `RunRepository`:
- `load_existing_run(run_id: str)`: Load a run by ID for resumption
- `get_processed_questions(run_id: str)`: Get set of successfully processed question names
- `get_existing_results(run_id: str)`: Get already-generated card data

Add new query function to `queries.py`:
- `get_successful_problems_for_run(run_id: str)`: Get questions that completed successfully

### Phase 2: Orchestrator Changes

New flow for resume mode:
1. Load existing run metadata (validate subject, mode match)
2. Update run status back to "running"
3. Get set of already-processed questions
4. Filter out processed questions from the generation list
5. Run generation on remaining questions
6. Collect existing results from database + new results
7. Update run status to "completed" with merged stats

### Phase 3: CLI Changes

Add to generate parser:
- `--resume <run_id>`: Run ID to resume (can be partial, uses prefix match)

Handle validation:
- Run must exist
- Run must be "failed" or "running" (not "completed")
- Subject/mode must match current arguments (or infer from run)

### Phase 4: Result Merging

When saving results:
- Load existing successful problem results from database
- Combine with newly generated results
- Save to new JSON file with updated timestamp
- Update run statistics to reflect total

## Files to Create/Modify

### New Files
- `tests/unit/test_resume.py` - Unit tests for resume functionality
- `tests/integration/test_resume_integration.py` - Integration tests

### Modified Files
- `src/cli.py` - Add `--resume` argument
- `src/orchestrator.py` - Add resume mode logic
- `src/repositories.py` - Add resume-related repository methods
- `src/queries.py` - Add query for successful problems
- `README.md` - Document resume feature
- `AGENTS.md` - Update with resume command examples

## Test Plan

### Unit Tests
- Test `RunRepository.load_existing_run()` returns correct run
- Test `RunRepository.get_processed_questions()` returns correct set
- Test filtering logic removes already-processed questions
- Test partial run ID matching
- Test validation: wrong subject, wrong mode, completed run

### Integration Tests
- Test full resume workflow: create run, process some, fail, resume, complete
- Test results merging produces correct final output
- Test stats are correctly updated

### E2E Tests
- Test CLI `--resume` flag parses correctly
- Test resume with dry-run mode
- Test error messages for invalid run IDs

## Risks and Mitigations

1. **Run ID ambiguity**: Use prefix matching like existing `query run` command
2. **Subject mismatch**: Validate and error early with clear message
3. **Concurrent resumes**: Status check prevents double-resuming
4. **Database integrity**: Use transactions for status updates

## Implementation Order

1. Repository layer changes (foundation)
2. Orchestrator changes (core logic)
3. CLI changes (user interface)
4. Unit tests
5. Integration tests
6. Documentation updates
