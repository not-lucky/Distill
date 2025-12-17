import asyncio
import json
import os
import re
import datetime
import itertools
from pathlib import Path
from random import shuffle
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field
from cerebras.cloud.sdk import Cerebras
from gemini_webapi import GeminiClient
from gemini_webapi.constants import Model

from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
API_KEYS_FILE = Path(os.getenv("API_KEYS_FILE_PATH", ""))
GEMINI_CREDENTIALS_FILE = Path(os.getenv("GEMINI_CREDENTIALS_FILE_PATH", ""))
ARCHIVAL_DIR = Path("anki_cards_archival")
CONCURRENT_REQUESTS = 5  # Number of simultaneous questions
ENABLE_GEMINI = False # Set to True to enable Gemini generation

QUESTIONS = ["Lowest Common Ancestor of a Binary Search Tree",
"Binary Tree Level Order Traversal",
"Binary Tree Right Side View",
"Count Good Nodes In Binary Tree",
"Validate Binary Search Tree",
"Kth Smallest Element In a Bst",
"Construct Binary Tree From Preorder And Inorder Traversal",
"Binary Tree Maximum Path Sum",
"Serialize And Deserialize Binary Tree",]

# ----------------------------------------------------------------------
# Data Models
# ----------------------------------------------------------------------
class AnkiCard(BaseModel):
    model_config = {'extra': 'forbid'}
    card_type: str = Field(..., description="Type of the card (e.g., 'Concept', 'Code', 'Intuition'). Use PascalCase.")
    tags: List[str] = Field(..., description="Tags for the card. Use PascalCase.")
    front: str = Field(..., description="Front side of the card (Markdown supported)")
    back: str = Field(..., description="Back side of the card (Markdown supported)")

class LeetCodeProblem(BaseModel):
    model_config = {'extra': 'forbid'}
    title: str = Field(..., description="Title of the LeetCode problem")
    topic: str = Field(..., description="Main topic (e.g., 'Arrays', 'Linked Lists')")
    difficulty: str = Field(..., description="Difficulty level (Easy, Medium, Hard)")
    cards: List[AnkiCard]

# ----------------------------------------------------------------------
# Clients & Keys
# ----------------------------------------------------------------------
def load_api_keys() -> itertools.cycle:
    if not API_KEYS_FILE.exists():
        raise FileNotFoundError(f"API keys file not found: {API_KEYS_FILE}")
    
    with open(API_KEYS_FILE, "r") as f:
        keys_data = json.load(f)
    
    shuffle(keys_data)
    
    api_keys = [item["api_key"] for item in keys_data if "api_key" in item]
    if not api_keys:
        raise ValueError("No API keys found in the file.")
    
    print(f"Loaded {len(api_keys)} API keys.")
    return itertools.cycle(api_keys)

async def load_gemini_clients() -> itertools.cycle:
    """Initializes and returns a cycle of GeminiClients using all credentials."""
    if not GEMINI_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"Credentials file not found: {GEMINI_CREDENTIALS_FILE}")
    
    with GEMINI_CREDENTIALS_FILE.open("r", encoding="utf-8") as f:
        creds_list = json.load(f)
        if not creds_list:
            raise ValueError("No credentials found in JSON file")
    
    clients = []
    print(f"Loading {len(creds_list)} Gemini clients...")
    for i, creds in enumerate(creds_list):
        try:
            client = GeminiClient(creds["Secure_1PSID"], creds["Secure_1PSIDTS"], proxy=None)
            await client.init(auto_refresh=True)
            clients.append(client)
            print(f"  Initialized Gemini client {i+1}/{len(creds_list)}")
        except Exception as e:
            print(f"  Failed to initialize Gemini client {i+1}: {e}")

    if not clients:
        raise ValueError("Could not initialize any Gemini clients.")
        
    return itertools.cycle(clients)

# ----------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------
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
I have two sets of Anki cards generated for the problem "{question}".
Set 1 (Cerebras):
{cerebras_output}

Set 2 (Cerebras):
{cerebras_output_2}

Set 3 (Gemini):
{gemini_output}

**Task**:
1. Combine these three sets into a SINGLE, high-quality deck.
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

# ----------------------------------------------------------------------
# Generation Functions
# ----------------------------------------------------------------------
async def get_cerebras_initial_output(question: str, api_key: str, model: str = "gpt-oss-120b") -> str:
    print(f"  [Cerebras] Generating initial cards for '{question}'...")
    client = Cerebras(api_key=api_key)
    try:
        problem_schema = LeetCodeProblem.model_json_schema()
        
        # Run synchronous client call in a thread
        optional_args = {}
        if model == "gpt-oss-120b":
            optional_args["reasoning_effort"] = "high"

        completion = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
                {"role": "user", "content": INITIAL_PROMPT_TEMPLATE.format(
                    question=question,
                    schema=json.dumps(problem_schema, indent=2)
                )},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "leetcode_problem_schema",
                    "strict": True,
                    "schema": problem_schema
                }
            },
            temperature=0.4,
            **optional_args
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"  [Cerebras] Error: {e}")
        return ""

