"""
Cluster recent content by topic.

Uses embeddings similarity to group related content.
Simple k-means clustering via scikit-learn.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import sqlite3
import json

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ContentItem:
    """A piece of content for clustering."""
    content_id: str
    title: str
    source_type: str  # podcast, article, newsletter, etc.
    date: Optional[datetime] = None
    preview: str = ""
    embedding: Optional[List[float]] = None


@dataclass
class TopicCluster:
    """A cluster of related content items."""
    id: int
    label: str  # LLM-generated label
    items: List[ContentItem] = field(default_factory=list)
    centroid: Optional[List[float]] = None
    keywords: List[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.items)


def cluster_recent_content(
    days: int = 7,
    min_clusters: int = 3,
    max_clusters: int = 8,
    db_path: str = "data/indexes/atlas_vectors.db",
) -> List[TopicCluster]:
    """
    Cluster content ingested in the last N days.

    Args:
        days: Look back this many days
        min_clusters: Minimum number of clusters
        max_clusters: Maximum number of clusters
        db_path: Path to vector database

    Returns:
        List of TopicCluster with labeled groups
    """
    # Get recent content with embeddings
    items = _get_recent_content(days, db_path)

    if len(items) < min_clusters:
        logger.warning(f"Only {len(items)} items, not enough to cluster")
        # Return single cluster with all items
        if items:
            return [TopicCluster(id=0, label="Recent Content", items=items)]
        return []

    # Extract embeddings
    embeddings = np.array([item.embedding for item in items if item.embedding])

    if len(embeddings) < min_clusters:
        logger.warning("Not enough items with embeddings")
        return [TopicCluster(id=0, label="Recent Content", items=items)]

    # Determine optimal number of clusters
    n_clusters = min(max_clusters, max(min_clusters, len(items) // 5))

    # Cluster using k-means
    clusters = _kmeans_cluster(items, embeddings, n_clusters)

    # Label clusters using keywords
    for cluster in clusters:
        cluster.label = _generate_label(cluster)
        cluster.keywords = _extract_keywords(cluster)

    return clusters


def _get_recent_content(days: int, db_path: str) -> List[ContentItem]:
    """Get content from the last N days with embeddings."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Calculate cutoff date
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    # Get unique content IDs with their first chunk's embedding
    # Using a subquery to get one chunk per content
    cursor.execute("""
        SELECT DISTINCT
            c.content_id,
            c.metadata,
            c.embedding
        FROM chunks c
        WHERE c.chunk_index = 0
        ORDER BY c.content_id
        LIMIT 500
    """)

    items = []
    for row in cursor.fetchall():
        content_id, metadata_str, embedding_blob = row

        metadata = json.loads(metadata_str) if metadata_str else {}

        # Parse date if available
        date = None
        if "date" in metadata:
            try:
                date = datetime.fromisoformat(metadata["date"])
            except (ValueError, TypeError):
                pass

        # Extract embedding
        embedding = None
        if embedding_blob:
            try:
                embedding = list(np.frombuffer(embedding_blob, dtype=np.float32))
            except Exception:
                pass

        items.append(ContentItem(
            content_id=content_id,
            title=metadata.get("title", content_id),
            source_type=metadata.get("source", "unknown"),
            date=date,
            preview=metadata.get("preview", "")[:200],
            embedding=embedding,
        ))

    conn.close()

    logger.info(f"Found {len(items)} content items for clustering")
    return items


def _kmeans_cluster(
    items: List[ContentItem],
    embeddings: np.ndarray,
    n_clusters: int,
) -> List[TopicCluster]:
    """Run k-means clustering."""
    try:
        from sklearn.cluster import KMeans
    except ImportError:
        logger.error("scikit-learn not installed. Run: pip install scikit-learn")
        return [TopicCluster(id=0, label="All Content", items=items)]

    # Fit k-means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    # Group items by cluster
    clusters: Dict[int, TopicCluster] = {}

    for i, (item, label) in enumerate(zip(items, labels)):
        if label not in clusters:
            clusters[label] = TopicCluster(
                id=label,
                label=f"Topic {label}",
                centroid=kmeans.cluster_centers_[label].tolist(),
            )
        clusters[label].items.append(item)

    return list(clusters.values())


def _generate_label(cluster: TopicCluster) -> str:
    """Generate a label for the cluster from its content."""
    # Simple approach: use most common title words
    words = []
    for item in cluster.items[:5]:
        words.extend(item.title.lower().split())

    # Remove common words
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "that", "this", "these",
        "those", "it", "its", "what", "how", "why", "when", "where", "who",
        "-", "–", "|", "ep.", "episode", "part", "#",
    }

    word_counts: Dict[str, int] = {}
    for word in words:
        word = word.strip(".,!?:;\"'()[]")
        if word and len(word) > 2 and word not in stopwords:
            word_counts[word] = word_counts.get(word, 0) + 1

    # Get top words
    top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    if top_words:
        return " & ".join(w.title() for w, _ in top_words)

    return f"Topic {cluster.id}"


def _extract_keywords(cluster: TopicCluster) -> List[str]:
    """Extract keywords from cluster content."""
    words = []
    for item in cluster.items:
        words.extend(item.title.lower().split())

    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were",
    }

    word_counts: Dict[str, int] = {}
    for word in words:
        word = word.strip(".,!?:;\"'()[]")
        if word and len(word) > 2 and word not in stopwords:
            word_counts[word] = word_counts.get(word, 0) + 1

    top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return [w for w, _ in top_words]
