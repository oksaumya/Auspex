"""Project-wide settings and path helpers."""
import os
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
DEFAULT_PROJECT_ROOT = _THIS_FILE.parent.parent

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", str(DEFAULT_PROJECT_ROOT))).resolve()
DEMO_DIR = PROJECT_ROOT / "fixtures" / "demo_files"
LEARNING_DB_PATH = PROJECT_ROOT / "learning_database.json"
CHECKPOINT_DB_PATH = Path(os.getenv("CHECKPOINT_DB_PATH", str(PROJECT_ROOT / "auspex.db"))).resolve()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.1"))

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

LANGSMITH_ENABLED = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT", "auspex")

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
MAX_DIFF_CHARS = int(os.getenv("MAX_DIFF_CHARS", "100000"))


def has_groq_key() -> bool:
    return bool(GROQ_API_KEY) and "your_" not in (GROQ_API_KEY or "")
