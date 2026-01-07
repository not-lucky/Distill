# LeetCode Prompt Improvements

## Problem Identified

The existing LeetCode card generation was producing:
- Too many unnecessary alternate solutions (40-50+ cards)
- Excessive variations of the same approach
- Shallow coverage of approaches (breadth over depth)
- Cards that didn't add learning value
- Overly lengthy, non-scannable content

## Solution Implemented

Created **two new LeetCode-specific prompts** to replace the generic ones:

### 1. `initial_leetcode.md` - Initial Card Generation
**Location:** `src/data/prompts/initial_leetcode.md`

**Key Changes:**
- **Reduced target**: 15-25 cards instead of 25-40
- **Focus on depth**: For each approach, deep-dive into intuition, algorithm, code, complexity
- **Smart filtering**: Only include 2-3 most relevant approaches (not "ALL possible variations")
- **Quality gates**: Removes obscure/academic approaches that don't add learning value
- **Better structure**: 
  - Problem Foundation (3-4 cards)
  - Common Approaches (2-3 approaches × 5-6 cards each)
  - Implementation Mastery (2-3 cards)
  - Problem Context (1-2 cards optional)

**Filtering Rules Added:**
```markdown
Do NOT include approaches that are:
- Nearly identical to another approach already included
- Overly obscure or academic
- Less efficient without learning value
```

### 2. `combine_leetcode.md` - Combining Multiple Sets
**Location:** `src/data/prompts/combine_leetcode.md`

**Key Changes:**
- **Target 15-25 final cards** (not 40-50+)
- **Remove duplicates aggressively**: One "Problem Understanding" card, not three
- **Consolidate approaches**: Merge DP variants into single approach
- **Quality over quantity**: Keep well-explained cards, remove verbose ones
- **Clear grouping**: Shows exactly how to organize final deck
- **Explicit rules**: What cards to keep vs what to remove

**Consolidation Rules:**
```
Problem Understanding (1-2 cards)
Approach 1 (4-5 cards)
Approach 2 (4-5 cards)
Approach 3 (4-5 cards) [optional]
Implementation (2-3 cards)
Context (1 card optional)
```

### 3. Code Changes Made

**File:** `src/prompts.py`
- Added `INITIAL_LEETCODE_PROMPT_TEMPLATE`
- Added `COMBINE_LEETCODE_PROMPT_TEMPLATE`

**File:** `src/config/subjects.py`
- LeetCode mode now uses `INITIAL_LEETCODE_PROMPT_TEMPLATE` (was `None` before)
- Imported new LeetCode combining prompt

**File:** `src/generator.py`
- Card combiner now selects `COMBINE_LEETCODE_PROMPT_TEMPLATE` when mode is "leetcode"
- MCQ modes still use original MCQ combining prompt

## How It Works

### Generation Flow

```
User runs: uv run main.py leetcode
                    ↓
SubjectRegistry.get_config("leetcode", is_multiple_choice=False)
                    ↓
Selects INITIAL_LEETCODE_PROMPT_TEMPLATE
                    ↓
Providers generate initial card sets (with new prompt)
                    ↓
Each provider creates 15-25 cards with:
  - Problem understanding
  - 2-3 focused approaches (not 5+)
  - Deep dive per approach
  - Implementation tips
```

### Combining Flow

```
Multiple provider sets generated
                    ↓
CardGenerator.combine_cards()
                    ↓
Uses COMBINE_LEETCODE_PROMPT_TEMPLATE
                    ↓
LLM merges sets:
  - Removes duplicate approaches
  - Keeps only best explanation per approach
  - Consolidates to 15-25 total
  - Follows consolidation structure
                    ↓
Final deck: Focused, deep, scannable
```

## What You Get

### Before (Old Prompts)
- 40-50 cards per problem
- 5-7 different solution approaches included
- Shallow coverage ("here's code for approach X")
- Redundant variations of DP (top-down + bottom-up as separate approaches)
- Cards that repeat information across approaches

### After (New Prompts)
- 15-25 cards per problem ✓
- 2-3 most relevant approaches ✓
- Deep understanding ("why this works, how to implement, when to use") ✓
- Consolidated approaches (DP covered once, deeply) ✓
- Unique value in each card ✓

## Usage

No changes needed in how you run commands:

```bash
# Same command, better output
uv run main.py leetcode

# New cards will be:
# - Fewer in quantity (15-25 vs 40-50)
# - Greater in depth (detailed approach explanations)
# - Higher in quality (no fluff, no redundant variations)
```

## Customization

If you want to adjust the generation strategy, edit:

- **More/fewer approaches**: Edit `initial_leetcode.md` → "Approaches to Consider" section
- **Different card count**: Edit `initial_leetcode.md` → "Generate **X-Y** cards"
- **Different consolidation**: Edit `combine_leetcode.md` → "Card count" section

## Testing

Generate a few LeetCode problems to see the improvements:

```bash
uv run main.py leetcode
```

Compare the JSON output:
- Check `card_type` distribution (should be smaller variety)
- Check `tags` for duplicate approach variations (should be minimal)
- Read card content (should feel more substantial)

## Backward Compatibility

- Old generic prompts (`initial.md`, `combine.md`) still exist
- CS and Physics modes unaffected
- MCQ modes unaffected
- Can easily switch back if needed

---

**Summary**: LeetCode generation now produces focused, deep cards instead of comprehensive but shallow ones. Quality over quantity.
