from pathlib import Path

def load_prompt(prompt_filename: str) -> str:
    """Load prompt template from src/data/prompts"""
    # Assuming this code is run from project root, or we use relative path from this file
    current_file_path = Path(__file__)
    project_root_path = current_file_path.parent.parent
    prompt_file_path = project_root_path / "src" / "data" / "prompts" / prompt_filename
    
    if not prompt_file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file_path}")
        
    with open(prompt_file_path, "r", encoding="utf-8") as prompt_file:
        return prompt_file.read()

# Load prompts at module level (or could be lazy loaded)
INITIAL_PROMPT_TEMPLATE = load_prompt("initial.md")
GENIUS_PERSONA_PROMPT_TEMPLATE = load_prompt("genius_cs.md")
COMBINE_PROMPT_TEMPLATE = load_prompt("combine.md")
MCQ_COMBINE_PROMPT_TEMPLATE = load_prompt("mcq_combine.md")
PHYSICS_PROMPT_TEMPLATE = load_prompt("physics.md")
MCQ_PROMPT_TEMPLATE = load_prompt("mcq.md")
PHYSICS_MCQ_PROMPT_TEMPLATE = load_prompt("physics_mcq.md")
