"""
Atlas Exception Classes

Custom exceptions for Atlas v4 with proper error handling,
context information, and recovery suggestions.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ErrorContext:
    """Context information for errors."""
    component: str
    operation: str
    url: Optional[str] = None
    source_type: Optional[str] = None
    retry_count: int = 0
    additional_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


class AtlasException(Exception):
    """Base exception for Atlas errors."""

    def __init__(
        self,
        message: str,
        error_code: str = None,
        context: ErrorContext = None,
        recovery_suggestions: List[str] = None,
        cause: Exception = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context
        self.recovery_suggestions = recovery_suggestions or []
        self.cause = cause
        self.timestamp = None

        # Set timestamp
        from datetime import datetime
        self.timestamp = datetime.utcnow()

    def __str__(self):
        """String representation with context."""
        base_msg = f"[{self.error_code}] {self.message}"

        if self.context:
            base_msg += f" (component: {self.context.component}, operation: {self.context.operation})"

        if self.cause:
            base_msg += f" caused by: {str(self.cause)}"

        return base_msg

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": {
                "component": self.context.component if self.context else None,
                "operation": self.context.operation if self.context else None,
                "url": self.context.url if self.context else None,
                "source_type": self.context.source_type if self.context else None,
                "retry_count": self.context.retry_count if self.context else 0,
                "additional_data": self.context.additional_data if self.context else {}
            },
            "recovery_suggestions": self.recovery_suggestions,
            "cause": str(self.cause) if self.cause else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class ConfigurationError(AtlasException):
    """Raised for configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: str = None,
        config_file: str = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.config_file = config_file

        if not self.recovery_suggestions:
            self.recovery_suggestions = [
                "Check configuration file syntax",
                "Verify all required fields are present",
                "Ensure environment variables are set",
                "Run with --help to see configuration options"
            ]


