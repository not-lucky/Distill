"""Query utilities for filtering and retrieving data from the database"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from src.database import DatabaseManager, Run, Problem, ProviderResult, Card
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
import json


def _get_session() -> Session:
    """Get a database session from the default manager."""
    return DatabaseManager.get_default().get_session()


def get_runs(
    mode: Optional[str] = None,
    subject: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    status: Optional[str] = None,
    user_label: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
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
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)

    Returns:
        List of Run objects matching the criteria
    """
    session = _get_session()
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

    query = query.order_by(Run.created_at.desc())

    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    results = query.all()
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
    session = _get_session()
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
    session = _get_session()
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
    session = _get_session()
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
    session = _get_session()
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
    session = _get_session()
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
    session = _get_session()
    query = session.query(Card).filter(Card.run_id == run_id)

    if card_type:
        query = query.filter(Card.card_type == card_type)

    cards = query.all()
    session.close()
    return cards


def search_cards(
    search_query: str,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Card]:
    """
    Search cards by content (front or back).

    Args:
        search_query: Search string to match in card content
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)

    Returns:
        List of Card objects matching the search query
    """
    session = _get_session()
    query = (
        session.query(Card)
        .filter(
            (Card.front.like(f"%{search_query}%"))
            | (Card.back.like(f"%{search_query}%"))
        )
    )

    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    cards = query.all()
    session.close()
    return cards


def get_run_statistics(run_id: str) -> Dict[str, Any]:
    """
    Get aggregate statistics for a run.

    Args:
        run_id: The run ID

    Returns:
        Dictionary with run statistics
    """
    session = _get_session()

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

    # Build by_provider dict separately for type safety
    by_provider: Dict[str, Dict[str, Any]] = {}

    stats: Dict[str, Any] = {
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
            "by_provider": by_provider,
        },
    }

    # Provider breakdown
    for pr in provider_results:
        provider_name = str(pr.provider_name) if pr.provider_name else "unknown"
        if provider_name not in by_provider:
            by_provider[provider_name] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "avg_cards": 0,
            }
        by_provider[provider_name]["total"] += 1
        if pr.success:
            by_provider[provider_name]["successful"] += 1
        else:
            by_provider[provider_name]["failed"] += 1

    # Calculate avg cards per provider
    for provider_name in by_provider:
        provider_cards = [
            pr.card_count
            for pr in provider_results
            if pr.provider_name == provider_name and pr.card_count is not None
        ]
        if provider_cards:
            by_provider[provider_name]["avg_cards"] = sum(
                provider_cards
            ) / len(provider_cards)

    session.close()
    return stats


def compare_runs(run_id1: str, run_id2: str) -> Dict[str, Any]:
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


