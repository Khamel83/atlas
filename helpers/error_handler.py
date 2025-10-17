"""
Centralized Error Handling and Logging Utilities

This module provides standardized error handling, logging, and retry mechanisms
for the Atlas system, ensuring consistent error reporting and handling patterns.
"""

import os
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from helpers.retry_queue import enqueue


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better organization."""

    NETWORK = "network"
    PARSING = "parsing"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    FILE_SYSTEM = "file_system"
    EXTERNAL_API = "external_api"
    PROCESSING = "processing"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Container for error context information."""

    module: str
    function: str
    url: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AtlasError:
    """Standardized error object for Atlas system."""

    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: ErrorContext
    original_exception: Optional[Exception] = None
    traceback_str: Optional[str] = None
    should_retry: bool = False
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.original_exception and not self.traceback_str:
            self.traceback_str = traceback.format_exc()


class AtlasErrorHandler:
    """Centralized error handler for the Atlas system."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_directory = config.get("data_directory", "output")
        self.error_log_path = os.path.join(self.data_directory, "error_log.jsonl")
        self._setup_error_logging()

    def _setup_error_logging(self):
        """Set up error logging infrastructure."""
        os.makedirs(os.path.dirname(self.error_log_path), exist_ok=True)

    def handle_error(self, error: AtlasError, log_path: str) -> bool:
        """
        Handle an error with appropriate logging and retry logic.

        Args:
            error: The AtlasError object
            log_path: Path to the module-specific log file

        Returns:
            bool: True if error was handled successfully, False otherwise
        """
        # Log to module-specific log
        self._log_to_module(error, log_path)

        # Log to centralized error log
        self._log_to_central(error)

        # Handle retry logic if applicable
        if error.should_retry and error.retry_count < error.max_retries:
            return self._handle_retry(error)

        # Log critical errors to troubleshooting checklist
        if error.severity == ErrorSeverity.CRITICAL:
            self._update_troubleshooting_checklist(error)

        return False

    def _log_to_module(self, error: AtlasError, log_path: str):
        """Log error to module-specific log file."""
        from helpers.utils import log_error

        error_msg = f"[{error.category.value.upper()}] {error.message}"
        if error.context.url:
            error_msg += f" (URL: {error.context.url})"
        if error.context.file_path:
            error_msg += f" (File: {error.context.file_path})"

        log_error(log_path, error_msg)

        # Log traceback if available
        if error.traceback_str:
            log_error(log_path, f"Traceback:\n{error.traceback_str}")

    def _log_to_central(self, error: AtlasError):
        """Log error to centralized error log."""
        import json

        error_record = {
            "timestamp": error.context.timestamp,
            "message": error.message,
            "category": error.category.value,
            "severity": error.severity.value,
            "module": error.context.module,
            "function": error.context.function,
            "url": error.context.url,
            "file_path": error.context.file_path,
            "metadata": error.context.metadata,
            "retry_count": error.retry_count,
            "max_retries": error.max_retries,
            "should_retry": error.should_retry,
        }

        with open(self.error_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(error_record) + "\n")

    def _handle_retry(self, error: AtlasError) -> bool:
        """Handle retry logic for retryable errors."""
        retry_task = {
            "type": error.context.module,
            "error": error.message,
            "category": error.category.value,
            "severity": error.severity.value,
            "timestamp": error.context.timestamp,
            "retry_count": error.retry_count,
            "metadata": error.context.metadata,
        }

        # Add specific fields based on context
        if error.context.url:
            retry_task["url"] = error.context.url
        if error.context.file_path:
            retry_task["file_path"] = error.context.file_path

        enqueue(retry_task)
        return True

    def _update_troubleshooting_checklist(self, error: AtlasError):
        """Update troubleshooting checklist with critical errors."""
        checklist_path = "docs/troubleshooting_checklist.md"

        if not os.path.exists(checklist_path):
            return

        # Read existing checklist
        with open(checklist_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Add new critical error entry
        new_entry = f"""
-   [ ] **{error.category.value.title()} Error in {error.context.module}:**
    -   **Question:** Have you checked for {error.message.lower()}?
    -   **Context:** Critical error occurred in {error.context.function}. {error.message}
    -   **Last Seen:** {error.context.timestamp}
