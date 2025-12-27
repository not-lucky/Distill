
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme

# Define a custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "critical": "bold white on red",
    "success": "bold green",
    "repr.number": "bold cyan",
    "repr.str": "green",
})

# Create a global console object sharing the same theme
console = Console(theme=custom_theme)

def setup_logging(log_file: str = "app.log", level: str = "INFO"):
    """
    Sets up logging to both file (plain text) and terminal (rich).
    """
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    # We remove existing handlers to avoid duplicates if called multiple times or during reloads
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.setLevel(log_level)
    
    # Rich Handler (Console)
    rich_handler = RichHandler(
        console=console, 
        rich_tracebacks=True,
        show_time=True,
        omit_repeated_times=False,
        show_path=False, # cleaner look
        markup=True
    )
    rich_handler.setLevel(log_level)
    
    # File Handler
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    root_logger.addHandler(rich_handler)
    root_logger.addHandler(file_handler)

    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    log = logging.getLogger("rich")
    # log.info(f"Logging initialized. [link=file://{log_file}]Log file[/link]")
