"""
Generate digest summaries from clustered content.

Uses LLM to create readable summaries for each topic cluster.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime

import requests

from modules.ask.config import get_config
from .clusterer import TopicCluster, cluster_recent_content

logger = logging.getLogger(__name__)


@dataclass
class ClusterSummary:
    """Summary for a single topic cluster."""
    topic: str
    summary: str
    items: List[str]  # List of content titles
    keywords: List[str]


@dataclass
class DigestResult:
    """Complete digest with all summaries."""
    date: datetime
    period_days: int
    clusters: List[ClusterSummary]
    total_items: int
    tokens_used: int

    @property
    def markdown(self) -> str:
        """Generate markdown output."""
        lines = [
            f"# Weekly Digest",
            f"",
            f"**Period**: Last {self.period_days} days",
            f"**Generated**: {self.date.strftime('%Y-%m-%d %H:%M')}",
            f"**Total items**: {self.total_items}",
            f"",
        ]

        for i, cluster in enumerate(self.clusters, 1):
            lines.extend([
                f"## {i}. {cluster.topic}",
                f"",
                cluster.summary,
                f"",
                f"**Content included:**",
            ])

            for item in cluster.items[:5]:
                lines.append(f"- {item}")

            if len(cluster.items) > 5:
                lines.append(f"- ...and {len(cluster.items) - 5} more")

            if cluster.keywords:
                lines.append(f"")
                lines.append(f"*Keywords: {', '.join(cluster.keywords)}*")

            lines.append("")

        return "\n".join(lines)


def generate_digest(
    days: int = 7,
    min_clusters: int = 3,
    max_clusters: int = 8,
) -> DigestResult:
    """
    Generate a digest of recent content.

    Args:
        days: Look back this many days
        min_clusters: Minimum topic clusters
        max_clusters: Maximum topic clusters

    Returns:
        DigestResult with summaries
    """
    # Step 1: Cluster recent content
    clusters = cluster_recent_content(
        days=days,
        min_clusters=min_clusters,
        max_clusters=max_clusters,
    )

    if not clusters:
        return DigestResult(
            date=datetime.now(),
            period_days=days,
            clusters=[],
            total_items=0,
            tokens_used=0,
        )

    # Step 2: Generate summary for each cluster
    summaries = []
    total_tokens = 0

    for cluster in clusters:
        summary, tokens = _summarize_cluster(cluster)
        total_tokens += tokens

        summaries.append(ClusterSummary(
            topic=cluster.label,
            summary=summary,
            items=[item.title for item in cluster.items],
            keywords=cluster.keywords,
        ))

    # Count total items
    total_items = sum(len(c.items) for c in clusters)

    return DigestResult(
        date=datetime.now(),
        period_days=days,
        clusters=summaries,
        total_items=total_items,
        tokens_used=total_tokens,
    )


def _summarize_cluster(cluster: TopicCluster) -> tuple[str, int]:
    """Generate summary for a single cluster using LLM."""
    config = get_config()

    if not config.api_key:
        # Fallback to simple summary
        titles = [item.title for item in cluster.items[:5]]
        return f"Collection of {len(cluster.items)} items including: {', '.join(titles)}", 0

    # Build context from cluster items
    items_text = []
    for item in cluster.items[:10]:  # Limit to 10 items
        items_text.append(f"- {item.title} ({item.source_type})")

    context = "\n".join(items_text)

    prompt = f"""Summarize this collection of content in 2-3 sentences.
Focus on the common themes and key insights.

Content in this cluster:
{context}

Write a concise summary that captures what this content is about:"""

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/atlas",
        "X-Title": "Atlas Digest",
    }

    payload = {
        "model": config.llm.model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 200,
        "temperature": 0.3,
    }

    try:
        response = requests.post(
            f"{config.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        summary = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)

        return summary, tokens

    except requests.RequestException as e:
        logger.error(f"Summarization failed: {e}")
        # Fallback
        titles = [item.title for item in cluster.items[:3]]
        return f"Topics covered: {', '.join(titles)}", 0


def save_digest(digest: DigestResult, output_dir: str = "data/digests") -> str:
    """Save digest to file."""
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = f"{digest.date.strftime('%Y-%m-%d')}.md"
    filepath = output_path / filename

    filepath.write_text(digest.markdown)

    logger.info(f"Saved digest to {filepath}")
    return str(filepath)
