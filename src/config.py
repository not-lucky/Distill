import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVAL_DIR = BASE_DIR / "anki_cards_archival"
API_KEYS_FILE = Path(os.getenv("API_KEYS_FILE_PATH", "api_keys.json"))
GEMINI_CREDENTIALS_FILE = Path(os.getenv("GEMINI_CREDENTIALS_FILE_PATH", "python3ds.json"))

# Configuration
CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", 5))
ENABLE_GEMINI = os.getenv("ENABLE_GEMINI", "False").lower() == "true"

# Questions
QUESTIONS = [
    "Lowest Common Ancestor of a Binary Search Tree",
    "Binary Tree Level Order Traversal",
    "Binary Tree Right Side View",
    "Count Good Nodes In Binary Tree",
    "Validate Binary Search Tree",
    "Kth Smallest Element In a Bst",
    "Construct Binary Tree From Preorder And Inorder Traversal",
    "Binary Tree Maximum Path Sum",
    "Serialize And Deserialize Binary Tree",
]

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
