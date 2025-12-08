"""Configuration constants for the backend application."""

import os
from typing import Final, Optional
from pathlib import Path

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
except ImportError:
    # python-dotenv not installed, skip
    pass

# File size limits
MAX_FILE_SIZE_MB: Final[int] = int(os.getenv("MAX_FILE_SIZE_MB", "300"))
MAX_FILE_SIZE_BYTES: Final[int] = MAX_FILE_SIZE_MB * 1024 * 1024

# Allowed file types
ALLOWED_FILE_TYPES: Final[set[str]] = {"xlsx", "csv", "xlsb"}

# File processing parameters
DEFAULT_MAX_SCAN_ROWS: Final[int] = int(os.getenv("MAX_SCAN_ROWS", "200"))
DEFAULT_MAX_PREVIEW_ROWS: Final[int] = int(os.getenv("MAX_PREVIEW_ROWS", "50"))

# Logging
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")

# LLM Configuration
LLM_PROVIDER: Final[str] = os.getenv("LLM_PROVIDER", "qwen")  # Options: "mock", "chatgpt", "qwen", "local"
LLM_MODEL: Final[str] = os.getenv("QWEN_MODEL", "")  # Model name (provider-specific, reads from QWEN_MODEL)
LLM_API_KEY: Final[Optional[str]] = os.getenv("QWEN_API_KEY")  # API key (reads from QWEN_API_KEY)
LLM_BASE_URL: Final[Optional[str]] = os.getenv("QWEN_BASE_URL")  # Custom base URL (optional, reads from QWEN_BASE_URL)