def get_runs_summary(
    limit: Optional[int] = None,
    subject: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get a summary of runs with card counts.

    Args:
        limit: Maximum number of runs to return
        subject: Filter by subject
        status: Filter by status

    Returns:
        List of dictionaries with run summary information
    """
    session = _get_session()

    # Build base query with card count
    query = (
        session.query(
            Run.id,
            Run.subject,
            Run.card_type,
            Run.status,
            Run.user_label,
            Run.created_at,
            Run.completed_at,
            Run.total_problems,
            Run.successful_problems,
            Run.failed_problems,
            func.count(Card.id).label("card_count"),
        )
        .outerjoin(Card, Card.run_id == Run.id)
        .group_by(Run.id)
        .order_by(desc(Run.created_at))
    )

    if subject:
        query = query.filter(Run.subject == subject)
    if status:
        query = query.filter(Run.status == status)
    if limit is not None:
        query = query.limit(limit)

    results = query.all()
    session.close()

    return [
        {
            "id": str(r.id),
            "subject": r.subject,
            "card_type": r.card_type,
            "status": r.status,
            "user_label": r.user_label,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "total_problems": r.total_problems or 0,
            "successful_problems": r.successful_problems or 0,
            "failed_problems": r.failed_problems or 0,
            "card_count": r.card_count or 0,
        }
        for r in results
    ]


def get_problems(
    run_id: Optional[str] = None,
    status: Optional[str] = None,
    question_search: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Problem]:
    """
    Get problems with flexible filtering.

    Args:
        run_id: Filter by run ID
        status: Filter by status
        question_search: Search in question name (partial match)
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of Problem objects
    """
    session = _get_session()
    query = session.query(Problem)

    if run_id:
        query = query.filter(Problem.run_id == run_id)
    if status:
        query = query.filter(Problem.status == status)
    if question_search:
        query = query.filter(Problem.question_name.like(f"%{question_search}%"))

    query = query.order_by(desc(Problem.created_at))

    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    results = query.all()
    session.close()
    return results


def get_provider_results(
    run_id: Optional[str] = None,
    provider_name: Optional[str] = None,
    success: Optional[bool] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[ProviderResult]:
    """
    Get provider results with flexible filtering.

    Args:
        run_id: Filter by run ID
        provider_name: Filter by provider name
        success: Filter by success status
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of ProviderResult objects
    """
    session = _get_session()
    query = session.query(ProviderResult)

    if run_id:
        query = query.filter(ProviderResult.run_id == run_id)
    if provider_name:
        query = query.filter(ProviderResult.provider_name == provider_name)
    if success is not None:
        query = query.filter(ProviderResult.success == success)

    query = query.order_by(desc(ProviderResult.created_at))

    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    results = query.all()
    session.close()
    return results


def get_cards(
    run_id: Optional[str] = None,
    card_type: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Card]:
    """
    Get cards with flexible filtering and search.

    Args:
        run_id: Filter by run ID
        card_type: Filter by card type
        search_query: Search in front/back content
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of Card objects
    """
    session = _get_session()
    query = session.query(Card)

    if run_id:
        query = query.filter(Card.run_id == run_id)
    if card_type:
        query = query.filter(Card.card_type == card_type)
    if search_query:
        query = query.filter(
            (Card.front.like(f"%{search_query}%"))
            | (Card.back.like(f"%{search_query}%"))
        )

    query = query.order_by(desc(Card.created_at))

    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    cards = query.all()
    session.close()
    return cards


def get_provider_statistics(run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get aggregate statistics by provider.

    Args:
        run_id: Optional run ID to filter by

    Returns:
        Dictionary with provider statistics
    """
    session = _get_session()

    query = session.query(
        ProviderResult.provider_name,
        ProviderResult.provider_model,
        func.count(ProviderResult.id).label("total"),
        func.sum(func.cast(ProviderResult.success, Integer)).label("successful"),
        func.avg(ProviderResult.processing_time_seconds).label("avg_time"),
        func.avg(ProviderResult.card_count).label("avg_cards"),
    ).group_by(ProviderResult.provider_name, ProviderResult.provider_model)

    if run_id:
        query = query.filter(ProviderResult.run_id == run_id)

    results = query.all()
    session.close()

    stats: Dict[str, Any] = {"providers": {}}
    for r in results:
        provider_key = f"{r.provider_name}:{r.provider_model}"
        total = r.total or 0
        successful = r.successful or 0
        stats["providers"][provider_key] = {
            "provider_name": r.provider_name,
            "model": r.provider_model,
            "total_requests": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "avg_processing_time": round(r.avg_time or 0, 2),
            "avg_cards_generated": round(r.avg_cards or 0, 1),
        }

    return stats


# Need to import Integer for the cast
from sqlalchemy import Integer as Integer


def get_global_statistics(subject: Optional[str] = None) -> Dict[str, Any]:
    """
    Get global statistics across all runs.

    Args:
        subject: Optional subject to filter by

    Returns:
        Dictionary with global statistics
    """
    session = _get_session()

    # Run statistics
    run_query = session.query(
        func.count(Run.id).label("total_runs"),
        func.sum(func.cast(Run.status == "completed", Integer)).label("completed_runs"),
        func.sum(func.cast(Run.status == "failed", Integer)).label("failed_runs"),
    )

    if subject:
        run_query = run_query.filter(Run.subject == subject)

    run_stats = run_query.first()

    # Problem statistics
    problem_query = session.query(
        func.count(Problem.id).label("total_problems"),
        func.sum(func.cast(Problem.status == "success", Integer)).label("successful"),
        func.avg(Problem.processing_time_seconds).label("avg_time"),
    )

    if subject:
        problem_query = problem_query.join(Run, Problem.run_id == Run.id).filter(
            Run.subject == subject
        )

    problem_stats = problem_query.first()

    # Card statistics
    card_query = session.query(func.count(Card.id).label("total_cards"))

    if subject:
        card_query = card_query.join(Run, Card.run_id == Run.id).filter(
            Run.subject == subject
        )

    card_stats = card_query.first()

    # Subject breakdown (if not filtering by subject)
    subject_breakdown = {}
    if not subject:
        subject_query = (
            session.query(
                Run.subject,
                func.count(Run.id).label("runs"),
                func.count(Card.id).label("cards"),
            )
            .outerjoin(Card, Card.run_id == Run.id)
            .group_by(Run.subject)
        )

        for r in subject_query.all():
            subject_breakdown[r.subject] = {
                "runs": r.runs or 0,
                "cards": r.cards or 0,
            }

    session.close()

    total_runs = run_stats.total_runs or 0 if run_stats else 0
    completed_runs = run_stats.completed_runs or 0 if run_stats else 0
    failed_runs = run_stats.failed_runs or 0 if run_stats else 0
    total_problems = problem_stats.total_problems or 0 if problem_stats else 0
    successful_problems = problem_stats.successful or 0 if problem_stats else 0
    avg_time = problem_stats.avg_time or 0 if problem_stats else 0
    total_cards = card_stats.total_cards or 0 if card_stats else 0

    return {
        "filter_subject": subject,
        "runs": {
            "total": total_runs,
            "completed": completed_runs,
            "failed": failed_runs,
            "running": total_runs - completed_runs - failed_runs,
            "completion_rate": (completed_runs / total_runs * 100) if total_runs > 0 else 0,
        },
        "problems": {
            "total": total_problems,
            "successful": successful_problems,
            "failed": total_problems - successful_problems,
            "success_rate": (successful_problems / total_problems * 100)
            if total_problems > 0
            else 0,
            "avg_processing_time": round(avg_time, 2),
        },
        "cards": {
            "total": total_cards,
            "avg_per_problem": round(total_cards / successful_problems, 1)
            if successful_problems > 0
            else 0,
        },
        "by_subject": subject_breakdown,
    }


def get_run_by_id(run_id: str) -> Optional[Run]:
    """
    Get a single run by ID.

    Args:
        run_id: The run ID (can be partial, will match prefix)

    Returns:
        Run object or None if not found
    """
    session = _get_session()

    # Try exact match first
    run = session.query(Run).filter(Run.id == run_id).first()

    # If not found, try prefix match
    if not run:
        run = session.query(Run).filter(Run.id.like(f"{run_id}%")).first()

    session.close()
    return run
