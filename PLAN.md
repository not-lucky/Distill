# Database Query Feature Implementation Plan

## Overview

Implement a comprehensive CLI-based database querying system for LLM2Deck. This allows users to query runs, problems, provider results, and cards directly from the command line.

## Goals

1. **CLI Command**: Add a `query` subcommand to the CLI with various sub-subcommands ✅
2. **Rich Output**: Support multiple output formats (table, JSON, simple text) ✅
3. **Flexible Filtering**: Allow filtering by date, status, subject, provider, etc. ✅
4. **Statistics**: Provide aggregate statistics and insights ✅

## Architecture

```
src/
├── cli.py              # Added 'query' subcommand with sub-subcommands
├── queries.py          # Enhanced with pagination and new query functions
└── services/
    └── query.py        # NEW: QueryService for CLI presentation
```

## CLI Command Structure

```bash
# List runs
uv run main.py query runs [--status STATUS] [--subject SUBJECT] [--limit N] [--format json|table]

# Show run details with statistics
uv run main.py query run <run_id> [--format json|table]

# List problems
uv run main.py query problems [--run RUN_ID] [--status STATUS] [--search QUERY] [--limit N]

# Show provider results
uv run main.py query providers [--run RUN_ID] [--provider NAME] [--success/--failed] [--limit N]

# List/search cards
uv run main.py query cards [--run RUN_ID] [--type TYPE] [--search QUERY] [--limit N]

# Show summary statistics
uv run main.py query stats [--subject SUBJECT]
```

## Implementation Steps

### Phase 1: Core Query Enhancements ✅
- Enhanced `src/queries.py` with pagination and more filtering options
- Added `get_runs_summary()`, `get_provider_statistics()`, `get_global_statistics()`
- Added `get_problems()`, `get_provider_results()`, `get_cards()` with flexible filters
- Added `get_run_by_id()` with partial ID matching

### Phase 2: Query Service Layer ✅
- Created `src/services/query.py` with formatting logic
- Implemented `QueryService` class with methods for each query type
- Added table and JSON output formats
- Added helper functions for date formatting and text truncation

### Phase 3: CLI Integration ✅
- Added `query` subcommand with all sub-subcommands
- Implemented argument parsing for all options
- Added `--format` and `--limit` options

### Phase 4: Testing ✅
- Created `tests/unit/test_query_service.py` with 30 tests
- Created `tests/integration/test_query_cli.py` with 22 tests
- All 1477 tests passing

### Phase 5: Documentation ✅
- Updated README.md with query command documentation
- Updated AGENTS.md with query-related patterns

## Output Formats

### Table Format (default)
```
ID (short) | Subject  | Type     | Status    | Created          | Problems | Cards
-----------+----------+----------+-----------+------------------+----------+------
abc12345   | leetcode | standard | completed | 2026-01-14 12:30 | 10/10    | 245
def67890   | cs       | mcq      | completed | 2026-01-14 10:15 | 20/20    | 180
```

### JSON Format
```json
{
  "runs": [
    {
      "id": "abc12345-6789-0000-0000-000000000000",
      "subject": "leetcode",
      "status": "completed",
      "created_at": "2026-01-14T12:30:00Z",
      "card_count": 245
    }
  ]
}
```

## Files Modified/Created

### Created:
- `src/services/query.py` - QueryService with formatting logic
- `tests/unit/test_query_service.py` - Unit tests (30 tests)
- `tests/integration/test_query_cli.py` - Integration tests (22 tests)
- `PLAN.md` - This file
- `TODO.md` - Task tracking

### Modified:
- `src/queries.py` - Added pagination, new query functions
- `src/cli.py` - Added `query` command with subcommands
- `README.md` - Added query command documentation
- `AGENTS.md` - Added query patterns and service documentation

---

## Status: ✅ COMPLETE

Implemented on 2026-01-14. All phases complete with 52 new tests added.
