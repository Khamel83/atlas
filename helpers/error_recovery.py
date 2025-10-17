#!/usr/bin/env python3
"""
Error Recovery System - Phase 3.3
Comprehensive error recovery with exponential backoff, circuit breakers, and retry strategies
"""

import time
import logging
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Any, Optional, List, Dict, Union
from dataclasses import dataclass, field
from enum import Enum
import traceback

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerException

class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # seconds
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    jitter: bool = True  # Add randomness to prevent thundering herd
    backoff_multiplier: float = 2.0
    retryable_exceptions: List[type] = field(default_factory=lambda: [
        ConnectionError, TimeoutError, OSError
    ])

@dataclass
class RecoveryAttempt:
    """Single recovery attempt record"""
    timestamp: datetime
    attempt_number: int
    exception_type: str
    exception_message: str
    delay_before_retry: float
    success: bool

class ErrorRecoveryManager:
    """
    Comprehensive error recovery with multiple strategies and circuit breaker integration
    """

    def __init__(self, name: str, base_path: str = "/home/ubuntu/dev/atlas"):
        self.name = name
        self.base_path = Path(base_path)
        self.data_dir = self.base_path / "data" / "error_recovery"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Recovery tracking
        self.recovery_log = self.data_dir / f"{name}_recovery.json"
        self.attempts_history: List[RecoveryAttempt] = []
        self._load_history()

        # Circuit breaker integration
        self.circuit_breaker = None

        # Setup logging
        self.logger = logging.getLogger(f"ErrorRecovery.{name}")

    def _load_history(self):
        """Load recovery attempt history from disk"""
        try:
            if self.recovery_log.exists():
                with open(self.recovery_log, 'r') as f:
                    data = json.load(f)

                    for attempt_data in data.get('attempts', []):
                        attempt = RecoveryAttempt(
                            timestamp=datetime.fromisoformat(attempt_data['timestamp']),
                            attempt_number=attempt_data['attempt_number'],
                            exception_type=attempt_data['exception_type'],
                            exception_message=attempt_data['exception_message'],
                            delay_before_retry=attempt_data['delay_before_retry'],
                            success=attempt_data['success']
                        )
                        self.attempts_history.append(attempt)

        except Exception as e:
            self.logger.warning(f"Failed to load recovery history: {e}")

    def _save_history(self):
        """Save recovery attempt history to disk"""
        try:
            data = {
                'name': self.name,
                'last_updated': datetime.now().isoformat(),
                'attempts': []
            }

            for attempt in self.attempts_history[-100:]:  # Keep last 100 attempts
                data['attempts'].append({
                    'timestamp': attempt.timestamp.isoformat(),
                    'attempt_number': attempt.attempt_number,
                    'exception_type': attempt.exception_type,
                    'exception_message': attempt.exception_message,
                    'delay_before_retry': attempt.delay_before_retry,
                    'success': attempt.success
                })

            with open(self.recovery_log, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Failed to save recovery history: {e}")

    def set_circuit_breaker(self, config: CircuitBreakerConfig = None) -> 'ErrorRecoveryManager':
        """Enable circuit breaker integration"""
        self.circuit_breaker = CircuitBreaker(self.name, config)
        return self

    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay before next retry attempt"""
        if config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * attempt
        elif config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = config.base_delay * self._fibonacci(attempt)
        else:  # EXPONENTIAL_BACKOFF
            delay = config.base_delay * (config.backoff_multiplier ** (attempt - 1))

        # Apply jitter to prevent thundering herd
        if config.jitter:
            jitter_range = delay * 0.1  # ±10% jitter
            delay += random.uniform(-jitter_range, jitter_range)

        # Ensure delay bounds
        return max(0, min(delay, config.max_delay))

    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number for backoff strategy"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    def _is_retryable_exception(self, exception: Exception, config: RetryConfig) -> bool:
        """Check if exception is retryable based on configuration"""
        return any(isinstance(exception, exc_type) for exc_type in config.retryable_exceptions)

    def _record_attempt(self, attempt_number: int, exception: Exception,
                       delay: float, success: bool):
        """Record a recovery attempt"""
        attempt = RecoveryAttempt(
            timestamp=datetime.now(),
            attempt_number=attempt_number,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            delay_before_retry=delay,
            success=success
        )

        self.attempts_history.append(attempt)
        self._save_history()

        if success:
            self.logger.info(f"Recovery attempt {attempt_number} succeeded after {delay:.2f}s delay")
        else:
            self.logger.warning(f"Recovery attempt {attempt_number} failed: {exception}")

    def execute_with_recovery(self, func: Callable, config: RetryConfig = None,
                            *args, **kwargs) -> Any:
        """
        Execute function with comprehensive error recovery

        Args:
            func: Function to execute with recovery
            config: Retry configuration (uses defaults if None)
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result if successful

        Raises:
            Exception: Final exception if all recovery attempts fail
        """
        if config is None:
            config = RetryConfig()

        last_exception = None

        for attempt in range(1, config.max_attempts + 1):
            try:
                # Try with circuit breaker if enabled
                if self.circuit_breaker:
                    result = self.circuit_breaker.call(func, *args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success - record and return
                if last_exception:  # Only record if there was a previous failure
                    self._record_attempt(attempt, last_exception, 0, True)

                return result

            except CircuitBreakerException as e:
                # Circuit breaker is open - don't retry
                self.logger.error(f"Circuit breaker open, aborting recovery: {e}")
                raise

            except Exception as e:
                last_exception = e

                # Check if this is the last attempt
                if attempt >= config.max_attempts:
                    self._record_attempt(attempt, e, 0, False)
                    self.logger.error(f"All {config.max_attempts} recovery attempts failed")
                    raise

                # Check if exception is retryable
                if not self._is_retryable_exception(e, config):
                    self.logger.error(f"Non-retryable exception: {type(e).__name__}")
                    self._record_attempt(attempt, e, 0, False)
                    raise

                # Calculate delay and wait
                delay = self._calculate_delay(attempt, config)
                self._record_attempt(attempt, e, delay, False)

                self.logger.info(f"Attempt {attempt} failed, retrying in {delay:.2f}s...")
                time.sleep(delay)

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        if not self.attempts_history:
            return {
                'name': self.name,
                'total_attempts': 0,
                'success_rate': 0.0,
                'last_attempt': None
            }

        total_attempts = len(self.attempts_history)
        successful_attempts = sum(1 for attempt in self.attempts_history if attempt.success)
        success_rate = (successful_attempts / total_attempts) * 100

        # Recent failure analysis (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_attempts = [a for a in self.attempts_history if a.timestamp > cutoff_time]

        # Most common exception types
        exception_counts = {}
        for attempt in self.attempts_history[-50:]:  # Last 50 attempts
            exc_type = attempt.exception_type
            exception_counts[exc_type] = exception_counts.get(exc_type, 0) + 1

        return {
            'name': self.name,
            'total_attempts': total_attempts,
            'successful_attempts': successful_attempts,
            'failed_attempts': total_attempts - successful_attempts,
            'success_rate': round(success_rate, 2),
            'recent_attempts_24h': len(recent_attempts),
            'last_attempt': {
                'timestamp': self.attempts_history[-1].timestamp.isoformat(),
                'success': self.attempts_history[-1].success,
                'exception_type': self.attempts_history[-1].exception_type
            } if self.attempts_history else None,
            'common_exceptions': dict(sorted(exception_counts.items(),
                                           key=lambda x: x[1], reverse=True)[:5]),
            'circuit_breaker_metrics': self.circuit_breaker.get_metrics() if self.circuit_breaker else None
        }

    def clear_history(self):
        """Clear recovery attempt history"""
        self.attempts_history.clear()
        if self.recovery_log.exists():
            self.recovery_log.unlink()
        self.logger.info(f"Recovery history cleared for {self.name}")

# Decorator for easy function decoration
def with_error_recovery(name: str, config: RetryConfig = None,
                       circuit_breaker_config: CircuitBreakerConfig = None):
    """
    Decorator for applying error recovery to functions

    Usage:
        @with_error_recovery("api_calls", RetryConfig(max_attempts=5))
        def call_external_api():
            # API call logic that might fail
            pass
    """
    recovery_manager = ErrorRecoveryManager(name)

    if circuit_breaker_config:
        recovery_manager.set_circuit_breaker(circuit_breaker_config)

    def decorator(func):
        def wrapper(*args, **kwargs):
            return recovery_manager.execute_with_recovery(func, config, *args, **kwargs)

        # Attach recovery manager for access to stats
        wrapper.recovery_manager = recovery_manager
        return wrapper

    return decorator

# Predefined configurations for common scenarios
class RecoveryConfigs:
    """Common recovery configurations"""

    # Quick operations (API calls, database queries)
    QUICK_OPERATIONS = RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )

    # Network operations (file downloads, external services)
    NETWORK_OPERATIONS = RetryConfig(
        max_attempts=5,
        base_delay=2.0,
        max_delay=60.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions=[ConnectionError, TimeoutError, OSError]
    )

    # Heavy operations (large file processing, transcription)
    HEAVY_OPERATIONS = RetryConfig(
        max_attempts=3,
        base_delay=5.0,
        max_delay=300.0,
        strategy=RetryStrategy.LINEAR_BACKOFF
    )

    # Critical operations (database writes, essential services)
    CRITICAL_OPERATIONS = RetryConfig(
        max_attempts=7,
        base_delay=1.0,
        max_delay=120.0,
        strategy=RetryStrategy.FIBONACCI_BACKOFF
    )