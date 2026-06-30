"""
Configuration manager for the Agentic Supply Chain Resilience Platform.
Loads environment variables and ensures workspace folders exist.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base project paths
BASE_DIR = Path(__file__).resolve().parent

# Load variables from .env relative to project directory
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Config parameters
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "mock-api-key")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ENV = os.getenv("ENV", "development")

# Networking / MCP
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8000"))
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "localhost")

# Storage folder configurations (resolved relative to BASE_DIR)
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
MEMORIES_DIR = BASE_DIR / os.getenv("MEMORIES_DIR", "memory")
REPORTS_DIR = BASE_DIR / os.getenv("REPORTS_DIR", "outputs/reports")
TRACES_DIR = BASE_DIR / os.getenv("TRACES_DIR", "outputs/traces")
AUDIT_LOG_PATH = BASE_DIR / os.getenv("AUDIT_LOG_PATH", "security/audit.log")

def initialize_directories():
    """Ensure all required project directories exist on startup."""
    dirs_to_create = [
        DATA_DIR,
        MEMORIES_DIR,
        REPORTS_DIR,
        TRACES_DIR,
        AUDIT_LOG_PATH.parent
    ]
    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)

# Run directory check on import
initialize_directories()

def get_masked_api_key() -> str:
    """Return a masked representation of the API key for secure logging."""
    if not GEMINI_API_KEY or GEMINI_API_KEY in ("mock-api-key", "mock-api-key-for-skeleton-testing"):
        return "[NOT CONFIGURED]"
    if len(GEMINI_API_KEY) <= 8:
        return "[INVALID/TOO SHORT]"
    return f"{GEMINI_API_KEY[:4]}...{GEMINI_API_KEY[-4:]}"

def has_valid_gemini_key() -> bool:
    """Return True when the runtime has a non-placeholder Gemini API key."""
    return bool(
        GEMINI_API_KEY
        and GEMINI_API_KEY not in ("mock-api-key", "mock-api-key-for-skeleton-testing")
        and len(GEMINI_API_KEY) > 8
    )
