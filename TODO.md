# TODO.md - Selective Question Generation Implementation Checklist

## Phase 1: Core Implementation ✅ COMPLETED

### Questions Module (`src/questions.py`)
- [x] Add `QuestionFilter` dataclass
- [x] Add `filter_indexed_questions()` function
- [x] Handle category filtering (case-insensitive partial match)
- [x] Handle question name filtering (case-insensitive partial match)
- [x] Handle skip-until filtering
- [x] Handle limit filtering
- [x] Add `has_filters()` method to `QuestionFilter`

### CLI (`src/cli.py`)
- [x] Add `--category` argument
- [x] Add `--question` argument
- [x] Add `--limit` argument to generate
- [x] Add `--skip-until` argument
- [x] Update `handle_generate()` to create `QuestionFilter`
- [x] Pass filter to `Orchestrator`

### Orchestrator (`src/orchestrator.py`)
- [x] Add `question_filter` parameter to `__init__`
- [x] Apply filter in `run()` before resume filter
- [x] Log filter information in dry-run mode
- [x] Handle empty filtered questions gracefully

## Phase 2: Testing ✅ COMPLETED

### Unit Tests for Questions (`tests/unit/test_questions.py`)
- [x] Test `QuestionFilter` dataclass creation
- [x] Test `has_filters()` returns True when any filter set
- [x] Test `has_filters()` returns False when no filters
- [x] Test category filter - exact match
- [x] Test category filter - partial match (case insensitive)
- [x] Test category filter - no match returns empty
- [x] Test question filter - exact match
- [x] Test question filter - partial match (case insensitive)
- [x] Test question filter - no match returns empty
- [x] Test skip-until - skips until match
- [x] Test skip-until - includes matched question
- [x] Test skip-until - no match returns empty
- [x] Test limit - returns first N questions
- [x] Test limit - returns all if limit > total
- [x] Test combined filters (category + limit)
- [x] Test combined filters (question + skip-until)
- [x] Test filter order (category → question → skip-until → limit)

### Unit Tests for CLI (`tests/unit/test_cli.py`)
- [x] Test `--category` argument parsing
- [x] Test `--question` argument parsing
- [x] Test `--limit` argument parsing (positive integer)
- [x] Test `--skip-until` argument parsing
- [x] Test all filter args together
- [x] Test help text includes filter options
- [x] Test filter passed to Orchestrator
- [x] Test no filter results in None

### Unit Tests for Orchestrator (`tests/unit/test_orchestrator.py`)
- [x] Test filter parameter accepted
- [x] Test filter applied to questions
- [x] Test dry-run logs filtered count
- [x] Test empty filter not applied
- [x] Test filter + no filter mode

## Phase 3: Documentation ✅ COMPLETED

### AGENTS.md
- [x] Add filter options to Quick Reference
- [x] Add usage examples
- [x] Document filter behavior and combination

### README.md
- [x] Add filter options to usage section
- [x] Add examples for common use cases

### IMPROVEMENT.md
- [x] Mark Priority 3 items as completed

## Completion Tracking

| Component | Status |
|-----------|--------|
| `src/questions.py` | ✅ Complete |
| `src/cli.py` | ✅ Complete |
| `src/orchestrator.py` | ✅ Complete |
| Unit Tests - questions | ✅ Complete (34 new tests) |
| Unit Tests - cli | ✅ Complete (8 new tests) |
| Unit Tests - orchestrator | ✅ Complete (6 new tests) |
| AGENTS.md | ✅ Complete |
| README.md | ✅ Complete |
| IMPROVEMENT.md | ✅ Complete |

## Summary

All items for Priority 3 (Selective Question Generation) have been implemented:

1. **QuestionFilter dataclass** - Holds filter configuration with category, question_name, limit, skip_until
2. **filter_indexed_questions()** - Applies filters in order: category → question → skip-until → limit
3. **CLI arguments** - `--category`, `--question`, `--limit`, `--skip-until`
4. **Orchestrator integration** - Applies filter before resume mode filtering
5. **48 new tests** - Comprehensive coverage of all filter functionality
6. **Documentation** - Updated AGENTS.md, README.md, and IMPROVEMENT.md
