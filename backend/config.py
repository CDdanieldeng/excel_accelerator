"""Configuration constants for the backend application."""

import os
from typing import Final

# File size limits
MAX_FILE_SIZE_MB: Final[int] = int(os.getenv("MAX_FILE_SIZE_MB", "300"))
MAX_FILE_SIZE_BYTES: Final[int] = MAX_FILE_SIZE_MB * 1024 * 1024

# Allowed file types
ALLOWED_FILE_TYPES: Final[set[str]] = {"xlsx", "csv", "xlsb"}

# Table detection parameters
MAX_HEADER_SEARCH_ROWS: Final[int] = int(os.getenv("MAX_HEADER_SEARCH_ROWS", "20"))
DEFAULT_MAX_SCAN_ROWS: Final[int] = int(os.getenv("MAX_SCAN_ROWS", "200"))
DEFAULT_MAX_PREVIEW_ROWS: Final[int] = int(os.getenv("MAX_PREVIEW_ROWS", "50"))

# Logging
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")

