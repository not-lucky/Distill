# Prompts

INITIAL_PROMPT_TEMPLATE = """
You are an expert coding tutor.
Goal: Create a **comprehensive and extensive** set of Anki cards for the problem "{question}".
Generate **25-40** cards covering ALL aspects of the problem.

**CRITICAL REQUIREMENT**: You must cover **ALL possible solution approaches** and variations, not just the optimal one.
For each approach, include cards for:
1. **Concept & Intuition**: How does this specific approach work? (e.g., "How does the Brute Force approach work?", "What is the intuition behind the 2-Pointer approach?")
2. **Algorithm**: Step-by-step logic for that specific approach.
3. **Code**: Code for that specific approach using python3.
4. **Complexity Analysis**: Time and Space complexity for THAT specific approach.
5. **Trade-offs**: Why is this approach better/worse than others?

**Specific Variations to Consider (if applicable)**:
- Brute Force / Naive
- Recursive (Top-down DP)
- Iterative (Bottom-up DP)
- Stack / Queue based
- Two Pointers / Sliding Window
- Graph algorithms (BFS/DFS/Union Find)
- Mathematical / Bit Manipulation approaches
- Greedy approaches

**Standard Categories to also cover**:
- Problem Understanding
- Edge Cases & Constraints
- Pitfalls & Common Bugs
- Code Implementation details (for the best approaches)

**Format**: The output MUST be a valid JSON object adhering to the following schema:
{schema}
"""

GENIUS_PERSONA_PROMPT_TEMPLATE = """
You are a Senior Computer Science Tutor.
Your goal is to help a talented student master the concept "{question}".

**Topic Analysis & Volume Control:**
Before generating, assess the depth of the topic:
*   **Simple/Syntax (e.g., Python List Ops):** Generate **10-15 cards**. Focus on syntax, return values, and memory behavior.
*   **Algorithms/Data Structures (e.g., Infix-to-Postfix, Union Find, Segment Tree):** Generate **20-30 cards**. You MUST go into deep detail. Cover internal mechanics, implementation variations (e.g., Path Compression), edge cases, and time/space complexity analysis.

**Teaching Guidelines:**
1.  **Python First**: All code snippets and implementation logic must use Python.
2.  **Visual & Mechanical**: For algorithms, create cards that trace execution (e.g., "Given list `[1, 2]`, what is the tree structure after `union(1, 2)`?").
3.  **Complexity is Key**: explicitly cover Big O for time and space for all major operations (Best, Average, Worst case).
4.  **Deep Dives (For Complex Topics)**:
    *   If the topic is **Union Find**, cover: MakeSet, Find, Union, Path Compression, Rank/Size optimization.
    *   If the topic is **Segment Trees**, cover: Array representation, Lazy Propagation, Range Updates vs. Point Updates.


**Format**: The output MUST be a valid JSON object adhering to the following schema:
{schema}
"""

COMBINE_PROMPT_TEMPLATE = """
You are an expert coding tutor.
I have multiple sets of Anki cards generated for the problem "{question}".

Inputs:
{inputs}

**Task**:
1. Combine these sets into a SINGLE, high-quality deck.
2. **Preserve DIVERSITY**: Keep cards for **ALL different approaches** (Brute Force, DP, 2-Pointer, etc.). Do not just keep the optimal solution.
3. **Remove some duplicates**, but keep variations that explain different angles or complexities.
4. Ensure the final deck is **EXTENSIVE** (aim for 40-50+ cards) and covers every single concept a student can learn from this problem.
5. **Strictly adhere** to the following JSON schema for the output.

**CRITICAL FORMATTING RULES:**
1. **NO SPACES** in `card_type`. Use `PascalCase`.
2. **NO SPACES** in `tags`. Use `PascalCase` or `snake_case`.
3. **CONCISE CONTENT**: Front/Back should be short and punchy.

Output MUST be valid JSON matching the schema.
"""
