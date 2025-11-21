"""
Retry and error handling for Atlas v4.

Failure classification and retry logic:
- Error taxonomy (transient, structural, permanent, incomplete)
- Exponential backoff retry
- Dead letter queue management
"""

from .classifier import classify_error
from .engine import retry_with_backoff

__all__ = [
    "classify_error",
    "retry_with_backoff",
]