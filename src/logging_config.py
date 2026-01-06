
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme

# Define a custom theme
custom_logging_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "critical": "bold white on red",
    "success": "bold green",
    "repr.number": "bold cyan",
    "repr.str": "green",
})

# Create a global console object sharing the same theme
console = Console(theme=custom_logging_theme)

def setup_logging(log_file_path: str = "app.log", log_level_name: str = "INFO"):
    """
    Sets up logging to both file (plain text) and terminal (rich).
    """
    
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Configure root logger
    # We remove existing handlers to avoid duplicates if called multiple times or during reloads
    root_logger = logging.getLogger()
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)
        
    root_logger.setLevel(log_level)
    
    # Rich Handler (Console)
    rich_console_handler = RichHandler(
        console=console, 
        rich_tracebacks=True,
        show_time=True,
        omit_repeated_times=False,
        show_path=False, # cleaner look
        markup=True
    )
    rich_console_handler.setLevel(log_level)
    
    # File Handler
    file_log_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_log_handler.setLevel(log_level)
    file_log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_log_handler.setFormatter(file_log_formatter)
    
    root_logger.addHandler(rich_console_handler)
    root_logger.addHandler(file_log_handler)

    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    rich_logger = logging.getLogger("rich")
    # rich_logger.info(f"Logging initialized. [link=file://{log_file_path}]Log file[/link]")
