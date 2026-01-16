"""Query utilities for filtering and retrieving data from the database"""

from typing import List, Dict, Optional
from datetime import datetime
from src.database import get_session, Run, Problem, ProviderResult, Card
from sqlalchemy import func
import json


def get_runs(
    mode: Optional[str] = None,
    subject: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    status: Optional[str] = None,
    user_label: Optional[str] = None,
) -> List[Run]:
    """
    Filter runs by various criteria.

    Args:
        mode: Filter by generation mode (e.g., "leetcode", "cs_mcq")
        subject: Filter by subject (e.g., "leetcode", "cs", "physics")
        created_after: Filter runs created after this datetime
        created_before: Filter runs created before this datetime
        status: Filter by status ("running", "completed", "failed")
        user_label: Filter by user label (partial match)

    Returns:
        List of Run objects matching the criteria
    """
    session = get_session()
    query = session.query(Run)

    if mode:
        query = query.filter(Run.mode == mode)
    if subject:
        query = query.filter(Run.subject == subject)
    if created_after:
        query = query.filter(Run.created_at >= created_after)
    if created_before:
        query = query.filter(Run.created_at <= created_before)
    if status:
        query = query.filter(Run.status == status)
    if user_label:
        query = query.filter(Run.user_label.like(f"%{user_label}%"))

    results = query.order_by(Run.created_at.desc()).all()
    session.close()
    return results


def get_problems_by_run(run_id: str) -> List[Problem]:
    """
    Get all problems for a specific run.

    Args:
        run_id: The run ID

    Returns:
        List of Problem objects for this run
    """
    session = get_session()
    problems = session.query(Problem).filter(Problem.run_id == run_id).all()
    session.close()
    return problems


def get_problems_by_question(question_name: str) -> List[Problem]:
    """
    Get all historical attempts at a specific question.

    Args:
        question_name: The question name (partial match supported)

    Returns:
        List of Problem objects matching the question name
    """
    session = get_session()
    problems = (
        session.query(Problem)
        .filter(Problem.question_name.like(f"%{question_name}%"))
        .order_by(Problem.created_at.desc())
        .all()
    )
    session.close()
    return problems


def get_provider_results_by_problem(problem_id: int) -> List[ProviderResult]:
    """
    Get all provider results for a problem.

    Args:
        problem_id: The problem ID

    Returns:
        List of ProviderResult objects for this problem
    """
    session = get_session()
    results = (
        session.query(ProviderResult)
        .filter(ProviderResult.problem_id == problem_id)
        .all()
    )
    session.close()
    return results


def get_provider_results_by_run(
    run_id: str, provider_name: Optional[str] = None, success: Optional[bool] = None
) -> List[ProviderResult]:
    """
    Get provider results for a run with optional filters.

    Args:
        run_id: The run ID
        provider_name: Optional filter by provider name
        success: Optional filter by success status

    Returns:
        List of ProviderResult objects matching the criteria
    """
    session = get_session()
    query = session.query(ProviderResult).filter(ProviderResult.run_id == run_id)

    if provider_name:
        query = query.filter(ProviderResult.provider_name == provider_name)
    if success is not None:
        query = query.filter(ProviderResult.success == success)

    results = query.all()
    session.close()
    return results


def get_cards_by_problem(problem_id: int) -> List[Card]:
    """
    Get all cards for a problem.

    Args:
        problem_id: The problem ID

    Returns:
        List of Card objects for this problem
    """
    session = get_session()
    cards = (
        session.query(Card)
        .filter(Card.problem_id == problem_id)
        .order_by(Card.card_index)
        .all()
    )
    session.close()
    return cards


def get_cards_by_run(run_id: str, card_type: Optional[str] = None) -> List[Card]:
    """
    Get all cards for a run with optional card type filter.

    Args:
        run_id: The run ID
        card_type: Optional filter by card type

    Returns:
        List of Card objects matching the criteria
    """
    session = get_session()
    query = session.query(Card).filter(Card.run_id == run_id)

    if card_type:
        query = query.filter(Card.card_type == card_type)

    cards = query.all()
    session.close()
    return cards


