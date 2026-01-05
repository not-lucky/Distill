import json
from pathlib import Path
import logging
from typing import Dict, List, Union, Tuple

logger = logging.getLogger(__name__)

# Type alias for the categorized structure
CategorizedQuestions = Dict[str, List[str]]  # {"category": ["problem1", "problem2"]}

def load_questions() -> Tuple[Union[CategorizedQuestions, List[str]], List[str], List[str]]:
    """
    Load questions from src/data/questions.json
    
    Returns:
        Tuple of (leetcode_questions, cs_questions, physics_questions)
        - leetcode_questions: Dict[str, List[str]] - categorized by topic
        - cs_questions: List[str] - flat list
        - physics_questions: List[str] - flat list
    """
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    data_path = project_root / "src" / "data" / "questions.json"
    
    if not data_path.exists():
        logger.error(f"Questions data file not found: {data_path}")
        return {}, [], []
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("leetcode", {}), data.get("cs", []), data.get("physics", [])
    except Exception as e:
        logger.error(f"Failed to load questions: {e}")
        return {}, [], []


def flatten_categorized_questions(categorized: CategorizedQuestions) -> List[str]:
    """
    Flatten a categorized question dict to a simple list.
    
    Args:
        categorized: Dict mapping category names to lists of problems
        
    Returns:
        Flat list of all problems
    """
    result = []
    for problems in categorized.values():
        result.extend(problems)
    return result


def get_indexed_questions(categorized: CategorizedQuestions) -> List[Tuple[int, str, int, str]]:
    """
    Get questions with their category and problem indices.
    
    Args:
        categorized: Dict mapping category names to lists of problems
        
    Returns:
        List of tuples: (category_index, category_name, problem_index, problem_name)
        Indices are 1-based for display purposes.
    """
    result = []
    for cat_idx, (category_name, problems) in enumerate(categorized.items(), start=1):
        for prob_idx, problem_name in enumerate(problems, start=1):
            result.append((cat_idx, category_name, prob_idx, problem_name))
    return result


# Load at module level
QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS = load_questions()
