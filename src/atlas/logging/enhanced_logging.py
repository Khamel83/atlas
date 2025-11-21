"""
Enhanced Logging System for Atlas v4

Provides structured logging with error tracking, performance monitoring,
and comprehensive log management capabilities.
"""

import json
import logging
import logging.handlers
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict

from ..exceptions import AtlasException, ErrorContext


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: str = None
    function: str = None
    line_number: int = None
    error_code: str = None
    error_details: Dict[str, Any] = None
    performance_metrics: Dict[str, Any] = None
    user_id: str = None
    session_id: str = None
    component: str = None
    operation: str = None
    extra_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.error_details is None:
            self.error_details = {}
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.extra_data is None:
            self.extra_data = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def __init__(
        self,
        include_extra: bool = True,
        include_traceback: bool = True,
        format_type: str = "json"
    ):
        super().__init__()
        self.include_extra = include_extra
        self.include_traceback = include_traceback
        self.format_type = format_type

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured data."""
        # Create base log entry
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            module=getattr(record, 'module', None),
            function=getattr(record, 'funcName', None),
            line_number=getattr(record, 'lineno', None),
            extra_data={}
        )

        # Add exception information if present
        if record.exc_info:
            log_entry.error_details = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info) if self.include_traceback else None
            }

        # Add error details for Atlas exceptions
        if hasattr(record, 'error_code'):
            log_entry.error_code = record.error_code

        if hasattr(record, 'error_details'):
            log_entry.error_details.update(record.error_details)

        # Add performance metrics
        if hasattr(record, 'performance_metrics'):
            log_entry.performance_metrics.update(record.performance_metrics)

        # Add user and session information
        if hasattr(record, 'user_id'):
            log_entry.user_id = record.user_id

        if hasattr(record, 'session_id'):
            log_entry.session_id = record.session_id

        # Add component and operation
        if hasattr(record, 'component'):
            log_entry.component = record.component

        if hasattr(record, 'operation'):
            log_entry.operation = record.operation

        # Add any extra fields
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in [
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info', 'message'
                ]:
                    log_entry.extra_data[key] = value

        # Format based on type
        if self.format_type == "json":
            return json.dumps(log_entry.to_dict(), default=str)
        elif self.format_type == "simple":
            return f"{log_entry.timestamp} [{log_entry.level}] {log_entry.logger_name}: {log_entry.message}"
        else:
            # Detailed format
            parts = [
                f"{log_entry.timestamp}",
                f"[{log_entry.level}]",
                f"{log_entry.logger_name}"
            ]

            if log_entry.component:
                parts.append(f"({log_entry.component})")

            if log_entry.operation:
                parts.append(f"[{log_entry.operation}]")

            parts.append(f": {log_entry.message}")

            if log_entry.error_code:
                parts.append(f" [{log_entry.error_code}]")

            return " ".join(parts)


class PerformanceTracker:
    """Track performance metrics for operations."""

    def __init__(self, logger: logging.Logger, operation: str, component: str = None):
        self.logger = logger
        self.operation = operation
        self.component = component
        self.start_time = None
        self.end_time = None
        self.metrics = {}

    def __enter__(self):
        """Start performance tracking."""
        self.start_time = time.time()
        self.metrics["start_time"] = datetime.utcnow().isoformat() + "Z"
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End performance tracking and log metrics."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        self.metrics.update({
            "end_time": datetime.utcnow().isoformat() + "Z",
            "duration_seconds": round(duration, 3),
            "duration_ms": round(duration * 1000, 1)
        })

        # Add memory usage if available
        try:
            import psutil
            process = psutil.Process()
            self.metrics.update({
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent()
            })
        except ImportError:
            pass

        # Log performance metrics
        if exc_type:
            self.logger.error(
                f"Operation '{self.operation}' failed after {duration:.3f}s",
                extra={
                    "component": self.component,
                    "operation": self.operation,
                    "performance_metrics": self.metrics,
                    "error_type": exc_type.__name__ if exc_type else None
                }
            )
        else:
            self.logger.info(
                f"Operation '{self.operation}' completed in {duration:.3f}s",
                extra={
                    "component": self.component,
                    "operation": self.operation,
                    "performance_metrics": self.metrics
                }
            )

    def add_metric(self, key: str, value: Any):
        """Add custom metric."""
        self.metrics[key] = value


class EnhancedLogger:
    """Enhanced logger with additional capabilities."""

    def __init__(self, name: str, logger: logging.Logger):
        self.name = name
        self.logger = logger
        self.session_id = self._generate_session_id()

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        import uuid
        return str(uuid.uuid4())[:8]

    def log_operation(
        self,
        level: str,
        operation: str,
        message: str,
        component: str = None,
        user_id: str = None,
        extra_data: Dict[str, Any] = None,
        error: Exception = None
    ):
        """Log operation with context."""
        extra = {
            "component": component or self.name,
            "operation": operation,
            "session_id": self.session_id
        }

        if user_id:
            extra["user_id"] = user_id

        if extra_data:
            extra["extra_data"] = extra_data

        if error:
            if isinstance(error, AtlasException):
                extra.update({
                    "error_code": error.error_code,
                    "error_details": error.to_dict()
                })
            else:
                extra["error_details"] = {
                    "type": type(error).__name__,
                    "message": str(error)
                }

        # Get log level
        log_level = getattr(logging, level.upper(), logging.INFO)

        self.logger.log(
            log_level,
            message,
            extra=extra,
            exc_info=error is not None
        )

    def track_performance(
        self,
        operation: str,
        component: str = None
    ) -> PerformanceTracker:
        """Create performance tracker for operation."""
        return PerformanceTracker(
            logger=self.logger,
            operation=operation,
            component=component or self.name
        )

    def log_error(
        self,
        error: Exception,
        operation: str = None,
        component: str = None,
        user_id: str = None,
        extra_data: Dict[str, Any] = None
    ):
        """Log error with full context."""
        self.log_operation(
            level="ERROR",
            operation=operation or "unknown",
            message=f"Error occurred: {str(error)}",
            component=component,
            user_id=user_id,
            extra_data=extra_data,
            error=error
        )

    def log_ingestion_event(
        self,
        event_type: str,
        url: str,
        source_type: str,
        status: str,
        message: str = None,
        **kwargs
    ):
        """Log ingestion-specific events."""
        extra_data = {
            "url": url,
            "source_type": source_type,
            "event_type": event_type,
            "status": status
        }
        extra_data.update(kwargs)

        self.log_operation(
            level="INFO",
            operation=f"ingestion_{event_type}",
            message=message or f"{event_type.title()} for {source_type}: {url}",
            component="ingestion",
            extra_data=extra_data
        )

    def log_bot_event(
        self,
        event_type: str,
        user_id: str,
        command: str = None,
        message: str = None,
        **kwargs
    ):
        """Log bot-specific events."""
        extra_data = {
            "event_type": event_type,
            "user_id": user_id
        }

        if command:
            extra_data["command"] = command

        extra_data.update(kwargs)

        self.log_operation(
            level="INFO",
            operation=f"bot_{event_type}",
            message=message or f"{event_type.title()} from user {user_id}",
            component="bot",
            user_id=user_id,
            extra_data=extra_data
        )


def setup_enhanced_logging(
    level: str = "INFO",
    log_file: str = None,
    format_type: str = "json",
    enable_console: bool = True,
    max_file_size: str = "100MB",
    backup_count: int = 5,
    component_name: str = "atlas"
) -> EnhancedLogger:
    """
    Setup enhanced logging with structured output.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
        format_type: Format type (json, simple, detailed)
        enable_console: Whether to enable console logging
        max_file_size: Maximum log file size
        backup_count: Number of backup files to keep
        component_name: Component name for logger

    Returns:
        EnhancedLogger instance
    """
    # Create logger
    logger = logging.getLogger(component_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = StructuredFormatter(
        include_extra=True,
        include_traceback=True,
        format_type=format_type
    )

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Parse max file size
        size_units = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
        size_value = int(max_file_size[:-2])
        size_unit = max_file_size[-2:]
        max_bytes = size_value * size_units.get(size_unit, 1024**2)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Create enhanced logger
    enhanced_logger = EnhancedLogger(component_name, logger)

    # Log initialization
    enhanced_logger.log_operation(
        level="INFO",
        operation="logging_init",
        message=f"Enhanced logging initialized (level: {level}, format: {format_type})",
        component="logging"
    )

    return enhanced_logger


def get_logger(name: str) -> EnhancedLogger:
    """Get enhanced logger instance."""
    base_logger = logging.getLogger(name)
    return EnhancedLogger(name, base_logger)


# Context manager for operation logging
class OperationLogger:
    """Context manager for operation logging."""

    def __init__(
        self,
        logger: EnhancedLogger,
        operation: str,
        component: str = None,
        user_id: str = None,
        level: str = "INFO",
        log_start: bool = True,
        log_success: bool = True,
        log_failure: bool = True
    ):
        self.logger = logger
        self.operation = operation
        self.component = component
        self.user_id = user_id
        self.level = level
        self.log_start = log_start
        self.log_success = log_success
        self.log_failure = log_failure
        self.start_time = None

    def __enter__(self):
        """Start operation logging."""
        self.start_time = time.time()

        if self.log_start:
            self.logger.log_operation(
                level=self.level,
                operation=self.operation,
                message=f"Starting {self.operation}",
                component=self.component,
                user_id=self.user_id,
                extra_data={"start_time": datetime.utcnow().isoformat() + "Z"}
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End operation logging."""
        duration = time.time() - self.start_time if self.start_time else 0

        extra_data = {
            "end_time": datetime.utcnow().isoformat() + "Z",
            "duration_seconds": round(duration, 3)
        }

        if exc_type:
            if self.log_failure:
                self.logger.log_operation(
                    level="ERROR",
                    operation=self.operation,
                    message=f"Failed {self.operation}: {str(exc_val)}",
                    component=self.component,
                    user_id=self.user_id,
                    extra_data=extra_data,
                    error=exc_val
                )
        else:
            if self.log_success:
                self.logger.log_operation(
                    level=self.level,
                    operation=self.operation,
                    message=f"Completed {self.operation}",
                    component=self.component,
                    user_id=self.user_id,
                    extra_data=extra_data
                )