def search_cards(search_query: str) -> List[Card]:
    """
    Search cards by content (front or back).

    Args:
        search_query: Search string to match in card content

    Returns:
        List of Card objects matching the search query
    """
    session = get_session()
    cards = (
        session.query(Card)
        .filter(
            (Card.front.like(f"%{search_query}%"))
            | (Card.back.like(f"%{search_query}%"))
        )
        .all()
    )
    session.close()
    return cards


def get_run_statistics(run_id: str) -> Dict:
    """
    Get aggregate statistics for a run.

    Args:
        run_id: The run ID

    Returns:
        Dictionary with run statistics
    """
    session = get_session()

    run = session.query(Run).filter(Run.id == run_id).first()
    if not run:
        session.close()
        return {"error": "Run not found"}

    problems = session.query(Problem).filter(Problem.run_id == run_id).all()
    provider_results = (
        session.query(ProviderResult).filter(ProviderResult.run_id == run_id).all()
    )
    cards = session.query(Card).filter(Card.run_id == run_id).all()

    successful_problems = [p for p in problems if p.status == "success"]
    failed_problems = [p for p in problems if p.status == "failed"]

    stats = {
        "run_id": run_id,
        "user_label": run.user_label,
        "mode": run.mode,
        "subject": run.subject,
        "card_type": run.card_type,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "total_problems": len(problems),
        "successful_problems": len(successful_problems),
        "failed_problems": len(failed_problems),
        "success_rate": (len(successful_problems) / len(problems) * 100)
        if problems
        else 0,
        "total_cards": len(cards),
        "avg_cards_per_problem": len(cards) / len(successful_problems)
        if successful_problems
        else 0,
        "avg_processing_time": sum(p.processing_time_seconds or 0 for p in problems)
        / len(problems)
        if problems
        else 0,
        "provider_results": {
            "total": len(provider_results),
            "successful": sum(1 for pr in provider_results if pr.success),
            "failed": sum(1 for pr in provider_results if not pr.success),
            "by_provider": {},
        },
    }

    # Provider breakdown
    for pr in provider_results:
        if pr.provider_name not in stats["provider_results"]["by_provider"]:
            stats["provider_results"]["by_provider"][pr.provider_name] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "avg_cards": 0,
            }
        stats["provider_results"]["by_provider"][pr.provider_name]["total"] += 1
        if pr.success:
            stats["provider_results"]["by_provider"][pr.provider_name][
                "successful"
            ] += 1
        else:
            stats["provider_results"]["by_provider"][pr.provider_name]["failed"] += 1

    # Calculate avg cards per provider
    for provider_name in stats["provider_results"]["by_provider"]:
        provider_cards = [
            pr.card_count
            for pr in provider_results
            if pr.provider_name == provider_name and pr.card_count is not None
        ]
        if provider_cards:
            stats["provider_results"]["by_provider"][provider_name]["avg_cards"] = sum(
                provider_cards
            ) / len(provider_cards)

    session.close()
    return stats


def compare_runs(run_id1: str, run_id2: str) -> Dict:
    """
    Compare two runs side-by-side.

    Args:
        run_id1: First run ID
        run_id2: Second run ID

    Returns:
        Dictionary with comparison data
    """
    stats1 = get_run_statistics(run_id1)
    stats2 = get_run_statistics(run_id2)

    if "error" in stats1 or "error" in stats2:
        return {"error": "One or both runs not found"}

    comparison = {
        "run1": stats1,
        "run2": stats2,
        "differences": {
            "total_problems_diff": stats2["total_problems"] - stats1["total_problems"],
            "success_rate_diff": stats2["success_rate"] - stats1["success_rate"],
            "total_cards_diff": stats2["total_cards"] - stats1["total_cards"],
            "avg_cards_diff": stats2["avg_cards_per_problem"]
            - stats1["avg_cards_per_problem"],
            "processing_time_diff": stats2["avg_processing_time"]
            - stats1["avg_processing_time"],
        },
    }

    return comparison
