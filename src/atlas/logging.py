"""
Logging infrastructure for Atlas v4.

Provides structured logging with rotation, proper formatting,
and integration with the Atlas operational model.
"""

import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import json


class AtlasFormatter(logging.Formatter):
    """Custom formatter for Atlas structured logging."""

    def __init__(self):
        super().__init__()
        self.base_format = "%(asctime)sZ %(levelname)-8s %(name)-20s %(message)s"
        self.date_format = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with Atlas context."""
        # Add UTC timestamp
        record.asctime = datetime.now(timezone.utc).strftime(self.date_format)

        # Format base message
        formatted = super().format(record)

        # Add structured context if available
        if hasattr(record, 'atlas_context') and record.atlas_context:
            context_str = " | ".join(f"{k}={v}" for k, v in record.atlas_context.items())
            formatted = f"{formatted} | {context_str}"

        return formatted


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_size_mb: int = 100,
    backup_count: int = 5,
    enable_console: bool = True
) -> None:
    """
    Setup logging for Atlas with rotation and structured output.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (optional)
        max_size_mb: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        enable_console: Enable console output
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = AtlasFormatter()

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=max_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set specific logger levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with Atlas-specific configuration."""
    return logging.getLogger(f"atlas.{name}")


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context
) -> None:
    """
    Log a message with structured context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error)
        message: Log message
        **context: Additional context fields
    """
    log_method = getattr(logger, level.lower())

    # Format context into message
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        full_message = f"{message} | {context_str}"
    else:
        full_message = message

    log_method(full_message)


class OperationLogger:
    """Specialized logger for Atlas operations."""

    def __init__(self, operation: str, source: str = ""):
        self.operation = operation
        self.source = source
        self.logger = get_logger(f"operations.{operation}")

    def start(self, message: str, **context) -> None:
        """Log operation start."""
        log_with_context(
            self.logger, "info", f"[START] {message}",
            operation=self.operation, source=self.source, **context
        )

    def success(self, message: str, **context) -> None:
        """Log operation success."""
        log_with_context(
            self.logger, "info", f"[SUCCESS] {message}",
            operation=self.operation, source=self.source, **context
        )

    def error(self, message: str, **context) -> None:
        """Log operation error."""
        log_with_context(
            self.logger, "error", f"[ERROR] {message}",
            operation=self.operation, source=self.source, **context
        )

    def warning(self, message: str, **context) -> None:
        """Log operation warning."""
        log_with_context(
            self.logger, "warning", f"[WARNING] {message}",
            operation=self.operation, source=self.source, **context
        )

    def info(self, message: str, **context) -> None:
        """Log operation info."""
        log_with_context(
            self.logger, "info", message,
            operation=self.operation, source=self.source, **context
        )


def log_ingestion_result(
    operation: OperationLogger,
    source: str,
    processed: int,
    duplicates: int,
    errors: int,
    duration_seconds: float
) -> None:
    """
    Log standardized ingestion results.

    Args:
        operation: Operation logger instance
        source: Source name
        processed: Number of items processed
        duplicates: Number of duplicates found
        errors: Number of errors encountered
        duration_seconds: Operation duration
    """
    operation.success(
        "Ingestion completed",
        source=source,
        processed=processed,
        duplicates=duplicates,
        errors=errors,
        duration_seconds=duration_seconds,
        items_per_second=processed / duration_seconds if duration_seconds > 0 else 0
    )


def log_error_with_traceback(
    operation: OperationLogger,
    error: Exception,
    context: Dict[str, Any]
) -> None:
    """
    Log error with full traceback and context.

    Args:
        operation: Operation logger instance
        error: Exception that occurred
        context: Additional context
    """
    operation.error(
        f"Error: {type(error).__name__}: {str(error)}",
        error_type=type(error).__name__,
        error_message=str(error),
        **context
    )

    # Log full traceback at debug level
    logger = get_logger(f"operations.{operation.operation}")
    logger.debug(f"Full traceback for {context}:", exc_info=error)