async def get_gemini_output(client: GeminiClient, question: str) -> str:
    print(f"  [Gemini] Generating initial cards for '{question}'...")
    try:
        problem_schema = LeetCodeProblem.model_json_schema()
        prompt = INITIAL_PROMPT_TEMPLATE.format(
            question=question,
            schema=json.dumps(problem_schema, indent=2)
        )
        response = await client.generate_content(prompt, model=Model.G_3_0_PRO)
        return response.text
    except Exception as e:
        print(f"  [Gemini] Error: {e}")
        return ""

async def get_combined_output(question: str, cerebras_text: str, cerebras_text_2: str, gemini_text: str, api_key: str) -> Optional[Dict]:
    print(f"  [Cerebras] Combining and structuring outputs for '{question}'...")
    client = Cerebras(api_key=api_key)
    try:
        problem_schema = LeetCodeProblem.model_json_schema()
        
        completion = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates Anki cards in JSON format."},
                {"role": "user", "content": COMBINE_PROMPT_TEMPLATE.format(
                    question=question,
                    cerebras_output=cerebras_text,
                    cerebras_output_2=cerebras_text_2,
                    gemini_output=gemini_text
                )},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "leetcode_problem_schema",
                    "strict": True,
                    "schema": problem_schema
                }
            },
            temperature=0.2,
            reasoning_effort='high'
        )
        
        content = completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"  [Cerebras] Combination Error: {e}")
        return None

# ----------------------------------------------------------------------
# Saving Functions
# ----------------------------------------------------------------------
def sanitize_filename(name: str) -> str:
    # Remove special characters and spaces
    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
    return re.sub(r'[-\s]+', '_', name)

def save_archival(question: str, data: Dict):
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    sanitized_name = sanitize_filename(question)
    filename = f"{timestamp}_{sanitized_name}.json"
    filepath = ARCHIVAL_DIR / filename
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [Save] Archived to {filepath}")

def save_final_deck(all_problems: List[Dict]):
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    filename = f"leetcode_anki_deck_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(all_problems, f, indent=2)
    print(f"  [Save] Final deck saved to {filename}")

# ----------------------------------------------------------------------
# Main Processing Logic
# ----------------------------------------------------------------------
async def process_question(
    question: str, 
    semaphore: asyncio.Semaphore, 
    key_cycle: itertools.cycle,
    gemini_cycle: Optional[itertools.cycle],
    all_problems: List[Dict]
):
    async with semaphore:
        # Get a key for this request cycle
        # Note: We might want a fresh key for each call, or one per question.
        # Here we grab one for the initial call and one for the combine call.
        
        api_key_initial = next(key_cycle)
        
        gemini_out = ""
        if ENABLE_GEMINI and gemini_cycle:
            gemini_client = next(gemini_cycle)
            cerebras_out, cerebras_out_2, gemini_out = await asyncio.gather(
                get_cerebras_initial_output(question, api_key_initial, "gpt-oss-120b"),
                get_cerebras_initial_output(question, next(key_cycle), 'zai-glm-4.6'),
                get_gemini_output(gemini_client, question),
            )
        else:
             cerebras_out, cerebras_out_2 = await asyncio.gather(
                get_cerebras_initial_output(question, api_key_initial, "gpt-oss-120b"),
                get_cerebras_initial_output(question, next(key_cycle), 'zai-glm-4.6'),
            )
        
        if not cerebras_out and not cerebras_out_2 and not gemini_out:
            print(f"  [Error] Both LLMs failed for '{question}'. Skipping.")
            return
            
        # 3. Combine
        api_key_combine = next(key_cycle)
        final_data = await get_combined_output(question, cerebras_out, cerebras_out_2, gemini_out, api_key_combine)
        
        if final_data:
            # Post-process tags/types (just in case)
            for card in final_data.get('cards', []):
                if 'tags' in card:
                    card['tags'] = [tag.replace(' ', '') for card_tag in card['tags'] for tag in [card_tag]] # Fix list comp
                    # The above line was a bit weird in original, let's fix it properly:
                    card['tags'] = [tag.replace(' ', '') for tag in card['tags']]

                if 'card_type' in card:
                    card['card_type'] = card['card_type'].replace(' ', '')

            # Save Archival
            save_archival(question, final_data)
            
            # Add to list (thread-safe append in asyncio is fine as it runs in single thread loop)
            all_problems.append(final_data)
        else:
            print(f"  [Error] Failed to generate final JSON for '{question}'.")

async def main():
    # Ensure archival directory exists
    ARCHIVAL_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        key_cycle = load_api_keys()
    except Exception as e:
        print(f"Error loading API keys: {e}")
        return

    # Initialize Gemini Client
    gemini_cycle = None
    if ENABLE_GEMINI:
        try:
            gemini_cycle = await load_gemini_clients()
        except Exception as e:
            print(f"Failed to initialize Gemini clients: {e}")
            return

    all_problems = []
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    
    tasks = []
    for i, question in enumerate(QUESTIONS):
        print(f"Queueing {i+1}/{len(QUESTIONS)}: {question}")
        tasks.append(process_question(question, semaphore, key_cycle, gemini_cycle, all_problems))
    
    await asyncio.gather(*tasks)

    # Save Final Deck
    if all_problems:
        save_final_deck(all_problems)
    else:
        print("No cards generated.")

if __name__ == "__main__":
    asyncio.run(main())
