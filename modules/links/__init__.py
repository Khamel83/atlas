"""
Atlas Link Discovery & Ingestion Pipeline.

Unified system for extracting, scoring, approving, and ingesting URLs
from any text source (transcripts, show notes, articles, newsletters).

Usage:
    from modules.links import extract_links, approve_links, bridge_to_queue

    # Extract links from any text
    links = extract_links(text, source_type='transcript', content_id='podcast:acquired:ep-1')

    # Run approval workflow
    approved, rejected = approve_links()

    # Bridge approved links to ingestion queue
    count = bridge_to_queue(limit=50)
"""

from modules.links.extractor import extract_links, LinkExtractor
from modules.links.approval import approve_links, ApprovalEngine
from modules.links.bridge import bridge_to_queue, LinkBridge
from modules.links.models import Link, LinkSource, ApprovalResult

__all__ = [
    'extract_links',
    'approve_links',
    'bridge_to_queue',
    'LinkExtractor',
    'ApprovalEngine',
    'LinkBridge',
    'Link',
    'LinkSource',
    'ApprovalResult',
]
