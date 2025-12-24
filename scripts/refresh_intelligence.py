#!/usr/bin/env python3
"""
Pre-compute intelligence layer data for fast serving.

Runs hourly to generate:
- Topic map
- Trending topics
- Source statistics
- Sample quotes by topic

Results cached to JSON files served by the API.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/intelligence_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_source_stats():
    """Get content distribution by source."""
    import sqlite3

    db_path = Path("data/indexes/atlas_vectors.db")
    if not db_path.exists():
        return {}

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("""
            SELECT content_id, COUNT(*) as chunks
            FROM chunks
            GROUP BY content_id
        """).fetchall()

    # Infer sources from content_ids
    source_counts = Counter()
    for content_id, chunks in rows:
        cid = content_id.lower()
        if cid.startswith("podcast:stratechery"):
            source = "Stratechery Podcast"
        elif cid.startswith("stratechery:"):
            source = "Stratechery Articles"
        elif cid.startswith("podcast:acquired"):
            source = "Acquired"
        elif cid.startswith("podcast:hard-fork"):
            source = "Hard Fork"
        elif cid.startswith("podcast:ezra") or "ezra-klein" in cid:
            source = "Ezra Klein"
        elif cid.startswith("podcast:lex"):
            source = "Lex Fridman"
        elif cid.startswith("podcast:dwarkesh"):
            source = "Dwarkesh Patel"
        elif cid.startswith("podcast:conversation"):
            source = "Conversations with Tyler"
        elif cid.startswith("podcast:planet-money"):
            source = "Planet Money"
        elif cid.startswith("podcast:"):
            source = "Other Podcasts"
        elif cid.startswith("article:"):
            source = "Articles"
        elif cid.startswith("newsletter:"):
            source = "Newsletters"
        else:
            source = "Other"

        source_counts[source] += chunks

    return dict(source_counts.most_common(20))


def get_topic_keywords():
    """Extract trending topics from recent content."""
    import sqlite3
    import re

    db_path = Path("data/indexes/atlas_vectors.db")
    if not db_path.exists():
        return []

    # Get recent content titles
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("""
            SELECT DISTINCT content_id, metadata
            FROM chunks
            ORDER BY rowid DESC
            LIMIT 5000
        """).fetchall()

    # Extract keywords from metadata
    topic_keywords = [
        "ai", "artificial intelligence", "machine learning", "llm", "gpt", "claude", "openai",
        "apple", "google", "microsoft", "meta", "amazon", "nvidia", "tesla",
        "startup", "venture", "vc", "funding", "ipo",
        "crypto", "bitcoin", "blockchain",
        "china", "regulation", "antitrust",
        "climate", "energy",
        "healthcare", "biotech",
    ]

    keyword_counts = Counter()
    for content_id, metadata_str in rows:
        try:
            metadata = json.loads(metadata_str) if metadata_str else {}
            title = metadata.get("title", content_id).lower()

            for kw in topic_keywords:
                if kw in title:
                    keyword_counts[kw] += 1
        except:
            continue

    return [{"topic": k, "count": v} for k, v in keyword_counts.most_common(15)]


def get_overall_stats():
    """Get overall database stats."""
    import sqlite3

    db_path = Path("data/indexes/atlas_vectors.db")
    if not db_path.exists():
        return {}

    with sqlite3.connect(db_path) as conn:
        total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        unique_content = conn.execute("SELECT COUNT(DISTINCT content_id) FROM chunks").fetchone()[0]

    return {
        "total_chunks": total_chunks,
        "unique_content": unique_content,
    }


def main():
    logger.info("Refreshing intelligence cache...")

    # Gather all stats
    stats = get_overall_stats()
    sources = get_source_stats()
    topics = get_topic_keywords()

    cache_data = {
        "generated_at": datetime.now().isoformat(),
        "stats": stats,
        "sources": sources,
        "trending_topics": topics,
    }

    # Write cache
    cache_file = CACHE_DIR / "intelligence.json"
    with open(cache_file, "w") as f:
        json.dump(cache_data, f, indent=2)

    logger.info(f"Cache written to {cache_file}")
    logger.info(f"  Total chunks: {stats.get('total_chunks', 0):,}")
    logger.info(f"  Unique content: {stats.get('unique_content', 0):,}")
    logger.info(f"  Sources: {len(sources)}")
    logger.info(f"  Topics: {len(topics)}")


if __name__ == "__main__":
    main()
