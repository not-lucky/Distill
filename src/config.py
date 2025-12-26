import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVAL_DIR = BASE_DIR / "anki_cards_archival"
CEREBRAS_KEYS_FILE_PATH = Path(os.getenv("CEREBRAS_KEYS_FILE_PATH", "api_keys.json"))
OPENROUTER_KEYS_FILE = Path(os.getenv("OPENROUTER_KEYS_FILE_PATH", "openrouter_keys.json"))
GEMINI_CREDENTIALS_FILE = Path(os.getenv("GEMINI_CREDENTIALS_FILE_PATH", "python3ds.json"))
NVIDIA_KEYS_FILE = Path(os.getenv("NVIDIA_KEYS_FILE_PATH", "nvidia_keys.json"))

# Configuration
CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", 5))
ENABLE_GEMINI = os.getenv("ENABLE_GEMINI", "False").lower() == "true"
