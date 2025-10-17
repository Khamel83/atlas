#!/usr/bin/env python3
"""
Circuit Breaker Pattern Implementation - Phase 3.3
Provides resilient failure handling for Atlas services with configurable thresholds
"""

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta
import threading
import json
from pathlib import Path

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests due to failures
    HALF_OPEN = "half_open"  # Testing if service has recovered

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: int = 60          # Seconds before attempting recovery
    success_threshold: int = 3          # Successes needed to close from half-open
    timeout: int = 30                   # Request timeout in seconds

@dataclass
class CircuitMetrics:
    """Circuit breaker metrics tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[datetime] = None
    state_change_time: datetime = field(default_factory=datetime.now)

class CircuitBreakerException(Exception):
    """Circuit breaker specific exception"""
    pass

class CircuitBreaker:
    """
    Circuit breaker implementation for resilient service calls

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail fast
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self.lock = threading.RLock()

        # Setup logging
        self.logger = logging.getLogger(f"CircuitBreaker.{name}")

        # State persistence
        self.state_file = Path(f"/home/ubuntu/dev/atlas/data/circuit_breaker_{name}.json")
        self.state_file.parent.mkdir(exist_ok=True)
        self._load_state()

    def _load_state(self):
        """Load circuit breaker state from disk"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)

                    # Restore state
                    self.state = CircuitState(data.get('state', 'closed'))

                    # Restore metrics
                    metrics_data = data.get('metrics', {})
                    self.metrics.total_requests = metrics_data.get('total_requests', 0)
                    self.metrics.successful_requests = metrics_data.get('successful_requests', 0)
                    self.metrics.failed_requests = metrics_data.get('failed_requests', 0)
                    self.metrics.consecutive_failures = metrics_data.get('consecutive_failures', 0)
                    self.metrics.consecutive_successes = metrics_data.get('consecutive_successes', 0)

                    # Restore timestamps
                    if metrics_data.get('last_failure_time'):
                        self.metrics.last_failure_time = datetime.fromisoformat(metrics_data['last_failure_time'])
                    if data.get('state_change_time'):
                        self.metrics.state_change_time = datetime.fromisoformat(data['state_change_time'])

        except Exception as e:
            self.logger.warning(f"Failed to load circuit breaker state: {e}")

    def _save_state(self):
        """Save circuit breaker state to disk"""
        try:
            data = {
                'state': self.state.value,
                'state_change_time': self.metrics.state_change_time.isoformat(),
                'metrics': {
                    'total_requests': self.metrics.total_requests,
                    'successful_requests': self.metrics.successful_requests,
                    'failed_requests': self.metrics.failed_requests,
                    'consecutive_failures': self.metrics.consecutive_failures,
                    'consecutive_successes': self.metrics.consecutive_successes,
                    'last_failure_time': self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None
                }
            }

            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Failed to save circuit breaker state: {e}")

    def _can_attempt_request(self) -> bool:
        """Check if a request can be attempted based on current state"""
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self.metrics.last_failure_time:
                    time_since_failure = datetime.now() - self.metrics.last_failure_time
                    if time_since_failure.total_seconds() >= self.config.recovery_timeout:
                        self._transition_to_half_open()
                        return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                return True

            return False

    def _transition_to_half_open(self):
        """Transition to half-open state"""
        self.logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.metrics.state_change_time = datetime.now()
        self.metrics.consecutive_successes = 0
        self._save_state()

    def _transition_to_open(self):
        """Transition to open state"""
        self.logger.warning(f"Circuit breaker {self.name} OPEN - too many failures")
        self.state = CircuitState.OPEN
        self.metrics.state_change_time = datetime.now()
        self.metrics.last_failure_time = datetime.now()
        self._save_state()

    def _transition_to_closed(self):
        """Transition to closed state"""
        self.logger.info(f"Circuit breaker {self.name} CLOSED - service recovered")
        self.state = CircuitState.CLOSED
        self.metrics.state_change_time = datetime.now()
        self.metrics.consecutive_failures = 0
        self._save_state()

    def _record_success(self):
        """Record a successful request"""
        with self.lock:
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.consecutive_failures = 0
            self.metrics.consecutive_successes += 1

            # Check for state transitions
            if self.state == CircuitState.HALF_OPEN:
                if self.metrics.consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()

            self._save_state()

    def _record_failure(self, error: Exception):
        """Record a failed request"""
        with self.lock:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.consecutive_failures += 1
            self.metrics.consecutive_successes = 0
            self.metrics.last_failure_time = datetime.now()

            self.logger.warning(f"Circuit breaker {self.name} recorded failure: {error}")

            # Check for state transitions
            if self.state == CircuitState.CLOSED:
                if self.metrics.consecutive_failures >= self.config.failure_threshold:
                    self._transition_to_open()
            elif self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()

            self._save_state()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerException: When circuit is open
            Exception: Original function exceptions when circuit allows
        """
        if not self._can_attempt_request():
            raise CircuitBreakerException(
                f"Circuit breaker {self.name} is OPEN - requests blocked until recovery"
            )

        try:
            # Execute with timeout
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Check for timeout
            if execution_time > self.config.timeout:
                raise TimeoutError(f"Function execution exceeded {self.config.timeout}s timeout")

            self._record_success()
            return result

        except Exception as e:
            self._record_failure(e)
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get current circuit breaker metrics"""
        with self.lock:
            success_rate = 0.0
            if self.metrics.total_requests > 0:
                success_rate = (self.metrics.successful_requests / self.metrics.total_requests) * 100

            return {
                'name': self.name,
                'state': self.state.value,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'recovery_timeout': self.config.recovery_timeout,
                    'success_threshold': self.config.success_threshold,
                    'timeout': self.config.timeout
                },
                'metrics': {
                    'total_requests': self.metrics.total_requests,
                    'successful_requests': self.metrics.successful_requests,
                    'failed_requests': self.metrics.failed_requests,
                    'success_rate': round(success_rate, 2),
                    'consecutive_failures': self.metrics.consecutive_failures,
                    'consecutive_successes': self.metrics.consecutive_successes,
                    'last_failure_time': self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                    'state_change_time': self.metrics.state_change_time.isoformat()
                }
            }

    def reset(self):
        """Reset circuit breaker to initial state"""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.metrics = CircuitMetrics()
            self._save_state()
            self.logger.info(f"Circuit breaker {self.name} reset")

    def force_open(self):
        """Force circuit breaker to open state (for testing/maintenance)"""
        with self.lock:
            self._transition_to_open()
            self.logger.warning(f"Circuit breaker {self.name} forced OPEN")

    def force_closed(self):
        """Force circuit breaker to closed state (for recovery)"""
        with self.lock:
            self._transition_to_closed()
            self.logger.info(f"Circuit breaker {self.name} forced CLOSED")

# Context manager support
class CircuitBreakerContext:
    """Context manager for circuit breaker usage"""

    def __init__(self, circuit_breaker: CircuitBreaker):
        self.circuit_breaker = circuit_breaker

    def __enter__(self):
        if not self.circuit_breaker._can_attempt_request():
            raise CircuitBreakerException(
                f"Circuit breaker {self.circuit_breaker.name} is OPEN"
            )
        return self.circuit_breaker

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.circuit_breaker._record_success()
        else:
            self.circuit_breaker._record_failure(exc_val)
        return False  # Don't suppress exceptions

def circuit_breaker_decorator(name: str, config: CircuitBreakerConfig = None):
    """
    Decorator for applying circuit breaker pattern to functions

    Usage:
        @circuit_breaker_decorator("api_service")
        def call_api():
            # API call logic
            pass
    """
    breaker = CircuitBreaker(name, config)

    def decorator(func):
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator