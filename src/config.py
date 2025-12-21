import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVAL_DIR = BASE_DIR / "anki_cards_archival"
CEREBRAS_KEYS_FILE_PATH = Path(os.getenv("CEREBRAS_KEYS_FILE_PATH", "api_keys.json"))
OPENROUTER_KEYS_FILE = Path(os.getenv("OPENROUTER_KEYS_FILE_PATH", "openrouter_keys.json"))
GEMINI_CREDENTIALS_FILE = Path(os.getenv("GEMINI_CREDENTIALS_FILE_PATH", "python3ds.json"))

# Configuration
CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", 5))
ENABLE_GEMINI = os.getenv("ENABLE_GEMINI", "False").lower() == "true"

# Questions
QUESTIONS = [
"Contains Duplicate",
"Valid Anagram",
"Two Sum",
"Group Anagrams",
"Top K Frequent Elements",
"Encode and Decode Strings",
"Product of Array Except Self",
"Valid Sudoku",
"Longest Consecutive Sequence",
"Valid Palindrome",
"Two Sum II Input Array Is Sorted",
"3Sum",
"Container With Most Water",
"Trapping Rain Water",
"Best Time to Buy And Sell Stock",
"Longest Substring Without Repeating Characters",
"Longest Repeating Character Replacement",
"Permutation In String",
"Minimum Window Substring",
"Sliding Window Maximum",
"Valid Parentheses",
"Min Stack",
"Evaluate Reverse Polish Notation",
"Daily Temperatures",
"Car Fleet",
"Largest Rectangle In Histogram",
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

GENIUS_PERSONA_PROMPT_TEMPLATE = """
You are a 140 IQ computer science genius and polymath.
Your goal is to explain the concept "{question}" to a young, extremely talented freshman student.
They have high potential and learn very quickly, but they lack some prerequisite knowledge.

**Your Teaching Style:**
1.  **First Principles**: Break everything down to its fundamental truths. Don't just say "it works this way", explain *why* it must work this way from a logical or physical standpoint.
2.  **Analogy & Intuition**: Use brilliant, unconventional analogies to bridge the gap between the unknown and the known.
3.  **No Jargon dumping**: Introduce terms only when necessary, and define them immediately and clearly.
4.  **Deep Insight**: Don't just cover the surface. Explain the deep connections to other fields or concepts if relevant.
5.  **Challenging but Accessible**: Respect their intelligence. Don't dumb it down, but make the path to understanding clear.

**Task**: Create a **comprehensive** set of Anki cards (25-40 cards) to master this concept.

**Card Categories to Cover:**
1.  **The "Why"**: Why does this concept exist? What problem does it solve?
2.  **The "What"**: Definitions, but explained intuitively.
3.  **The "How"**: Mechanisms, algorithms, or internal workings.
4.  **Mental Models**: How should one visualize or think about this concept?
5.  **Connections**: How does this relate to other CS concepts (OS, Architecture, Math, etc.)?

**Format**: The output MUST be a valid JSON object adhering to the following schema:
{schema}
"""

CS_QUESTIONS = [
    "How does a Hash Map work internally?",
    # "The difference between Process and Thread",
    # "How does Garbage Collection work?",
    # "TCP vs UDP",
    # "What happens when you type a URL into a browser?",
    # "Big O Notation and Time Complexity",
    # "Virtual Memory and Paging",
    # "CAP Theorem",
    # "ACID properties in Databases",
    # "Public Key Cryptography (RSA)",
]

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
