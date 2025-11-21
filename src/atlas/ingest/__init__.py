"""
Ingestion modules for Atlas v4.

Independent content processors:
- Gmail IMAP ingestion
- RSS feed ingestion
- YouTube content ingestion

Each ingestor is a standalone tool that can run independently.
"""

from .base import BaseIngestor

__all__ = [
    "BaseIngestor",
]