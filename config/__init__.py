"""Configuration module — loads .env and exposes settings."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from config/ directory
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Fallback: try project root
    load_dotenv(Path(__file__).parent.parent / ".env")

# --- Ollama ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "-1")

# --- Database connection strings ---
DB_ERP_URL = os.getenv("DB_ERP_URL", "")
DB_HR_URL = os.getenv("DB_HR_URL", "")
DB_PROJ_URL = os.getenv("DB_PROJ_URL", "")

DB_URLS = {
    "erp": DB_ERP_URL,
    "hr": DB_HR_URL,
    "projects": DB_PROJ_URL,
}

# --- JWT ---
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"

# --- Document pipeline ---
DOC_ROOT = os.getenv("DOC_ROOT", "/mnt/company-docs")
INDEX_PATH = os.getenv("INDEX_PATH", str(Path(__file__).parent.parent / "index"))
