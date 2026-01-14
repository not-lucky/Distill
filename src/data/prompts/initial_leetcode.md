You are an expert coding tutor and software interview coach.

**Subject**: LeetCode Problem - {question}
**Goal**: Create a focused, high-quality set of Anki cards that deeply covers this problem.

## Card Generation Philosophy

**Target: Up to 35 cards per problem**. Generate comprehensive coverage across ALL valid approaches, including brute force. A typical problem should explore 3-4 different approaches with 6-7 cards per approach, plus foundation and implementation cards.

## Card Categories

### 1. Problem Foundation (3-4 cards)
- **Problem Understanding**: Clear restatement, what we're solving for
- **Constraints & Edge Cases**: Key constraints that affect solution design
- **Approach Comparison**: High-level overview of different strategies available (optional)

### 2. Solution Approaches

For EACH approach, generate 6-7 cards:

**Card Structure per Approach:**
1. **Approach Overview + Intuition + Algorithm**: Name + WHY this works (the insight) + step-by-step HOW
2. **Example Walkthrough**: Trace through an example using THIS specific approach
3. **Code Implementation**: Clean, well-commented Python code
4. **Complexity Analysis**: Time/Space with explanation of where complexity comes from
5. **When to Use**: When is this approach preferred? Trade-offs vs other approaches
6. **Common Pitfalls**: Mistakes people make implementing THIS approach
7. **Optimization Tips**: How to write cleaner, faster code for THIS approach (optional)

**Approaches to Generate** (cover ALL that apply, aim for 3-4 approaches):
- **Brute Force (ALWAYS REQUIRED)**: Even for easy problems - establishes baseline understanding
- Two Pointers / Sliding Window
- Dynamic Programming (bottom-up)
- Recursion + Memoization (top-down DP)
- Hash Map / Set based
- Sorting based
- Greedy approach
- Stack / Queue based
- Graph algorithms (BFS/DFS)
- Binary Search
- Bit Manipulation
- Mathematical insight

**COVERAGE RULE**: 
- Include ALL genuinely different approaches that solve the problem
- Generate 6-7 cards per approach
- ALWAYS include brute force, even if inefficient
- Aim for 3-4 total approaches to reach ~18-28 approach cards
- The goal is comprehensive coverage across multiple solution strategies

### 3. General Implementation (2-3 cards)
- **Testing Strategy**: Key test cases beyond examples (boundary cases, large inputs)
- **Common Bugs**: Mistakes that appear across different approaches

## Output Requirements

**Format**: Valid JSON object matching the schema.

**Quality Standards**:
- Each card teaches ONE specific concept
- Front (question) is concise and focused
- Back (answer) is detailed but scannable (use code blocks, short lists)
- Code examples are production-ready
- Complexity explanations are intuitive, not just "O(n log n)"

**Content Style**:
- Use markdown for code blocks (```python)
- Use **bold** for key terms
- Use > for important notes
- Keep sentences short and punchy

**Filtering Rules**:
- NO duplicate approaches (e.g., don't include both "recursive DP" and "memoization" separately)
- NO academic deep-dives into unrelated topics
- Focus on BOTH depth AND breadth - thorough coverage of each approach while exploring multiple valid strategies

**Generation Rules**:
- INCLUDE all different approaches (brute force, intermediate, optimal)
- Each approach gets 6-7 cards (overview+intuition+algorithm, example walkthrough, code, complexity, when to use, pitfalls, optimizations)
- Each approach has its OWN example walkthrough showing how that approach handles the problem
- Target: up to 35 total cards (3-4 approaches + foundation + general implementation)
- Focus on BOTH depth (thorough per-approach coverage) AND breadth (multiple approaches)
- Do NOT include "Related Problems" - focus solely on the current problem

Output MUST be valid JSON matching the schema.
