You are an expert coding tutor.

**Problem**: {question}

I have multiple sets of Anki cards generated for this problem. Your job is to merge them into one cohesive, high-quality deck.

## Merging Philosophy

**Target: Up to 35 final cards**. Preserve diversity of approaches while removing true duplicates. A comprehensive deck should maintain 3-4 different approaches with 6-7 cards each, plus foundation and implementation cards.

## Merging Strategy

### 1. Preserve Approach Diversity
- **CRITICAL**: Keep cards for ALL genuinely different approaches (Brute Force, DP, Two Pointer, Hash Map, etc.)
- Each approach should have ~6-7 cards: overview+intuition+algorithm, example walkthrough, code, complexity, trade-offs, pitfalls, optimizations
- Remove duplicate cards only WITHIN the same approach
- Do NOT remove approaches just because they're suboptimal - brute force and intermediate solutions are required

### 2. What is "Redundant"?
- **Redundant**: Two cards explaining the same concept within the same approach
- **NOT Redundant**: Cards for different approaches (keep ALL approaches)
- **NOT Redundant**: Example walkthroughs - each approach needs its own
- **NOT Redundant**: Different pitfalls/optimizations specific to different approaches

### 3. Quality Over Quantity Within Each Approach
For EACH approach being kept (typically 3-4 approaches):
- Merge the best overview+intuition+algorithm card
- Keep the best example walkthrough for that approach
- Keep the cleanest code implementation
- Keep complexity analysis and trade-off discussion
- Merge pitfalls and optimization cards within that approach

### 4. Quality Standards
Ensure the final deck has:
- Clear progression: Problem understanding → Core approaches → Implementation details
- Each card teaches ONE specific concept
- Front (question) is short and focused
- Back (answer) is detailed and includes code where relevant

### 5. Consolidation Template (Target: up to 35 cards)
```
Problem Foundation (3-4 cards)
├── Problem statement + constraints
├── Key edge cases
└── Approach comparison (optional)

Approach 1: Brute Force (6-7 cards)
├── Overview + Intuition + Algorithm
├── Example walkthrough for brute force
├── Code implementation
├── Complexity analysis
├── When to use / Trade-offs
├── Common pitfalls
└── Optimizations (optional)

Approach 2: [Optimal/Alternative] (6-7 cards)
├── Overview + Intuition + Algorithm
├── Example walkthrough for this approach
├── Code implementation
├── Complexity analysis
├── When to use / Trade-offs
├── Common pitfalls
└── Optimizations (optional)

Approach 3: [Alternative] (6-7 cards, if applicable)
├── [same structure as Approach 2]

General Implementation (2-3 cards)
├── Testing strategy
└── Common bugs across approaches
```

## Output Requirements

- **Format**: Valid JSON matching the schema
- **Duplicate handling**: Merge identical concepts into single cards
- **Code quality**: Ensure all code examples are correct and well-commented
- **Unique cards**: Each card should teach something distinct

**CRITICAL FORMATTING RULES**:
1. **NO SPACES** in `card_type`. Use `PascalCase` (e.g., `TwoPointerIntuition`)
2. **NO SPACES** in `tags`. Use `PascalCase` (e.g., `TwoPointer`, `Intuition`)
3. Content should be **concise**: Front/Back should be scannable in 30-60 seconds

Output MUST be valid JSON matching the schema.
