"""Logging configuration for the backend application."""

import contextvars
import logging
import sys
from typing import Any

from backend.config import LOG_LEVEL

# Context variable to store request_id
request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="N/A")


def setup_logging() -> None:
    """Configure root logger with custom format including request_id support."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | [request_id=%(request_id)s] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Set request_id from context variable in record factory
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        # Get request_id from context variable (or use default)
        # Only set if not already set by extra
        if not hasattr(record, "request_id"):
            record.request_id = request_id_context.get()
        return record

    logging.setLogRecordFactory(record_factory)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)

