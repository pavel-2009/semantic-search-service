"""Centralized logging configuration for the application."""

import logging
import sys

from core.config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(level: str | int | None = None) -> None:
    """Configure root logging with a unified format and level."""
    global _configured
    resolved_level = level if level is not None else settings.LOG_LEVEL.upper()

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT))
        root_logger.addHandler(handler)

    root_logger.setLevel(resolved_level)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, ensuring centralized logging is configured."""
    if not _configured:
        setup_logging()
    return logging.getLogger(name)
