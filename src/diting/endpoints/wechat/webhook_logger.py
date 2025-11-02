"""
Webhook logger configuration

Configure structlog and RotatingFileHandler for webhook request logging.
"""

import logging
from logging.handlers import RotatingFileHandler
from os import W_OK, access
from pathlib import Path

import structlog


def setup_webhook_logger(log_file: str, max_bytes: int, backup_count: int, log_level: str):
    """
    Setup webhook logger

    Args:
        log_file: Log file path
        max_bytes: Maximum bytes per log file
        backup_count: Number of backup files to keep
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure rotating file handler
    rotating_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    rotating_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=rotating_handler.stream),
        cache_logger_on_first_use=True,
    )

    # Also configure standard logging for other libraries
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(message)s",
        handlers=[rotating_handler],
    )


def get_webhook_logger():
    """Get webhook logger instance"""
    return structlog.get_logger("webhook")


def check_log_writable(log_file: str) -> tuple[bool, str | None]:
    """
    Check if log file is writable

    Returns:
        (is_writable, error_message)
    """
    try:
        log_path = Path(log_file)
        # If file exists, check if writable
        if log_path.exists():
            with log_path.open("a", encoding="utf-8") as f:
                f.write("")  # Try to write empty string
            return True, None
        # If file doesn't exist, check if parent directory is writable
        if log_path.parent.exists():
            return log_path.parent.is_dir() and access(str(log_path.parent), W_OK), None
        # Parent directory doesn't exist
        return False, "Log directory does not exist"
    except PermissionError as e:
        return False, f"Permission denied: {e}"
    except Exception as e:
        return False, f"Log check failed: {e}"
