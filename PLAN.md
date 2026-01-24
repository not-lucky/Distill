# Priority 4: Cost Estimation & Budgeting - Implementation Plan

## Overview

Implement cost estimation and budgeting features for LLM2Deck to provide visibility into API costs before, during, and after generation runs.

## Features from IMPROVEMENT.md

1. **Pre-run cost estimation** based on question count and provider token rates
2. **`--budget <amount>` flag** to stop generation when budget exceeded
3. **Post-run cost summary** per provider (already partially implemented in progress.py)
4. **Track cumulative costs in database** across runs

## Design Decisions

### Token Estimation Model

Since we can't know exact token counts before running, we'll use historical averages:
- Default estimate: ~2000 input tokens + ~1500 output tokens per question per provider
- Configurable via `config.yaml` under `cost_estimation` section
- Can be refined based on historical data in database

### Budget Enforcement

- Budget is a soft limit - we check before starting each question
- If estimated remaining cost would exceed budget, stop gracefully
- Already-processed questions are saved; can resume later

### Cost Tracking Schema

Add new fields to the `Run` model and create a new `RunCost` table:
- `total_input_tokens` - sum across all providers
- `total_output_tokens` - sum across all providers  
- `total_estimated_cost_usd` - calculated cost

## Implementation Plan

### Phase 1: Cost Estimation Service (`src/services/cost.py`)

Create a dedicated service for cost calculations:

```python
class CostEstimator:
    """Estimates API costs based on provider pricing and token estimates."""
    
    def estimate_run_cost(providers, question_count) -> CostEstimate
    def calculate_actual_cost(provider_name, model, input_tokens, output_tokens) -> float
    def get_provider_pricing(provider_name) -> tuple[float, float]
```

Move `TOKEN_PRICING` from `progress.py` to this service and extend it.

### Phase 2: Database Schema Changes

Add columns to `Run` table:
- `total_input_tokens: int` 
- `total_output_tokens: int`
- `total_estimated_cost_usd: float`
- `budget_limit_usd: float` (if budget was set)
- `budget_exceeded: bool` (if stopped due to budget)

### Phase 3: CLI Changes

Add to `generate` command:
- `--budget <amount>` - Stop when cost exceeds this amount (USD)
- `--estimate-only` - Show cost estimate without generating

Update existing commands:
- `query stats` - Include cost summaries
- `query run <id>` - Show cost breakdown

### Phase 4: Orchestrator Integration

1. Before generation:
   - Calculate and display cost estimate
   - If `--estimate-only`, exit after showing estimate
   
2. During generation:
   - Track running costs via existing token callbacks
   - Check budget before each question
   - Stop gracefully if budget exceeded

3. After generation:
   - Save final costs to database
   - Display cost summary (enhanced version of current)

### Phase 5: Query Enhancements

Add `query costs` subcommand:
- Show cumulative costs across runs
- Filter by date range, subject
- Group by provider for cost analysis

## File Changes

### New Files
- `src/services/cost.py` - CostEstimator service
- `tests/unit/services/test_cost.py` - Unit tests

### Modified Files
- `src/database.py` - Add cost columns to Run model
- `src/repositories.py` - Add cost tracking methods
- `src/cli.py` - Add --budget, --estimate-only flags
- `src/orchestrator.py` - Integrate cost estimation and budget checking
- `src/progress.py` - Move TOKEN_PRICING to cost service, import from there
- `src/services/query.py` - Add cost queries
- `src/queries.py` - Add cost query functions

### Test Files
- `tests/unit/services/test_cost.py` - CostEstimator tests
- `tests/unit/test_orchestrator_budget.py` - Budget enforcement tests
- `tests/integration/test_cost_tracking.py` - End-to-end cost tracking

## API Changes

### CostEstimate Dataclass
```python
@dataclass
class CostEstimate:
    """Estimated cost for a generation run."""
    total_questions: int
    providers: List[ProviderCostEstimate]
    total_estimated_cost_usd: float
    estimated_input_tokens: int
    estimated_output_tokens: int
    confidence: str  # "low", "medium", "high" based on historical data
```

### ProviderCostEstimate Dataclass
```python
@dataclass  
class ProviderCostEstimate:
    """Per-provider cost estimate."""
    provider_name: str
    model: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    input_price_per_million: float
    output_price_per_million: float
    estimated_cost_usd: float
```

## Testing Strategy

1. **Unit Tests** (fast, isolated):
   - CostEstimator calculations
   - Budget checking logic
   - Database cost field updates

2. **Integration Tests**:
   - Cost tracking through full generation flow
   - Budget enforcement stopping generation
   - Query service cost summaries

3. **Mock Strategy**:
   - Use MockLLMProvider with configurable token counts
   - No real API calls in tests

## Rollout

1. Implement CostEstimator service with tests
2. Add database schema changes
3. Add CLI flags and pre-run estimation
4. Add budget enforcement
5. Add post-run cost tracking
6. Add query enhancements
7. Update documentation
