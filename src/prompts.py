from pathlib import Path

def load_prompt(filename: str) -> str:
    """Load prompt template from src/data/prompts"""
    # Assuming this code is run from project root, or we use relative path from this file
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    prompt_path = project_root / "src" / "data" / "prompts" / filename
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# Load prompts at module level (or could be lazy loaded)
INITIAL_PROMPT_TEMPLATE = load_prompt("initial.md")
GENIUS_PERSONA_PROMPT_TEMPLATE = load_prompt("genius_cs.md")
COMBINE_PROMPT_TEMPLATE = load_prompt("combine.md")
MCQ_COMBINE_PROMPT_TEMPLATE = load_prompt("mcq_combine.md")
PHYSICS_PROMPT_TEMPLATE = load_prompt("physics.md")
MCQ_PROMPT_TEMPLATE = load_prompt("mcq.md")
PHYSICS_MCQ_PROMPT_TEMPLATE = load_prompt("physics_mcq.md")
