import json
from dataclasses import dataclass
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple

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


@dataclass
class QuestionFilter:
    """Configuration for filtering questions during generation.
    
    Filters are applied in order: category → question → skip_until → limit
    
    Attributes:
        category: Filter by category name (case-insensitive partial match)
        question_name: Filter by question name (case-insensitive partial match)
        limit: Maximum number of questions to process
        skip_until: Skip questions until reaching this one (case-insensitive partial match)
    """
    category: Optional[str] = None
    question_name: Optional[str] = None
    limit: Optional[int] = None
    skip_until: Optional[str] = None

    def has_filters(self) -> bool:
        """Check if any filters are configured."""
        return any([
            self.category is not None,
            self.question_name is not None,
            self.limit is not None,
            self.skip_until is not None,
        ])


def filter_indexed_questions(
    questions: List[Tuple[int, str, int, str]],
    filter_config: QuestionFilter,
) -> List[Tuple[int, str, int, str]]:
    """
    Apply filters to indexed questions.
    
    Filters are applied in order:
    1. category - filter by category name (case-insensitive partial match)
    2. question_name - filter by question name (case-insensitive partial match)
    3. skip_until - skip questions until reaching the specified one
    4. limit - take first N questions
    
    Args:
        questions: List of tuples (category_index, category_name, problem_index, question_name)
        filter_config: QuestionFilter with filter criteria
        
    Returns:
        Filtered list of question tuples
    """
    result = questions.copy()
    
    # 1. Filter by category (case-insensitive partial match)
    if filter_config.category:
        category_lower = filter_config.category.lower()
        result = [
            q for q in result 
            if category_lower in q[1].lower()  # q[1] is category_name
        ]
        if not result:
            logger.warning(f"No questions found in category matching '{filter_config.category}'")
    
    # 2. Filter by question name (case-insensitive partial match)
    if filter_config.question_name:
        question_lower = filter_config.question_name.lower()
        result = [
            q for q in result 
            if question_lower in q[3].lower()  # q[3] is question_name
        ]
        if not result:
            logger.warning(f"No questions found matching '{filter_config.question_name}'")
    
    # 3. Skip until (case-insensitive partial match)
    if filter_config.skip_until:
        skip_lower = filter_config.skip_until.lower()
        found_idx = None
        for idx, q in enumerate(result):
            if skip_lower in q[3].lower():  # q[3] is question_name
                found_idx = idx
                break
        
        if found_idx is not None:
            result = result[found_idx:]  # Include the matched question
        else:
            logger.warning(f"Question '{filter_config.skip_until}' not found, no questions to skip to")
            result = []
    
    # 4. Limit (take first N)
    if filter_config.limit is not None:
        if filter_config.limit <= 0:
            logger.warning(f"Invalid limit {filter_config.limit}, must be positive")
            result = []
        else:
            result = result[:filter_config.limit]
    
    return result


# Load at module level
QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS = load_questions()
