"""
Atlas Digest - Weekly summaries of ingested content.

Clusters recent content by topic and generates digestible summaries.

Usage:
    from modules.digest import generate_digest

    # Generate weekly digest
    digest = generate_digest(days=7)
    print(digest.markdown)
"""

from .clusterer import cluster_recent_content, TopicCluster
from .summarizer import generate_digest, DigestResult

__all__ = [
    "cluster_recent_content",
    "TopicCluster",
    "generate_digest",
    "DigestResult",
]
