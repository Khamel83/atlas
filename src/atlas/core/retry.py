"""
Retry mechanism with exponential backoff for Atlas v4.

Provides robust retry functionality for failed operations with
configurable backoff strategies and jitter support.
"""

import time
import random
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Dict, Union
from dataclasses import dataclass, field
from enum import Enum


class BackoffStrategy(Enum):
    """Backoff strategies for retry attempts."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: bool = True
    jitter_factor: float = 0.1
    retry_on: tuple = (Exception,)  # Exception types to retry on
    retryable_status_codes: tuple = ()  # HTTP status codes to retry on


@dataclass
class RetryAttempt:
    """Information about a single retry attempt."""
    attempt_number: int
    timestamp: datetime
    delay: float
    error: Optional[Exception] = None
    success: bool = False


@dataclass
class RetryResult:
    """Result of a retry operation."""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    total_attempts: int = 0
    total_duration: float = 0.0
    attempts: list = field(default_factory=list)


class RetryableError(Exception):
    """Base class for errors that should be retried."""
    pass


class TemporaryError(RetryableError):
    """Temporary error that might resolve on retry."""
    pass


class RateLimitError(RetryableError):
    """Rate limiting error that requires backoff."""
    pass


class NetworkError(RetryableError):
    """Network-related error that might resolve on retry."""
    pass


class RetryHandler:
    """
    Handles retry logic with various backoff strategies.

    Features:
    - Multiple backoff strategies (exponential, linear, fixed, fibonacci)
    - Jitter to prevent thundering herd
    - Configurable retry conditions
    - Detailed attempt tracking
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry handler.

        Args:
            config: Retry configuration (uses default if None)
        """
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(f"atlas.core.{self.__class__.__name__}")

    def execute(
        self,
        func: Callable,
        *args,
        config: Optional[RetryConfig] = None,
        **kwargs
    ) -> RetryResult:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            config: Override retry config for this execution
            **kwargs: Function keyword arguments

        Returns:
            RetryResult with execution details
        """
        retry_config = config or self.config
        start_time = time.time()
        attempts = []

        for attempt in range(1, retry_config.max_attempts + 1):
            attempt_start = time.time()

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Create successful attempt record
                attempt_duration = time.time() - attempt_start
                attempt_record = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now(),
                    delay=0.0,
                    success=True
                )
                attempts.append(attempt_record)

                total_duration = time.time() - start_time

                self.logger.debug(
                    f"Operation succeeded on attempt {attempt}",
                    duration=attempt_duration,
                    total_duration=total_duration
                )

                return RetryResult(
                    success=True,
                    result=result,
                    total_attempts=attempt,
                    total_duration=total_duration,
                    attempts=attempts
                )

            except Exception as e:
                attempt_duration = time.time() - attempt_start

                # Check if error is retryable
                if not self._is_retryable_error(e, retry_config):
                    self.logger.warning(
                        f"Non-retryable error on attempt {attempt}",
                        error=str(e),
                        error_type=type(e).__name__
                    )

                    attempts.append(RetryAttempt(
                        attempt_number=attempt,
                        timestamp=datetime.now(),
                        delay=0.0,
                        error=e,
                        success=False
                    ))

                    total_duration = time.time() - start_time

                    return RetryResult(
                        success=False,
                        error=e,
                        total_attempts=attempt,
                        total_duration=total_duration,
                        attempts=attempts
                    )

                # Create failed attempt record
                attempt_record = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now(),
                    delay=0.0,
                    error=e,
                    success=False
                )
                attempts.append(attempt_record)

                # Check if this was the last attempt
                if attempt == retry_config.max_attempts:
                    self.logger.error(
                        f"Operation failed after {attempt} attempts",
                        final_error=str(e),
                        total_duration=time.time() - start_time
                    )

                    total_duration = time.time() - start_time

                    return RetryResult(
                        success=False,
                        error=e,
                        total_attempts=attempt,
                        total_duration=total_duration,
                        attempts=attempts
                    )

                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, retry_config)

                self.logger.warning(
                    f"Attempt {attempt} failed, retrying in {delay:.2f}s",
                    error=str(e),
                    error_type=type(e).__name__,
                    next_attempt=attempt + 1
                )

                # Update attempt record with delay
                attempt_record.delay = delay

                # Wait before next attempt
                time.sleep(delay)

    def _is_retryable_error(self, error: Exception, config: RetryConfig) -> bool:
        """Check if error should be retried."""
        # Check exception type
        for retryable_type in config.retry_on:
            if isinstance(error, retryable_type):
                return True

        # Check HTTP status codes for requests exceptions
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            if error.response.status_code in config.retryable_status_codes:
                return True

        # Check for specific error patterns
        error_message = str(error).lower()

        # Network-related errors
        network_indicators = [
            'connection', 'timeout', 'network', 'dns', 'socket',
            'temporary failure', 'service unavailable'
        ]

        for indicator in network_indicators:
            if indicator in error_message:
                return True

        return False

    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay before next attempt."""
        if config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = config.base_delay * (2 ** (attempt - 1))
        elif config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = config.base_delay * attempt
        elif config.backoff_strategy == BackoffStrategy.FIXED:
            delay = config.base_delay
        elif config.backoff_strategy == BackoffStrategy.FIBONACCI:
            delay = config.base_delay * self._fibonacci(attempt)
        else:
            delay = config.base_delay

        # Apply max delay limit
        delay = min(delay, config.max_delay)

        # Add jitter if enabled
        if config.jitter:
            jitter_amount = delay * config.jitter_factor
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)

        return delay

    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 1:
            return n

        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b

        return b

    def get_retry_stats(self) -> Dict[str, Any]:
        """Get statistics about retry operations."""
        # This would be implemented with persistent storage in a real system
        return {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "average_attempts": 0.0,
            "average_delay": 0.0
        }


# Convenience decorators
def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    jitter: bool = True,
    retry_on: tuple = (Exception,)
):
    """
    Decorator for adding retry functionality to functions.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between attempts
        max_delay: Maximum delay between attempts
        backoff_strategy: Strategy for calculating delays
        jitter: Whether to add jitter to delays
        retry_on: Exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_strategy=backoff_strategy,
                jitter=jitter,
                retry_on=retry_on
            )

            retry_handler = RetryHandler(config)
            result = retry_handler.execute(func, *args, **kwargs)

            if result.success:
                return result.result
            else:
                raise result.error

        return wrapper
    return decorator


# Default retry handler instance
default_retry_handler = RetryHandler()


def execute_with_retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    **kwargs
) -> Any:
    """
    Execute function with default retry configuration.

    Args:
        func: Function to execute
        *args: Function arguments
        max_attempts: Maximum retry attempts
        base_delay: Base delay between attempts
        **kwargs: Function keyword arguments

    Returns:
        Function result if successful

    Raises:
        Last exception if all attempts fail
    """
    config = RetryConfig(max_attempts=max_attempts, base_delay=base_delay)
    retry_handler = RetryHandler(config)
    result = retry_handler.execute(func, *args, **kwargs)

    if result.success:
        return result.result
    else:
        raise result.error