# PLAN.md - Priority 1: Progress Visualization

## Goal
Implement rich progress visualization for the card generation workflow to provide real-time feedback during large generation runs (100+ questions).

## Requirements from IMPROVEMENT.md
- [x] Add rich progress bar with `rich` library showing per-question status
- [x] Real-time provider status indicators (✓ success, ⏳ pending, ✗ failed)
- [x] ETA estimation based on completed questions
- [x] Live token usage/cost tracking per provider

## Implementation Status: ✅ COMPLETE

### Files Changed

#### 1. `src/progress.py` (NEW)
- `ProgressTracker` class with methods:
  - `start()` / `stop()` - lifecycle management
  - `start_question()` / `complete_question()` - question tracking
  - `update_provider_status()` - provider status with token/cost tracking
  - `_calculate_eta()` - rolling average ETA estimation
  - `get_summary()` / `print_summary()` - final statistics
- `ProviderStats` dataclass for per-provider statistics
- `ProviderStatus` enum for status indicators
- `TOKEN_PRICING` dictionary for cost estimation

#### 2. `src/task_runner.py`
- Added `TaskInfo` dataclass for task metadata
- Added `on_task_start` callback parameter
- Added `on_task_complete` callback parameter
- Added `task_names` parameter to `run_all()` and `run_all_ordered()`

#### 3. `src/providers/base.py`
- Added `TokenUsage` dataclass for tracking input/output tokens
- Added `TokenUsageCallback` type alias for callback

#### 4. `src/providers/openai_compatible.py`
- Added `on_token_usage` callback parameter
- Extract token usage from API response (`completion.usage`)
- Call callback on success/failure with token data

#### 5. `src/orchestrator.py`
- Integrated `ProgressTracker` into generation workflow
- Wire up token usage callbacks to all providers
- Wire up task start/complete callbacks to task runner
- Display progress during generation, summary after completion

## Token Pricing (USD per 1M tokens)
Configured in `src/progress.py`:
- Cerebras: $0.60 input, $0.60 output
- NVIDIA NIM: $0.50 input, $0.50 output (varies by model)
- OpenRouter: $0.50 input, $0.50 output (varies by model)
- Google GenAI: $0.10 input, $0.40 output (Gemini 2.0 Flash)
- Google Antigravity: Free (local proxy)

## Tests
Added `tests/unit/test_progress.py` with 31 tests covering:
- `ProviderStatus` enum values
- `ProviderStats` defaults, icons, styles
- `TOKEN_PRICING` configuration
- `ProgressTracker` initialization, start/stop, question tracking
- Provider status updates and cost calculation
- ETA calculation with rolling average
- Summary generation
- Edge cases (zero questions, unicode, long names, etc.)

## Usage
The progress visualization automatically activates when running:
```bash
uv run main.py generate leetcode
```

The display shows:
- Progress bar with question count and elapsed time
- Current question being processed
- Provider status table with success/fail counts, tokens, cost
- ETA estimation and totals

---
*Created: 2026-01-14*
*Completed: 2026-01-14*
