"""Structured logging setup with structlog."""

import logging
import sys

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog with console output.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
