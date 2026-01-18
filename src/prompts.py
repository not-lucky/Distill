import os
from pathlib import Path

# Configurable prompts directory via environment variable
# Default: src/data/prompts relative to project root
_DEFAULT_PROMPTS_DIR = Path(__file__).parent / "data" / "prompts"
PROMPTS_DIR = Path(os.getenv("LLM2DECK_PROMPTS_DIR", str(_DEFAULT_PROMPTS_DIR)))


def load_prompt(prompt_filename: str) -> str:
    """
    Load prompt template from prompts directory.

    Args:
        prompt_filename: Name of the prompt file (e.g., "initial.md")

    Returns:
        Contents of the prompt file.

    Raises:
        FileNotFoundError: If prompt file doesn't exist.

    Note:
        The prompts directory can be configured via LLM2DECK_PROMPTS_DIR
        environment variable.
    """
    prompt_file_path = PROMPTS_DIR / prompt_filename

    if not prompt_file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file_path}")

    with open(prompt_file_path, "r", encoding="utf-8") as prompt_file:
        return prompt_file.read()

# Load prompts at module level (or could be lazy loaded)
INITIAL_PROMPT_TEMPLATE = load_prompt("initial.md")
INITIAL_LEETCODE_PROMPT_TEMPLATE = load_prompt("initial_leetcode.md")
INITIAL_CS_PROMPT_TEMPLATE = load_prompt("initial_cs.md")
COMBINE_PROMPT_TEMPLATE = load_prompt("combine.md")
COMBINE_LEETCODE_PROMPT_TEMPLATE = load_prompt("combine_leetcode.md")
COMBINE_CS_PROMPT_TEMPLATE = load_prompt("combine_cs.md")
MCQ_COMBINE_PROMPT_TEMPLATE = load_prompt("mcq_combine.md")
PHYSICS_PROMPT_TEMPLATE = load_prompt("physics.md")
MCQ_PROMPT_TEMPLATE = load_prompt("mcq.md")
PHYSICS_MCQ_PROMPT_TEMPLATE = load_prompt("physics_mcq.md")

