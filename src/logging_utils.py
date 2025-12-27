
from contextlib import contextmanager
from src.logging_config import console

@contextmanager
def log_section(title: str):
    """
    Creates a visual section in the log output with a rule line.
    """
    console.print()
    console.rule(f"[bold blue]{title}[/bold blue]", align="left")
    yield
    console.print()

@contextmanager
def log_status(message: str):
    """
    Wraps a block of code with a spinner status.
    """
    with console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots"):
        yield
