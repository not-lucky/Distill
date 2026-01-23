"""Progress visualization for LLM2Deck card generation.

Provides real-time progress feedback using rich library with:
- Overall progress bar (questions completed/total)
- Provider status table (name, model, status, tokens, cost)
- ETA estimation
- Live updating stats
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, List

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TaskID
from rich.table import Table
from rich.text import Text

from src.logging_config import console as default_console


class ProviderStatus(Enum):
    """Status indicators for providers."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class ProviderStats:
    """Statistics for a single provider."""
    name: str
    model: str
    status: ProviderStatus = ProviderStatus.PENDING
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    estimated_cost: float = 0.0
    
    @property
    def status_icon(self) -> str:
        """Get status icon for display."""
        icons = {
            ProviderStatus.PENDING: "⏳",
            ProviderStatus.RUNNING: "🔄",
            ProviderStatus.SUCCESS: "✓",
            ProviderStatus.FAILED: "✗",
        }
        return icons.get(self.status, "?")
    
    @property
    def status_style(self) -> str:
        """Get rich style for status."""
        styles = {
            ProviderStatus.PENDING: "dim",
            ProviderStatus.RUNNING: "cyan",
            ProviderStatus.SUCCESS: "green",
            ProviderStatus.FAILED: "red",
        }
        return styles.get(self.status, "")


@dataclass
class QuestionProgress:
    """Progress state for a single question."""
    name: str
    status: str = "pending"  # pending, generating, combining, complete, failed
    providers_complete: int = 0
    providers_total: int = 0


# Token pricing per 1M tokens (input, output) in USD
# Sources: Provider pricing pages as of Jan 2026
TOKEN_PRICING: Dict[str, tuple[float, float]] = {
    "cerebras": (0.60, 0.60),
    "nvidia": (0.50, 0.50),  # varies by model
    "openrouter": (0.50, 0.50),  # varies by model  
    "google_genai": (0.10, 0.40),  # Gemini 2.0 Flash
    "google_antigravity": (0.0, 0.0),  # Local proxy, free
}


