import json
from pathlib import Path
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Type alias for the categorized structure
CategorizedQuestions = Dict[str, List[str]]  # {"category": ["problem1", "problem2"]}

def load_questions() -> Tuple[CategorizedQuestions, CategorizedQuestions, CategorizedQuestions]:
    """
    Load questions from src/data/questions.json
    
    Returns:
        Tuple of (leetcode_questions, cs_questions, physics_questions)
        All are Dict[str, List[str]] - categorized by topic
    """
    current_file_path = Path(__file__)
    project_root_path = current_file_path.parent.parent
    questions_data_path = project_root_path / "src" / "data" / "questions.json"
    
    if not questions_data_path.exists():
        logger.error(f"Questions data file not found: {questions_data_path}")
        return {}, {}, {}
        
    try:
        with open(questions_data_path, "r", encoding="utf-8") as questions_file:
            questions_data = json.load(questions_file)
            return questions_data.get("leetcode", {}), questions_data.get("cs", {}), questions_data.get("physics", {})
    except Exception as error:
        logger.error(f"Failed to load questions: {error}")
        return {}, {}, {}


def flatten_categorized_questions(categorized_questions: CategorizedQuestions) -> List[str]:
    """
    Flatten a categorized question dict to a simple list.
    
    Args:
        categorized_questions: Dict mapping category names to lists of problems
        
    Returns:
        Flat list of all problems
    """
    flattened_result = []
    for problem_list in categorized_questions.values():
        flattened_result.extend(problem_list)
    return flattened_result


def get_indexed_questions(categorized_questions: CategorizedQuestions) -> List[Tuple[int, str, int, str]]:
    """
    Get questions with their category and problem indices.
    
    Args:
        categorized_questions: Dict mapping category names to lists of problems
        
    Returns:
        List of tuples: (category_index, category_name, problem_index, problem_name)
        Indices are 1-based for display purposes.
    """
    indexed_result = []
    for category_index, (category_name, problem_list) in enumerate(categorized_questions.items(), start=1):
        for problem_index, problem_name in enumerate(problem_list, start=1):
            indexed_result.append((category_index, category_name, problem_index, problem_name))
    return indexed_result


# Load at module level
QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS = load_questions()