"""

        # Insert before the last section
        if "## Post-Task Checklist:" in content:
            content = content.replace(
                "## Post-Task Checklist:", new_entry + "\n## Post-Task Checklist:"
            )
        else:
            content += new_entry

        # Write updated checklist
        with open(checklist_path, "w", encoding="utf-8") as f:
            f.write(content)

    def create_error(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: ErrorContext,
        original_exception: Optional[Exception] = None,
        should_retry: bool = False,
        max_retries: int = 3,
    ) -> AtlasError:
        """Create a standardized AtlasError object."""
        return AtlasError(
            message=message,
            category=category,
            severity=severity,
            context=context,
            original_exception=original_exception,
            should_retry=should_retry,
            max_retries=max_retries,
        )

    def wrap_function(
        self,
        func: Callable,
        module_name: str,
        function_name: str,
        log_path: str,
        error_category: ErrorCategory = ErrorCategory.UNKNOWN,
        should_retry: bool = False,
    ):
        """
        Decorator to wrap functions with standardized error handling.

        Args:
            func: Function to wrap
            module_name: Name of the module
            function_name: Name of the function
            log_path: Path to log file
            error_category: Category of errors this function might produce
            should_retry: Whether errors should be retried
        """

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    module=module_name,
                    function=function_name,
                    metadata={"args": str(args), "kwargs": str(kwargs)},
                )

                error = self.create_error(
                    message=str(e),
                    category=error_category,
                    severity=ErrorSeverity.MEDIUM,
                    context=context,
                    original_exception=e,
                    should_retry=should_retry,
                )

                self.handle_error(error, log_path)
                return None

        return wrapper


class NetworkErrorHandler:
    """Specialized error handler for network-related errors."""

    @staticmethod
    def categorize_http_error(status_code: int) -> ErrorSeverity:
        """Categorize HTTP errors by status code."""
        if status_code in [400, 401, 403, 404]:
            return ErrorSeverity.MEDIUM
        elif status_code in [500, 502, 503, 504]:
            return ErrorSeverity.HIGH
        elif status_code == 429:  # Rate limiting
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.MEDIUM

    @staticmethod
    def should_retry_http_error(status_code: int) -> bool:
        """Determine if HTTP error should be retried."""
        # Retry on server errors and rate limiting
        return status_code in [429, 500, 502, 503, 504]


class FileSystemErrorHandler:
    """Specialized error handler for file system errors."""

    @staticmethod
    def categorize_fs_error(exception: Exception) -> ErrorSeverity:
        """Categorize file system errors."""
        if isinstance(exception, PermissionError):
            return ErrorSeverity.HIGH
        elif isinstance(exception, FileNotFoundError):
            return ErrorSeverity.MEDIUM
        elif isinstance(exception, OSError):
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.MEDIUM

    @staticmethod
    def should_retry_fs_error(exception: Exception) -> bool:
        """Determine if file system error should be retried."""
        # Don't retry permission errors or file not found
        return not isinstance(exception, (PermissionError, FileNotFoundError))


def create_error_handler(config: Dict[str, Any]) -> AtlasErrorHandler:
    """Factory function to create error handler."""
    return AtlasErrorHandler(config)


def handle_network_error(
    url: str,
    status_code: int,
    error_handler: AtlasErrorHandler,
    log_path: str,
    module_name: str,
    function_name: str,
) -> bool:
    """Convenience function for handling network errors."""
    context = ErrorContext(
        module=module_name,
        function=function_name,
        url=url,
        metadata={"status_code": status_code},
    )

    error = error_handler.create_error(
        message=f"HTTP {status_code} error for {url}",
        category=ErrorCategory.NETWORK,
        severity=NetworkErrorHandler.categorize_http_error(status_code),
        context=context,
        should_retry=NetworkErrorHandler.should_retry_http_error(status_code),
    )

    return error_handler.handle_error(error, log_path)


def handle_file_system_error(
    file_path: str,
    exception: Exception,
    error_handler: AtlasErrorHandler,
    log_path: str,
    module_name: str,
    function_name: str,
) -> bool:
    """Convenience function for handling file system errors."""
    context = ErrorContext(
        module=module_name,
        function=function_name,
        file_path=file_path,
        metadata={"exception_type": type(exception).__name__},
    )

    error = error_handler.create_error(
        message=f"File system error: {str(exception)}",
        category=ErrorCategory.FILE_SYSTEM,
        severity=FileSystemErrorHandler.categorize_fs_error(exception),
        context=context,
        original_exception=exception,
        should_retry=FileSystemErrorHandler.should_retry_fs_error(exception),
    )

    return error_handler.handle_error(error, log_path)