class StorageError(AtlasException):
    """Raised for storage-related errors."""

    def __init__(
        self,
        message: str,
        file_path: str = None,
        operation: str = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.file_path = file_path
        self.operation = operation

        if not self.recovery_suggestions:
            self.recovery_suggestions = [
                "Check file permissions",
                "Verify disk space availability",
                "Check directory existence",
                "Ensure vault is properly initialized"
            ]


class IngestionError(AtlasException):
    """Raised for content ingestion errors."""

    def __init__(
        self,
        message: str,
        url: str = None,
        source_type: str = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.url = url
        self.source_type = source_type

        if not self.recovery_suggestions:
            suggestions = [
                "Check network connectivity",
                "Verify URL accessibility",
                "Check source credentials",
                "Try again later"
            ]

            if source_type == "rss":
                suggestions.extend([
                    "Check feed URL validity",
                    "Verify feed format (RSS/Atom)",
                    "Check User-Agent restrictions"
                ])
            elif source_type == "gmail":
                suggestions.extend([
                    "Check Gmail API credentials",
                    "Verify OAuth token validity",
                    "Check API quota limits"
                ])
            elif source_type == "youtube":
                suggestions.extend([
                    "Check YouTube API key",
                    "Verify video availability",
                    "Check API quota limits"
                ])

            self.recovery_suggestions = suggestions


class DatabaseError(AtlasException):
    """Raised for database-related errors."""

    def __init__(
        self,
        message: str,
        query: str = None,
        table: str = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.query = query
        self.table = table

        if not self.recovery_suggestions:
            self.recovery_suggestions = [
                "Check database file permissions",
                "Verify database schema",
                "Check available disk space",
                "Restart database connection",
                "Run database integrity check"
            ]


class BotError(AtlasException):
    """Raised for Telegram bot errors."""

    def __init__(
        self,
        message: str,
        user_id: str = None,
        command: str = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.user_id = user_id
        self.command = command

        if not self.recovery_suggestions:
            self.recovery_suggestions = [
                "Check bot token validity",
                "Verify user permissions",
                "Check bot configuration",
                "Try restarting the bot",
                "Check Telegram API status"
            ]


class AuthenticationError(AtlasException):
    """Raised for authentication/authorization errors."""

    def __init__(
        self,
        message: str,
        service: str = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.service = service

        if not self.recovery_suggestions:
            suggestions = [
                "Check credentials configuration",
                "Verify API keys/tokens",
                "Check service permissions",
                "Refresh authentication tokens"
            ]

            if service == "gmail":
                suggestions.extend([
                    "Re-run Gmail authentication flow",
                    "Check OAuth consent screen configuration",
                    "Verify required API scopes"
                ])
            elif service == "youtube":
                suggestions.extend([
                    "Verify YouTube Data API is enabled",
                    "Check API key restrictions",
                    "Verify quota usage"
                ])
            elif service == "telegram":
                suggestions.extend([
                    "Check bot token from BotFather",
                    "Verify bot is not blocked by user",
                    "Check bot privacy settings"
                ])

            self.recovery_suggestions = suggestions


class ValidationError(AtlasException):
    """Raised for data validation errors."""

    def __init__(
        self,
        message: str,
        field: str = None,
        value: Any = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value

        if not self.recovery_suggestions:
            self.recovery_suggestions = [
                "Check input data format",
                "Verify required fields are present",
                "Check data type constraints",
                "Validate against schema requirements"
            ]


class RateLimitError(AtlasException):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        service: str = None,
        retry_after: int = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.service = service
        self.retry_after = retry_after

        if not self.recovery_suggestions:
            self.recovery_suggestions = [
                "Wait before retrying",
                "Reduce request frequency",
                "Check rate limit configuration",
                "Implement backoff strategy"
            ]

            if self.retry_after:
                self.recovery_suggestions.insert(0, f"Wait {self.retry_after} seconds before retrying")


class TimeoutError(AtlasException):
    """Raised when operations timeout."""

    def __init__(
        self,
        message: str,
        timeout_duration: int = None,
        operation: str = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.timeout_duration = timeout_duration
        self.operation = operation

        if not self.recovery_suggestions:
            suggestions = [
                "Increase timeout configuration",
                "Check network connectivity",
                "Verify service availability",
                "Retry with exponential backoff"
            ]

            if self.timeout_duration:
                suggestions.append(f"Current timeout: {self.timeout_duration} seconds")

            self.recovery_suggestions = suggestions


class ContentError(AtlasException):
    """Raised for content processing errors."""

    def __init__(
        self,
        message: str,
        content_type: str = None,
        processing_step: str = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.content_type = content_type
        self.processing_step = processing_step

        if not self.recovery_suggestions:
            self.recovery_suggestions = [
                "Check content format",
                "Verify content encoding",
                "Try alternative extraction method",
                "Check for content corruption"
            ]


class RetryExhaustedError(AtlasException):
    """Raised when retry attempts are exhausted."""

    def __init__(
        self,
        message: str,
        max_attempts: int = None,
        last_error: Exception = None,
        **kwargs
    ):
        super().__init__(message, cause=last_error, **kwargs)
        self.max_attempts = max_attempts
        self.last_error = last_error

        if not self.recovery_suggestions:
            suggestions = [
                "Check underlying error cause",
                "Increase retry attempts",
                "Implement fallback strategy",
                "Add to failure queue for later processing"
            ]

            if self.max_attempts:
                suggestions.append(f"Failed after {self.max_attempts} attempts")

            self.recovery_suggestions = suggestions


def create_error_context(
    component: str,
    operation: str,
    url: str = None,
    source_type: str = None,
    **kwargs
) -> ErrorContext:
    """Create error context with common parameters."""
    return ErrorContext(
        component=component,
        operation=operation,
        url=url,
        source_type=source_type,
        additional_data=kwargs
    )


def handle_exception(
    exception: Exception,
    logger: logging.Logger,
    context: ErrorContext = None,
    reraise: bool = True
) -> Optional[AtlasException]:
    """
    Handle and log exceptions consistently.

    Args:
        exception: The exception to handle
        logger: Logger instance for logging
        context: Error context information
        reraise: Whether to reraise the exception

    Returns:
        AtlasException if conversion occurred, None otherwise
    """
    # Convert to AtlasException if needed
    if not isinstance(exception, AtlasException):
        atlas_exception = AtlasException(
            message=str(exception),
            context=context,
            cause=exception
        )
    else:
        atlas_exception = exception

    # Log the error
    logger.error(
        f"Exception in {context.component if context else 'unknown'}: {atlas_exception.message}",
        extra={
            "error_code": atlas_exception.error_code,
            "context": atlas_exception.to_dict(),
            "exception": atlas_exception
        },
        exc_info=True
    )

    if reraise:
        raise atlas_exception

    return atlas_exception


def log_error_details(
    error: AtlasException,
    logger: logging.Logger,
    include_traceback: bool = True
):
    """Log detailed error information."""
    logger.error(
        f"Error Details: {error.error_code}",
        extra={
            "error_code": error.error_code,
            "error_details": error.to_dict(),
            "recovery_suggestions": error.recovery_suggestions
        },
        exc_info=include_traceback
    )


# Exception mapping for common error types
EXCEPTION_MAPPING = {
    "PermissionError": StorageError,
    "FileNotFoundError": StorageError,
    "sqlite3.Error": DatabaseError,
    "requests.RequestException": IngestionError,
    "requests.Timeout": TimeoutError,
    "requests.HTTPError": IngestionError,
    "yaml.YAMLError": ConfigurationError,
    "json.JSONDecodeError": ValidationError,
    "ValueError": ValidationError,
    "KeyError": ConfigurationError,
}


def convert_exception(
    exception: Exception,
    default_context: ErrorContext = None
) -> AtlasException:
    """
    Convert standard exceptions to Atlas exceptions.

    Args:
        exception: The exception to convert
        default_context: Default error context

    Returns:
        AtlasException instance
    """
    exception_type = type(exception).__name__

    # Find mapped exception type
    atlas_exception_type = EXCEPTION_MAPPING.get(
        exception_type,
        AtlasException
    )

    # Create context if not provided
    if not default_context:
        default_context = ErrorContext(
            component="unknown",
            operation="unknown"
        )

    # Create Atlas exception
    if atlas_exception_type == AtlasException:
        return AtlasException(
            message=str(exception),
            context=default_context,
            cause=exception
        )
    else:
        return atlas_exception_type(
            message=str(exception),
            context=default_context,
            cause=exception
        )