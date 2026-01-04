import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_questions():
    """Load questions from src/data/questions.json"""
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    data_path = project_root / "src" / "data" / "questions.json"
    
    if not data_path.exists():
        logger.error(f"Questions data file not found: {data_path}")
        return {}, {}, {}
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("leetcode", []), data.get("cs", []), data.get("physics", [])
    except Exception as e:
        logger.error(f"Failed to load questions: {e}")
        return [], [], []

# Load at module level
QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS = load_questions()
