"""Query service for CLI presentation of database queries."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from src.database import Run, Problem, ProviderResult, Card
from src import queries


OutputFormat = Literal["table", "json"]


@dataclass
class QueryResult:
    """Result of a query operation."""

    success: bool
    data: Any
    message: Optional[str] = None
    error: Optional[str] = None


def _format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M")


def _truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_table(headers: List[str], rows: List[List[str]]) -> str:
    """Format data as an ASCII table."""
    if not rows:
        return "No results found."

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Build format string
    format_str = " | ".join(f"{{:<{w}}}" for w in widths)
    separator = "-+-".join("-" * w for w in widths)

    # Build table
    lines = [
        format_str.format(*headers),
        separator,
    ]
    for row in rows:
        # Pad row if needed
        padded_row = list(row) + [""] * (len(headers) - len(row))
        lines.append(format_str.format(*padded_row[:len(headers)]))

    return "\n".join(lines)


class QueryService:
    """Service for querying and formatting database results."""

    def list_runs(
        self,
        subject: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        output_format: OutputFormat = "table",
    ) -> QueryResult:
        """
        List runs with optional filtering.

        Args:
            subject: Filter by subject
            status: Filter by status
            limit: Maximum number of results
            output_format: Output format (table or json)

        Returns:
            QueryResult with formatted output
        """
        try:
            runs = queries.get_runs_summary(
                limit=limit, subject=subject, status=status
            )

            if output_format == "json":
                return QueryResult(
                    success=True,
                    data=json.dumps({"runs": runs}, indent=2),
                    message=f"Found {len(runs)} run(s)",
                )

            # Table format
            headers = ["ID (short)", "Subject", "Type", "Status", "Created", "Problems", "Cards"]
            rows = [
                [
                    r["id"][:8],
                    r["subject"],
                    r["card_type"],
                    r["status"],
                    _format_datetime(
                        datetime.fromisoformat(r["created_at"]) if r["created_at"] else None
                    ),
                    f"{r['successful_problems']}/{r['total_problems']}",
                    str(r["card_count"]),
                ]
                for r in runs
            ]

            return QueryResult(
                success=True,
                data=_format_table(headers, rows),
                message=f"Found {len(runs)} run(s)",
            )

        except Exception as e:
            return QueryResult(success=False, data=None, error=str(e))

    def show_run(
        self,
        run_id: str,
        output_format: OutputFormat = "table",
    ) -> QueryResult:
        """
        Show details for a specific run.

        Args:
            run_id: Run ID (can be partial)
            output_format: Output format (table or json)

        Returns:
            QueryResult with run details
        """
        try:
            run = queries.get_run_by_id(run_id)
            if not run:
                return QueryResult(
                    success=False,
                    data=None,
                    error=f"Run not found: {run_id}",
                )

            stats = queries.get_run_statistics(str(run.id))

            if output_format == "json":
                return QueryResult(
                    success=True,
                    data=json.dumps(stats, indent=2),
                )

            # Table format - build a details view
            lines = [
                f"Run ID:      {stats['run_id']}",
                f"Subject:     {stats['subject']}",
                f"Card Type:   {stats['card_type']}",
                f"Mode:        {stats['mode']}",
                f"Status:      {stats['status']}",
                f"Label:       {stats['user_label'] or '-'}",
                f"Created:     {stats['created_at'] or '-'}",
                f"Completed:   {stats['completed_at'] or '-'}",
                "",
                "--- Statistics ---",
                f"Total Problems:     {stats['total_problems']}",
                f"Successful:         {stats['successful_problems']}",
                f"Failed:             {stats['failed_problems']}",
                f"Success Rate:       {stats['success_rate']:.1f}%",
                f"Total Cards:        {stats['total_cards']}",
                f"Avg Cards/Problem:  {stats['avg_cards_per_problem']:.1f}",
                f"Avg Processing:     {stats['avg_processing_time']:.2f}s",
                "",
                "--- Provider Results ---",
                f"Total:      {stats['provider_results']['total']}",
                f"Successful: {stats['provider_results']['successful']}",
                f"Failed:     {stats['provider_results']['failed']}",
            ]

            # Add provider breakdown
            by_provider = stats["provider_results"]["by_provider"]
            if by_provider:
                lines.append("")
                lines.append("By Provider:")
                for name, pstats in by_provider.items():
                    lines.append(
                        f"  {name}: {pstats['successful']}/{pstats['total']} "
                        f"(avg {pstats['avg_cards']:.1f} cards)"
                    )

            return QueryResult(
                success=True,
                data="\n".join(lines),
            )

        except Exception as e:
            return QueryResult(success=False, data=None, error=str(e))

    def list_problems(
        self,
        run_id: Optional[str] = None,
        status: Optional[str] = None,
        question_search: Optional[str] = None,
        limit: int = 20,
        output_format: OutputFormat = "table",
    ) -> QueryResult:
        """
        List problems with optional filtering.

        Args:
            run_id: Filter by run ID
            status: Filter by status
            question_search: Search in question names
            limit: Maximum number of results
            output_format: Output format (table or json)

        Returns:
            QueryResult with formatted output
        """
        try:
            problems = queries.get_problems(
                run_id=run_id,
                status=status,
                question_search=question_search,
                limit=limit,
            )

            if output_format == "json":
                data = [
                    {
                        "id": p.id,
                        "run_id": p.run_id,
                        "question_name": p.question_name,
                        "category": p.category_name,
                        "status": p.status,
                        "card_count": p.final_card_count,
                        "processing_time": p.processing_time_seconds,
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                    }
                    for p in problems
                ]
                return QueryResult(
                    success=True,
                    data=json.dumps({"problems": data}, indent=2),
                    message=f"Found {len(problems)} problem(s)",
                )

            # Table format
            headers = ["ID", "Run (short)", "Question", "Status", "Cards", "Time"]
            rows = [
                [
                    str(p.id),
                    str(p.run_id)[:8] if p.run_id else "-",
                    _truncate(str(p.question_name), 40),
                    str(p.status),
                    str(p.final_card_count or 0),
                    f"{p.processing_time_seconds:.1f}s" if p.processing_time_seconds else "-",
                ]
                for p in problems
            ]

            return QueryResult(
                success=True,
                data=_format_table(headers, rows),
                message=f"Found {len(problems)} problem(s)",
            )

        except Exception as e:
            return QueryResult(success=False, data=None, error=str(e))

    def list_providers(
        self,
        run_id: Optional[str] = None,
        provider_name: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 20,
        output_format: OutputFormat = "table",
    ) -> QueryResult:
        """
        List provider results with optional filtering.

        Args:
            run_id: Filter by run ID
            provider_name: Filter by provider name
            success: Filter by success status
            limit: Maximum number of results
            output_format: Output format (table or json)

        Returns:
            QueryResult with formatted output
        """
        try:
            results = queries.get_provider_results(
                run_id=run_id,
                provider_name=provider_name,
                success=success,
                limit=limit,
            )

            if output_format == "json":
                data = [
                    {
                        "id": r.id,
                        "problem_id": r.problem_id,
                        "provider": r.provider_name,
                        "model": r.provider_model,
                        "success": r.success,
                        "card_count": r.card_count,
                        "processing_time": r.processing_time_seconds,
                        "error": r.error_message,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in results
                ]
                return QueryResult(
                    success=True,
                    data=json.dumps({"provider_results": data}, indent=2),
                    message=f"Found {len(results)} result(s)",
                )

            # Table format
            headers = ["ID", "Provider", "Model", "Success", "Cards", "Time"]
            rows = [
                [
                    str(r.id),
                    _truncate(str(r.provider_name), 20),
                    _truncate(str(r.provider_model), 25),
                    "✓" if r.success else "✗",
                    str(r.card_count or 0),
                    f"{r.processing_time_seconds:.1f}s" if r.processing_time_seconds else "-",
                ]
                for r in results
            ]

            return QueryResult(
                success=True,
                data=_format_table(headers, rows),
                message=f"Found {len(results)} result(s)",
            )

        except Exception as e:
            return QueryResult(success=False, data=None, error=str(e))

    def list_cards(
        self,
        run_id: Optional[str] = None,
        card_type: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 20,
        output_format: OutputFormat = "table",
    ) -> QueryResult:
        """
        List cards with optional filtering and search.

        Args:
            run_id: Filter by run ID
            card_type: Filter by card type
            search_query: Search in card content
            limit: Maximum number of results
            output_format: Output format (table or json)

        Returns:
            QueryResult with formatted output
        """
        try:
            cards = queries.get_cards(
                run_id=run_id,
                card_type=card_type,
                search_query=search_query,
                limit=limit,
            )

            if output_format == "json":
                data = [
                    {
                        "id": c.id,
                        "problem_id": c.problem_id,
                        "card_type": c.card_type,
                        "front": c.front,
                        "back": c.back,
                        "tags": json.loads(str(c.tags)) if c.tags else [],
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                    }
                    for c in cards
                ]
                return QueryResult(
                    success=True,
                    data=json.dumps({"cards": data}, indent=2),
                    message=f"Found {len(cards)} card(s)",
                )

            # Table format
            headers = ["ID", "Problem", "Type", "Front (preview)", "Tags"]
            rows = [
                [
                    str(c.id),
                    str(c.problem_id),
                    str(c.card_type or "-"),
                    _truncate(str(c.front), 50),
                    _truncate(str(c.tags) if c.tags else "[]", 20),
                ]
                for c in cards
            ]

            return QueryResult(
                success=True,
                data=_format_table(headers, rows),
                message=f"Found {len(cards)} card(s)",
            )

        except Exception as e:
            return QueryResult(success=False, data=None, error=str(e))

    def show_stats(
        self,
        subject: Optional[str] = None,
        output_format: OutputFormat = "table",
    ) -> QueryResult:
        """
        Show global statistics.

        Args:
            subject: Filter by subject
            output_format: Output format (table or json)

        Returns:
            QueryResult with statistics
        """
        try:
            stats = queries.get_global_statistics(subject=subject)
            provider_stats = queries.get_provider_statistics()

            if output_format == "json":
                combined = {**stats, "providers": provider_stats["providers"]}
                return QueryResult(
                    success=True,
                    data=json.dumps(combined, indent=2),
                )

            # Build text report
            lines = []

            if subject:
                lines.append(f"=== Statistics for '{subject}' ===")
            else:
                lines.append("=== Global Statistics ===")

            lines.append("")
            lines.append("--- Runs ---")
            lines.append(f"Total:       {stats['runs']['total']}")
            lines.append(f"Completed:   {stats['runs']['completed']}")
            lines.append(f"Failed:      {stats['runs']['failed']}")
            lines.append(f"Running:     {stats['runs']['running']}")
            lines.append(f"Completion:  {stats['runs']['completion_rate']:.1f}%")

            lines.append("")
            lines.append("--- Problems ---")
            lines.append(f"Total:       {stats['problems']['total']}")
            lines.append(f"Successful:  {stats['problems']['successful']}")
            lines.append(f"Failed:      {stats['problems']['failed']}")
            lines.append(f"Success:     {stats['problems']['success_rate']:.1f}%")
            lines.append(f"Avg Time:    {stats['problems']['avg_processing_time']:.2f}s")

            lines.append("")
            lines.append("--- Cards ---")
            lines.append(f"Total:       {stats['cards']['total']}")
            lines.append(f"Avg/Problem: {stats['cards']['avg_per_problem']:.1f}")

            # Subject breakdown
            if stats["by_subject"]:
                lines.append("")
                lines.append("--- By Subject ---")
                for subj, data in stats["by_subject"].items():
                    lines.append(f"  {subj}: {data['runs']} runs, {data['cards']} cards")

            # Provider statistics
            if provider_stats["providers"]:
                lines.append("")
                lines.append("--- Providers ---")
                for key, pdata in provider_stats["providers"].items():
                    lines.append(
                        f"  {pdata['provider_name']} ({pdata['model']}): "
                        f"{pdata['successful']}/{pdata['total_requests']} "
                        f"({pdata['success_rate']:.1f}%)"
                    )

            return QueryResult(
                success=True,
                data="\n".join(lines),
            )

        except Exception as e:
            return QueryResult(success=False, data=None, error=str(e))
