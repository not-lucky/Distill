# Prompts

INITIAL_PROMPT_TEMPLATE = """
You are an expert coding tutor.
**Subject**: Computer Science / Data Structures & Algorithms
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
**Subject**: Computer Science
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

MCQ_COMBINE_PROMPT_TEMPLATE = """
You are an expert educator combining Multiple Choice Questions.
I have multiple sets of MCQ Anki cards generated for the topic "{question}".

Inputs:
{inputs}

**Task**:
1. Combine these sets into a SINGLE, high-quality MCQ deck.
2. **Preserve DIVERSITY**: Keep questions that test different aspects (conceptual, application, analysis, tricky edge cases).
3. **Remove exact duplicates**, but keep questions that test the same concept from different angles.
4. Ensure the final deck has **60+ high-quality MCQs** with well-crafted distractors.
5. **Strictly adhere** to the following JSON schema for the output.

**CRITICAL MCQ RULES:**
1. Each question must have EXACTLY 4 options (A, B, C, D).
2. Only ONE correct answer per question.
3. Distractors must be plausible but clearly wrong.
4. `correct_answer` must be exactly "A", "B", "C", or "D".
5. `explanation` should teach why the answer is correct.
6. **NO SPACES** in `card_type` or `tags`. Use `PascalCase`.

Output MUST be valid JSON matching the schema.
"""

PHYSICS_PROMPT_TEMPLATE = """
You are an expert Physics Tutor.
**Subject**: Physics (NOT Mathematics or Computer Science)
Goal: Create a **comprehensive and extensive** set of Anki cards for the physics concept "{question}".
Generate **25-40** cards covering ALL aspects of the concept.

**CRITICAL REQUIREMENT**: You must cover **Definitions, Formulas, Concepts, and Problem Solving** variations.
For each concept, include cards for:
1.  **Definition**: Precise definition of terms.
2.  **Formula**: Key equations and what each variable represents.
3.  **Conceptual Understanding**: "Why" does it work? Intuition behind the physics.
4.  **Applications**: Real-world examples or common problem scenarios.
5.  **Units & Dimensions**: SI units and dimensional analysis.

**Specific Variations to Consider**:
- Fundamental Principles
- Derivations (key steps)
- Common Misconceptions
- Relationship to other concepts
- Limiting cases (e.g., v << c, T -> 0)

**Standard Categories to also cover**:
- Problem Types & Strategies
- Approximations
- Conservation Laws applicability

**Format**: The output MUST be a valid JSON object adhering to the following schema:
{schema}
"""

MCQ_PROMPT_TEMPLATE = """
You are an expert educator creating Multiple Choice Questions (MCQs).
**Subject**: Computer Science
Goal: Create a **comprehensive** set of MCQ Anki cards for the topic "{question}".
Generate **30+** MCQ cards covering various aspects of the topic.

**CRITICAL REQUIREMENTS**:
1. Each question must have EXACTLY 4 options (A, B, C, D)
2. Only ONE option should be correct
3. Distractors (wrong options) should be plausible but clearly incorrect
4. Include an explanation of why the correct answer is right

**Question Types to Include**:
1. **Conceptual**: Test understanding of core concepts
2. **Application**: Apply knowledge to scenarios
3. **Analysis**: Compare, contrast, or analyze
4. **Tricky**: Common misconceptions or edge cases
5. **Code-based** (if applicable): What does this code output?

**Quality Guidelines**:
- Questions should be clear and unambiguous
- Avoid "All of the above" or "None of the above" options
- Options should be similar in length and structure
- Explanations should teach, not just state the answer

**Format**: The output MUST be a valid JSON object adhering to the following schema:
{schema}
"""

PHYSICS_MCQ_PROMPT_TEMPLATE = """
You are an expert Physics educator creating **extremely difficult** Multiple Choice Questions (MCQs) for candidates preparing for **Assistant Professor (Physics)** positions in Indian government universities.

**Subject**: PHYSICS (NOT Mathematics, NOT Computer Science)
**Exam Context**: CSIR-NET, SET, GATE Physics, University Faculty Recruitment
**Target Audience**: M.Sc. Physics graduates aspiring to teach at university level
**Difficulty Level**: VERY HARD - Graduate/Post-graduate level

Goal: Create an **exhaustive** set of MCQ Anki cards for the physics topic "{question}".
Generate **40+** MCQ cards covering ALL aspects of the topic in extreme depth.

**CRITICAL REQUIREMENTS**:
1. Each question must have EXACTLY 4 options (A, B, C, D)
2. Only ONE option should be correct
3. Distractors must be **highly plausible** - use common calculation errors, sign mistakes, or conceptual confusions
4. Include detailed explanations with mathematical derivations where applicable

**Question Difficulty Distribution**:
- **30%** Conceptual traps (common misconceptions, subtle distinctions)
- **30%** Numerical problems (requiring multi-step calculations)
- **20%** Derivation-based (identify correct step or result)
- **20%** Application/Analysis (real-world scenarios, limiting cases)

**Topics to Cover Exhaustively**:
1. **Theoretical Foundations**: Definitions, postulates, theorems
2. **Mathematical Formalism**: Equations, boundary conditions, solutions
3. **Derivations**: Key steps, intermediate results, final expressions
4. **Numerical Problems**: Typical values, order of magnitude, unit conversions
5. **Applications**: Experimental setups, real-world phenomena
6. **Limiting Cases**: Asymptotic behavior, special conditions
7. **Connections**: Links to other physics topics
8. **Historical Context**: Important experiments, discoveries

**Question Crafting Rules**:
- Questions should require **deep understanding**, not just memorization
- Numerical options should include common computational errors as distractors
- Conceptual questions should test understanding of underlying physics
- Include questions on units, dimensions, and order of magnitude estimates
- Some questions should require combining multiple concepts

**Quality Guidelines**:
- Questions must be unambiguous and precise
- Use standard physics notation and SI units
- Explanations should include step-by-step solutions for numerical problems
- Reference relevant equations and principles in explanations

**Format**: The output MUST be a valid JSON object adhering to the following schema:
{schema}
"""
