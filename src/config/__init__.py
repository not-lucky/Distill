import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Go up from config/ to src/ to project root
ARCHIVAL_DIR = BASE_DIR / "anki_cards_archival"
CEREBRAS_KEYS_FILE_PATH = Path(os.getenv("CEREBRAS_KEYS_FILE_PATH", "api_keys.json"))
OPENROUTER_KEYS_FILE = Path(os.getenv("OPENROUTER_KEYS_FILE_PATH", "openrouter_keys.json"))
GEMINI_CREDENTIALS_FILE = Path(os.getenv("GEMINI_CREDENTIALS_FILE_PATH", "python3ds.json"))
NVIDIA_KEYS_FILE = Path(os.getenv("NVIDIA_KEYS_FILE_PATH", "nvidia_keys.json"))
CANOPYWAVE_KEYS_FILE = Path(os.getenv("CANOPYWAVE_KEYS_FILE_PATH", "canopywave_keys.json"))
BASETEN_KEYS_FILE = Path(os.getenv("BASETEN_KEYS_FILE_PATH", "baseten_keys.json"))
GOOGLE_GENAI_KEYS_FILE = Path(os.getenv("GOOGLE_GENAI_KEYS_FILE_PATH", "google_genai_keys.json"))

# Configuration
CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", 8))
ENABLE_GEMINI = os.getenv("ENABLE_GEMINI", "False").lower() == "true"

# Re-export subject config
from .subjects import SubjectRegistry, SubjectConfig

__all__ = [
    'BASE_DIR',
    'ARCHIVAL_DIR', 
    'CEREBRAS_KEYS_FILE_PATH',
    'OPENROUTER_KEYS_FILE',
    'GEMINI_CREDENTIALS_FILE',
    'NVIDIA_KEYS_FILE',
    'CANOPYWAVE_KEYS_FILE',
    'BASETEN_KEYS_FILE',
    'GOOGLE_GENAI_KEYS_FILE',
    'CONCURRENT_REQUESTS',
    'ENABLE_GEMINI',
    'SubjectRegistry',
    'SubjectConfig',
]
