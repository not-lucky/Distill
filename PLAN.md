# PLAN.md - Selective Question Generation (Priority 3) ✅ COMPLETED

## Overview

Implement selective question generation allowing users to filter which questions are processed.

**Features to implement:**
1. `--category "Arrays"` - Generate only specific categories
2. `--question "Two Sum"` - Single question generation
3. `--limit N` - Generate first N questions (for testing)
4. `--skip-until "Binary Search"` - Skip questions until reaching a specific one

## Architecture Analysis

### Current Flow
1. `cli.py` parses args → creates `Orchestrator`
2. `Orchestrator.run()` calls `get_indexed_questions()` to get all questions
3. Questions are filtered for resume mode (`_processed_questions`)
4. Questions are processed in parallel via `ConcurrentTaskRunner`

### Key Files to Modify
- `src/cli.py` - Add new CLI arguments to generate subparser
- `src/orchestrator.py` - Accept filter parameters and apply them
- `src/questions.py` - Add filtering functions

### Key Files for Tests
- `tests/unit/test_cli.py` - Test CLI argument parsing
- `tests/unit/test_questions.py` - Test filtering functions
- `tests/unit/test_orchestrator.py` - Test filter integration

## Implementation Details

### 1. CLI Arguments (`src/cli.py`)

Add to `generate_parser`:
```python
generate_parser.add_argument(
    "--category",
    type=str,
    default=None,
    help="Only generate cards for specific category (e.g., 'Arrays and Hashing')",
)
generate_parser.add_argument(
    "--question",
    type=str,
    default=None,
    help="Generate cards for a single question by name",
)
generate_parser.add_argument(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of questions to process (for testing)",
)
generate_parser.add_argument(
    "--skip-until",
    type=str,
    default=None,
    metavar="QUESTION",
    help="Skip questions until reaching the specified question name",
)
```

### 2. Question Filtering (`src/questions.py`)

Add new functions:
```python
@dataclass
class QuestionFilter:
    """Configuration for filtering questions."""
    category: Optional[str] = None
    question_name: Optional[str] = None
    limit: Optional[int] = None
    skip_until: Optional[str] = None

def filter_indexed_questions(
    questions: List[Tuple[int, str, int, str]],
    filter_config: QuestionFilter,
) -> List[Tuple[int, str, int, str]]:
    """Apply filters to indexed questions."""
    # Implementation
```

### 3. Orchestrator Integration (`src/orchestrator.py`)

Modify `__init__` to accept `QuestionFilter`:
```python
def __init__(
    self,
    subject_config: SubjectConfig,
    is_mcq: bool = False,
    run_label: Optional[str] = None,
    dry_run: bool = False,
    bypass_cache_lookup: bool = False,
    resume_run_id: Optional[str] = None,
    question_filter: Optional[QuestionFilter] = None,  # NEW
):
```

Apply filter in `run()`:
```python
all_questions_with_metadata = get_indexed_questions(
    self.subject_config.target_questions
)
if self.question_filter:
    all_questions_with_metadata = filter_indexed_questions(
        all_questions_with_metadata, self.question_filter
    )
```

### 4. Handler Update (`src/cli.py`)

Update `handle_generate`:
```python
from src.questions import QuestionFilter

question_filter = QuestionFilter(
    category=getattr(args, "category", None),
    question_name=getattr(args, "question", None),
    limit=getattr(args, "limit", None),
    skip_until=getattr(args, "skip_until", None),
)

orchestrator = Orchestrator(
    ...
    question_filter=question_filter if question_filter.has_filters() else None,
)
```

## Filter Behavior

### `--category "Arrays"`
- Case-insensitive partial match on category names
- Example: `--category "arrays"` matches "Arrays and Hashing"

### `--question "Two Sum"`
- Case-insensitive partial match on question names
- Returns only matching questions
- Example: `--question "sum"` matches "Two Sum", "3Sum", etc.

### `--limit N`
- Applied after other filters
- Takes first N questions from the filtered set

### `--skip-until "Binary Search"`
- Skips all questions until finding a match (inclusive)
- Case-insensitive partial match
- Useful for resuming from a specific point without using `--resume`

### Combination
Filters are applied in this order:
1. `--category` (filter by category)
2. `--question` (filter by question name)
3. `--skip-until` (skip until question)
4. `--limit` (take first N)

## Test Plan

### Unit Tests for `questions.py`
- Test `filter_indexed_questions` with each filter type
- Test filter combinations
- Test case-insensitive matching
- Test partial matching
- Test empty results handling
- Test `--skip-until` with non-existent question

### Unit Tests for `cli.py`
- Test parsing of new arguments
- Test argument validation
- Test help text includes new options

### Unit Tests for `orchestrator.py`
- Test filter passed to orchestrator
- Test filter applied before resume filter
- Test dry-run mode shows filtered count

### Integration Tests
- Test full flow with `--limit 1`
- Test `--category` with real question data

## Error Handling

- `--category` with no match: Warning, continue with 0 questions
- `--question` with no match: Warning, continue with 0 questions
- `--skip-until` with no match: Error, abort with clear message
- `--limit 0` or negative: Error, must be positive integer

## Documentation Updates

- Update AGENTS.md with new CLI options
- Update README.md with usage examples
- Add to IMPROVEMENT.md checklist

## Files Changed Summary

| File | Change Type |
|------|-------------|
| `src/cli.py` | Add CLI arguments + update handler |
| `src/questions.py` | Add `QuestionFilter` class and filter function |
| `src/orchestrator.py` | Accept and apply `QuestionFilter` |
| `tests/unit/test_cli.py` | Add tests for new arguments |
| `tests/unit/test_questions.py` | Add tests for filtering |
| `tests/unit/test_orchestrator.py` | Add tests for filter integration |
| `AGENTS.md` | Document new options |
| `README.md` | Usage examples |
