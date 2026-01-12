You are an expert coding tutor.

**Problem**: {question}

I have multiple sets of Anki cards generated for this problem. Your job is to merge them into one cohesive, high-quality deck.

## Merging Philosophy

The final card count should reflect the problem's complexity. A straightforward problem may consolidate down to fewer cards; a problem with many valid approaches may retain more. Focus on eliminating true redundancy while preserving valuable different perspectives.

## Merging Strategy

### 1. Consolidate Approaches
- Keep cards for **genuinely different approaches**
- REMOVE duplicate approaches (e.g., don't keep both "recursive DP" and "top-down DP" if they're teaching the same thing)
- For each kept approach, merge the best cards from all sets

### 2. Quality Over Quantity
Focus on **understanding** rather than arbitrary coverage:
- Keep detailed algorithm cards from best set
- Keep well-explained code examples
- Keep intuition/insight cards (the "aha" moments)
- REMOVE overly verbose or redundant cards

### 3. Remove Duplicates Smartly
- If multiple sets have "Problem Understanding" cards, keep the clearest ONE
- If multiple sets have code for same approach, keep the cleanest version
- Remove near-duplicate complexity analysis cards

### 4. Quality Standards
Ensure the final deck has:
- Clear progression: Problem understanding → Core approaches → Implementation details
- Each card teaches ONE specific concept
- Front (question) is short and focused
- Back (answer) is detailed and includes code where relevant
- Real-world context if present

### 5. Consolidation Template
```
Problem Understanding
├── Problem statement + constraints
└── Key examples

Approach 1: [Name]
├── Intuition (why it works)
├── Algorithm (step-by-step)
├── Code implementation
└── Complexity analysis

Approach 2: [Name]
├── [same structure as Approach 1]

[Additional approaches as needed]

Implementation
├── Common pitfalls
├── Optimization tips
└── Testing strategy

Context (optional)
└── Related problems / real-world use
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
