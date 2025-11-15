"""IO utilities for file handling."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def save_uploaded_file(file_content: bytes, file_name: str) -> str:
    """
    Save uploaded file content to a temporary file.

    Args:
        file_content: File content as bytes
        file_name: Original file name

    Returns:
        Path to the temporary file
    """
    # Create temporary file with appropriate extension
    suffix = Path(file_name).suffix
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="excel_accel_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(file_content)
        logger.debug(f"Saved uploaded file to temporary path: {temp_path}")
        return temp_path
    except Exception as e:
        os.close(fd)
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        logger.exception(f"Error saving uploaded file: {file_name}")
        raise


def cleanup_temp_file(file_path: str) -> None:
    """
    Delete a temporary file.

    Args:
        file_path: Path to the file to delete
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in MB
    """
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)