class ProgressTracker:
    """Tracks and displays progress for card generation.
    
    Uses rich's Live display to show real-time progress including:
    - Overall progress bar with question count
    - Current question being processed
    - Provider status table with token/cost tracking
    - ETA estimation based on average processing time
    """

    def __init__(
        self,
        total_questions: int,
        provider_names: List[tuple[str, str]],  # List of (name, model) tuples
        console: Optional[Console] = None,
    ):
        """Initialize progress tracker.
        
        Args:
            total_questions: Total number of questions to process
            provider_names: List of (provider_name, model) tuples
            console: Rich console to use (default: global console)
        """
        self.console = console or default_console
        self.total_questions = total_questions
        self.completed_questions = 0
        self.failed_questions = 0
        self.current_question: Optional[str] = None
        
        # Initialize provider stats
        self.providers: Dict[str, ProviderStats] = {}
        for name, model in provider_names:
            key = f"{name}/{model}"
            self.providers[key] = ProviderStats(name=name, model=model)
        
        # Timing for ETA
        self.start_time: Optional[float] = None
        self.question_times: List[float] = []
        
        # Rich components
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=self.console,
        )
        self.task_id: Optional[TaskID] = None
        self.live: Optional[Live] = None

    def _calculate_eta(self) -> str:
        """Calculate estimated time remaining."""
        if not self.question_times or self.completed_questions == 0:
            return "calculating..."
        
        avg_time = sum(self.question_times) / len(self.question_times)
        remaining = self.total_questions - self.completed_questions
        eta_seconds = avg_time * remaining
        
        if eta_seconds < 60:
            return f"{eta_seconds:.0f}s"
        elif eta_seconds < 3600:
            minutes = eta_seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = eta_seconds / 3600
            return f"{hours:.1f}h"

    def _calculate_cost(self, provider_key: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate estimated cost for token usage."""
        stats = self.providers.get(provider_key)
        if not stats:
            return 0.0
        
        pricing = TOKEN_PRICING.get(stats.name, (0.0, 0.0))
        input_cost = (tokens_input / 1_000_000) * pricing[0]
        output_cost = (tokens_output / 1_000_000) * pricing[1]
        return input_cost + output_cost

    def _build_provider_table(self) -> Table:
        """Build the provider status table."""
        table = Table(title="Provider Status", box=None, padding=(0, 1))
        table.add_column("Provider", style="cyan", no_wrap=True)
        table.add_column("Model", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Success", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right", style="yellow")
        
        for stats in self.providers.values():
            status_text = Text(f"{stats.status_icon} {stats.status.value}", style=stats.status_style)
            tokens = f"{stats.tokens_input + stats.tokens_output:,}" if stats.tokens_input + stats.tokens_output > 0 else "-"
            cost = f"${stats.estimated_cost:.4f}" if stats.estimated_cost > 0 else "-"
            
            table.add_row(
                stats.name,
                stats.model[:20] + "..." if len(stats.model) > 20 else stats.model,
                status_text,
                str(stats.requests_success) if stats.requests_success > 0 else "-",
                str(stats.requests_failed) if stats.requests_failed > 0 else "-",
                tokens,
                cost,
            )
        
        return table

    def _build_stats_line(self) -> Text:
        """Build the stats summary line."""
        eta = self._calculate_eta()
        total_tokens = sum(s.tokens_input + s.tokens_output for s in self.providers.values())
        total_cost = sum(s.estimated_cost for s in self.providers.values())
        
        text = Text()
        text.append("ETA: ", style="dim")
        text.append(eta, style="bold cyan")
        text.append(" │ ", style="dim")
        text.append("Total Tokens: ", style="dim")
        text.append(f"{total_tokens:,}", style="bold")
        text.append(" │ ", style="dim")
        text.append("Est. Cost: ", style="dim")
        text.append(f"${total_cost:.4f}", style="bold yellow")
        
        return text

    def _build_display(self) -> Panel:
        """Build the complete display panel."""
        current = self.current_question or "Initializing..."
        current_text = Text()
        current_text.append("Current: ", style="dim")
        current_text.append(current[:60] + "..." if len(current) > 60 else current, style="bold")
        
        components = [
            self.progress,
            Text(),  # Spacer
            current_text,
            Text(),  # Spacer
            self._build_provider_table(),
            Text(),  # Spacer
            self._build_stats_line(),
        ]
        
        return Panel(
            Group(*components),
            title="[bold blue]LLM2Deck Generation Progress[/bold blue]",
            border_style="blue",
        )

    def start(self) -> None:
        """Start the progress display."""
        self.start_time = time.time()
        self.task_id = self.progress.add_task(
            "Generating cards",
            total=self.total_questions,
        )
        self.live = Live(
            self._build_display(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )
        self.live.start()

    def stop(self) -> None:
        """Stop the progress display."""
        if self.live:
            self.live.stop()
            self.live = None

    def _refresh(self) -> None:
        """Refresh the display."""
        if self.live:
            self.live.update(self._build_display())

    def start_question(self, question_name: str) -> None:
        """Mark a question as started.
        
        Args:
            question_name: Name of the question being processed
        """
        self.current_question = question_name
        self._refresh()

    def complete_question(self, question_name: str, success: bool = True, duration: Optional[float] = None) -> None:
        """Mark a question as completed.
        
        Args:
            question_name: Name of the completed question
            success: Whether the question was processed successfully
            duration: Time taken to process (for ETA calculation)
        """
        if success:
            self.completed_questions += 1
        else:
            self.failed_questions += 1
        
        if duration is not None:
            self.question_times.append(duration)
            # Keep only last 10 times for rolling average
            if len(self.question_times) > 10:
                self.question_times = self.question_times[-10:]
        
        if self.task_id is not None:
            self.progress.update(self.task_id, completed=self.completed_questions + self.failed_questions)
        
        self._refresh()

    def update_provider_status(
        self,
        provider_name: str,
        model: str,
        status: ProviderStatus,
        success: bool = True,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> None:
        """Update status for a provider.
        
        Args:
            provider_name: Name of the provider
            model: Model name
            status: New status
            success: Whether the request succeeded
            tokens_input: Input tokens used
            tokens_output: Output tokens used
        """
        key = f"{provider_name}/{model}"
        if key not in self.providers:
            self.providers[key] = ProviderStats(name=provider_name, model=model)
        
        stats = self.providers[key]
        stats.status = status
        stats.requests_total += 1
        
        if success:
            stats.requests_success += 1
        else:
            stats.requests_failed += 1
        
        stats.tokens_input += tokens_input
        stats.tokens_output += tokens_output
        stats.estimated_cost += self._calculate_cost(key, tokens_input, tokens_output)
        
        self._refresh()

    def get_summary(self) -> Dict:
        """Get final summary statistics.
        
        Returns:
            Dictionary with summary stats
        """
        total_time = time.time() - self.start_time if self.start_time else 0
        total_tokens = sum(s.tokens_input + s.tokens_output for s in self.providers.values())
        total_cost = sum(s.estimated_cost for s in self.providers.values())
        
        return {
            "total_questions": self.total_questions,
            "completed_questions": self.completed_questions,
            "failed_questions": self.failed_questions,
            "total_time_seconds": total_time,
            "total_tokens": total_tokens,
            "estimated_cost_usd": total_cost,
            "providers": {
                key: {
                    "requests_success": s.requests_success,
                    "requests_failed": s.requests_failed,
                    "tokens_total": s.tokens_input + s.tokens_output,
                    "estimated_cost": s.estimated_cost,
                }
                for key, s in self.providers.items()
            },
        }

    def print_summary(self) -> None:
        """Print a final summary to the console."""
        summary = self.get_summary()
        
        self.console.print()
        self.console.rule("[bold green]Generation Complete[/bold green]")
        self.console.print()
        
        # Summary table
        table = Table(title="Summary", box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        table.add_row("Questions Processed", f"{summary['completed_questions']}/{summary['total_questions']}")
        table.add_row("Failed", str(summary['failed_questions']))
        table.add_row("Total Time", f"{summary['total_time_seconds']:.1f}s")
        table.add_row("Total Tokens", f"{summary['total_tokens']:,}")
        table.add_row("Estimated Cost", f"${summary['estimated_cost_usd']:.4f}")
        
        self.console.print(table)
        self.console.print()
