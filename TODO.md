# Priority 4: Cost Estimation & Budgeting - Implementation Checklist

## Phase 1: Cost Estimation Service ✅

- [x] Create `src/services/cost.py` with CostEstimator class
- [x] Define CostEstimate and ProviderCostEstimate dataclasses
- [x] Move TOKEN_PRICING from progress.py to cost service
- [x] Implement `estimate_run_cost()` method
- [x] Implement `calculate_actual_cost()` method
- [x] Update progress.py to import TOKEN_PRICING from cost service
- [x] Create `tests/unit/services/test_cost.py`

## Phase 2: Database Schema Changes ✅

- [x] Add cost columns to Run model in `src/database.py`:
  - [x] `total_input_tokens` (Integer)
  - [x] `total_output_tokens` (Integer)
  - [x] `total_estimated_cost_usd` (Float)
  - [x] `budget_limit_usd` (Float, nullable)
  - [x] `budget_exceeded` (Boolean)
- [x] Add cost tracking methods to repositories.py
- [x] Create tests for database changes

## Phase 3: CLI Changes ✅

- [x] Add `--budget <amount>` flag to generate command
- [x] Add `--estimate-only` flag to generate command
- [x] Display cost estimate before generation starts
- [x] Create tests for CLI argument parsing

## Phase 4: Orchestrator Integration ✅

- [x] Integrate CostEstimator into Orchestrator
- [x] Show pre-run cost estimate
- [x] Implement budget checking before each question
- [x] Stop generation gracefully when budget exceeded
- [x] Track running costs during generation
- [x] Save final costs to database on completion
- [x] Update progress summary to show actual vs estimated
- [x] Create tests for budget enforcement

## Phase 5: Query Enhancements ✅

- [x] Add cost fields to `query run` output
- [x] Add cumulative cost to `query stats` output
- [x] Create tests for query enhancements

## Phase 6: Documentation ✅

- [x] Update README.md with cost estimation features
- [x] Update AGENTS.md with new CLI options
- [x] Add examples for budget usage

## Final Verification

- [x] All tests pass
- [x] Type checking passes (ty check src/)
- [x] Documentation complete
