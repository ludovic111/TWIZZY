"""Centralized logging configuration for TWIZZY.

Provides structured logging with rotation, filtering, and multiple outputs.
"""
import logging
import logging.handlers
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LoggingConfig:
    """Configuration for logging."""

    level: str = "INFO"
    log_dir: Path = Path.home() / ".twizzy" / "logs"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    file_output: bool = True
    json_format: bool = False


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured log records."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured fields."""
        # Base format
        base = f"[{self.formatTime(record)}] [{record.levelname}] [{record.name}]"

        # Add context if available
        context = getattr(record, "context", {})
        if context:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            base += f" [{context_str}]"

        # Add the message
        base += f" {record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


class ContextFilter(logging.Filter):
    """Filter that adds context to log records."""

    def __init__(self, default_context: dict[str, Any] | None = None):
        super().__init__()
        self.default_context = default_context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Add default context to record."""
        if not hasattr(record, "context"):
            record.context = {}
        record.context.update(self.default_context)
        return True


def setup_logging(config: LoggingConfig | None = None) -> logging.Logger:
    """Set up logging for TWIZZY.

    Args:
        config: Logging configuration. Uses defaults if not provided.

    Returns:
        The root TWIZZY logger
    """
    if config is None:
        config = LoggingConfig()

    # Create log directory
    config.log_dir.mkdir(parents=True, exist_ok=True)

    # Get or create logger
    logger = logging.getLogger("twizzy")
    logger.setLevel(getattr(logging, config.level.upper()))
    logger.handlers = []  # Clear existing handlers

    # Create formatter
    formatter = StructuredFormatter()

    # Console handler
    if config.console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if config.file_output:
        log_file = config.log_dir / "twizzy.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Separate error log
        error_file = config.log_dir / "twizzy.errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    # Add context filter
    logger.addFilter(ContextFilter())

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (will be prefixed with 'twizzy.')

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"twizzy.{name}")


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Log a message with additional context.

    Args:
        logger: The logger to use
        level: Log level (e.g., logging.INFO)
        message: The log message
        **context: Additional context fields
    """
    extra = {"context": context}
    logger.log(level, message, extra=extra)
