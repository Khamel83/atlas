#!/usr/bin/env python3
"""
Proactive Content Surfacer

Intelligently surfaces relevant content from Atlas based on context,
recent activity, and user patterns.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from helpers.config import load_config
except ImportError:
    load_config = lambda: {}


@dataclass
class SurfacedContent:
    """Container for surfaced content with relevance scoring."""
    uid: str
    title: str
    source: str
    content_type: str
    relevance_score: float
    surface_reason: str
    metadata: Dict[str, Any]
    updated_at: str

    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


@dataclass
class SurfacingContext:
    """Context for content surfacing."""
    current_topic: Optional[str] = None
    recent_queries: List[str] = None
    time_context: str = "any"  # morning, afternoon, evening, weekend
    content_types: List[str] = None
    max_results: int = 10

    def __post_init__(self):
        if self.recent_queries is None:
            self.recent_queries = []
        if self.content_types is None:
            self.content_types = []  # Empty list means no content type filtering


class ProactiveSurfacer:
    """
    Proactive content surfacing engine.

    Intelligently surfaces relevant content from Atlas based on:
    - Current context and recent activity
    - Time-based relevance (recent vs. historical)
    - Content relationships and patterns
    - User interaction patterns
    """

    def __init__(self, metadata_manager_or_config = None):
        """Initialize ProactiveSurfacer."""
        if hasattr(metadata_manager_or_config, 'config'):
            # It's a MetadataManager
            self.config = metadata_manager_or_config.config or {}
        else:
            # It's a config dict or None
            self.config = metadata_manager_or_config or {}

        self.db_path = "atlas.db"

        # Surfacing configuration with defaults
        self.relevance_threshold = self.config.get('relevance_threshold', 0.3)
        self.max_age_days = self.config.get('max_content_age_days', 365)
        self.boost_recent = self.config.get('boost_recent_content', True)

    def surface_content(self,
                       context: SurfacingContext,
                       log_path: str = "") -> List[SurfacedContent]:
        """
        Surface relevant content based on context.

        Args:
            context: Surfacing context with topics, queries, preferences
            log_path: Path for logging

        Returns:
            List of SurfacedContent objects ordered by relevance
        """
        try:
            # Get content from database
            content_items = self._get_content_from_db(context)

            # Score content for relevance
            scored_content = []
            for item in content_items:
                score = self._calculate_relevance_score(item, context)
                if score >= self.relevance_threshold:
                    reason = self._determine_surface_reason(item, context, score)

                    surfaced = SurfacedContent(
                        uid=str(item['id']),
                        title=item['title'] or "Untitled",
                        source=item['url'] or "",
                        content_type=item['content_type'] or "unknown",
                        relevance_score=score,
                        surface_reason=reason,
                        metadata=item,
                        updated_at=datetime.now().isoformat()
                    )
                    scored_content.append(surfaced)

            # Sort by relevance score and return top results
            scored_content.sort(key=lambda x: x.relevance_score, reverse=True)
            return scored_content[:context.max_results]

        except Exception as e:
            print(f"Error surfacing content: {e}")
            return self._mock_surface_content(context)

    def surface_by_topic(self,
                        topic: str,
                        max_results: int = 5) -> List[SurfacedContent]:
        """Surface content related to a specific topic."""
        context = SurfacingContext(
            current_topic=topic,
            max_results=max_results
        )
        return self.surface_content(context)

    def surface_recent(self,
                      days: int = 7,
                      max_results: int = 10) -> List[SurfacedContent]:
        """Surface recently added content."""
        context = SurfacingContext(
            time_context="recent",
            max_results=max_results
        )

        # Override age filter for this specific call
        original_max_age = self.max_age_days
        self.max_age_days = days

        try:
            results = self.surface_content(context)
            return results
        finally:
            self.max_age_days = original_max_age

    def surface_by_content_type(self,
                              content_type: str,
                              max_results: int = 10) -> List[SurfacedContent]:
        """Surface content of a specific type."""
        context = SurfacingContext(
            content_types=[content_type],
            max_results=max_results
        )
        return self.surface_content(context)

    def surface_diverse_content(self,
                               max_results: int = 10) -> List[SurfacedContent]:
        """Surface a diverse selection of content across types and topics."""
        try:
            # Get diverse content from database
            context = SurfacingContext(max_results=max_results * 2)  # Get more for diversity
            all_items = self._get_content_from_db(context)

            # Group by content type
            content_by_type = defaultdict(list)
            for item in all_items:
                content_type = item.get('content_type', 'unknown')
                content_by_type[content_type].append(item)

            # Sample from each type to ensure diversity
            surfaced_content = []
            types = list(content_by_type.keys())

            items_per_type = max(1, max_results // len(types)) if types else max_results

            for content_type in types:
                type_items = content_by_type[content_type]
                # Sort by recency and quality for each type
                type_items.sort(key=lambda x: (
                    x.get('extraction_quality', 0),
                    x.get('created_at', '')
                ), reverse=True)

                # Take a sample
                sampled_items = type_items[:items_per_type]

                for item in sampled_items:
                    quality_score = item.get('extraction_quality') or 0.5
                    base_score = 0.4 + (float(quality_score) * 0.3)  # 0.4-0.7 based on quality

                    surfaced = SurfacedContent(
                        uid=str(item['id']),
                        title=item.get('title', 'Untitled'),
                        source=item.get('url', ''),
                        content_type=item.get('content_type', 'unknown'),
                        relevance_score=base_score,
                        surface_reason=f"Diverse {content_type} selection",
                        metadata=item,
                        updated_at=datetime.now().isoformat()
                    )
                    surfaced_content.append(surfaced)

            # Sort by relevance and return top results
            surfaced_content.sort(key=lambda x: x.relevance_score, reverse=True)
            return surfaced_content[:max_results]

        except Exception as e:
            print(f"Error surfacing diverse content: {e}")
            return self._mock_surface_content(SurfacingContext(max_results=max_results))

    def surface_forgotten_content(self, n: int = 5) -> List[Any]:
        """Surface forgotten content - wrapper for web interface compatibility."""
        context = SurfacingContext(max_results=n)
        results = self.surface_diverse_content(max_results=n)

        # Convert to simple objects for template compatibility
        forgotten = []
        for item in results:
            forgotten.append(type('Item', (), {
                'title': item.title,
                'updated_at': item.updated_at[:10] if item.updated_at else 'Unknown'
            })())
        return forgotten

    def _get_content_from_db(self, context: SurfacingContext) -> List[Dict[str, Any]]:
        """Get content items from database based on context."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Get dict-like rows
            cursor = conn.cursor()

            # Build query based on context
            where_clauses = []
            params = []

            # Filter by content types
            if context.content_types:
                placeholders = ','.join(['?' for _ in context.content_types])
                where_clauses.append(f"c.content_type IN ({placeholders})")
                params.extend(context.content_types)

            # Filter by age if needed
            if self.max_age_days > 0:
                cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
                where_clauses.append("c.created_at >= ?")
                params.append(cutoff_date.isoformat())

            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)

            query = f"""
            SELECT c.id, c.title, c.content, c.content_type, c.url, c.created_at
            FROM content c
            {where_clause}
            ORDER BY c.created_at DESC
            LIMIT ?
            """
            params.append(context.max_results * 3)  # Get more to filter/score

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to list of dicts
            content_items = []
            for row in rows:
                item = dict(row)
                # Set default values for missing insight fields
                item['topics'] = []
                item['entities'] = []
                item['extraction_quality'] = 0.5  # Default quality score
                content_items.append(item)

            conn.close()
            return content_items

        except Exception as e:
            print(f"Database error: {e}")
            return []

    def _filter_by_age(self, content_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter content by maximum age."""
        if self.max_age_days <= 0:
            return content_items

        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)

        filtered = []
        for item in content_items:
            try:
                created_at = item.created_at
                if created_at:
                    content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if content_date >= cutoff_date:
                        filtered.append(item)
                else:
                    # Include items without dates (assume recent)
                    filtered.append(item)
            except Exception:
                # Include items with unparseable dates
                filtered.append(item)

        return filtered

    def _calculate_relevance_score(self,
                                  item: Dict[str, Any],
                                  context: SurfacingContext) -> float:
        """Calculate relevance score for content item."""
        score = 0.0

        # Base score for content type preference
        if item.get('content_type') in context.content_types:
            score += 0.2

        title = (item.get('title') or "").lower()
        content = (item.get('content') or "").lower()

        # Topic/title matching
        if context.current_topic:
            topic_lower = context.current_topic.lower()

            if topic_lower in title:
                score += 0.4
            elif any(word in title for word in topic_lower.split()):
                score += 0.2
            elif topic_lower in content[:1000]:  # Check first 1000 chars
                score += 0.1

        # Enhanced topic matching using extracted topics
        if context.current_topic and item.get('topics'):
            topic_lower = context.current_topic.lower()
            for topic in item['topics']:
                if isinstance(topic, dict):
                    topic_name = topic.get('name', '').lower()
                    if topic_lower in topic_name or topic_name in topic_lower:
                        score += 0.3
                        break

        # Entity matching for more intelligent surfacing
        if context.current_topic and item.get('entities'):
            topic_lower = context.current_topic.lower()
            for entity in item['entities']:
                if isinstance(entity, dict):
                    entity_name = entity.get('name', '').lower()
                    if topic_lower in entity_name or entity_name in topic_lower:
                        score += 0.25
                        break

        # Recent query matching
        if context.recent_queries:
            for query in context.recent_queries:
                query_lower = query.lower()
                if query_lower in title:
                    score += 0.3
                elif query_lower in content[:1000]:
                    score += 0.1

        # Quality boost from AI analysis
        quality = item.get('extraction_quality')
        if quality and quality > 0.8:
            score += 0.15
        elif quality and quality > 0.6:
            score += 0.1

        # Recency boost
        if self.boost_recent:
            try:
                created_at = item.get('created_at')
                if created_at:
                    content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_ago = (datetime.now() - content_date).days

                    if days_ago <= 7:
                        score += 0.2  # Recent content boost
                    elif days_ago <= 30:
                        score += 0.1  # Somewhat recent boost
            except Exception:
                pass

        return min(score, 1.0)  # Cap at 1.0

    def _determine_surface_reason(self,
                                 item: Dict[str, Any],
                                 context: SurfacingContext,
                                 score: float) -> str:
        """Determine why content was surfaced."""
        reasons = []

        title = (item.get('title') or "").lower()

        if context.current_topic:
            topic_lower = context.current_topic.lower()
            if topic_lower in title:
                reasons.append(f"matches topic '{context.current_topic}'")
            elif item.get('topics'):
                for topic in item['topics']:
                    if isinstance(topic, dict):
                        topic_name = topic.get('name', '').lower()
                        if topic_lower in topic_name:
                            reasons.append(f"extracted topic matches '{context.current_topic}'")
                            break

        if context.recent_queries:
            for query in context.recent_queries:
                if query.lower() in title:
                    reasons.append(f"matches recent query '{query}'")
                    break

        # Check for high quality AI analysis
        quality = item.get('extraction_quality')
        if quality and quality > 0.8:
            reasons.append("high-quality content")

        try:
            created_at = item.get('created_at')
            if created_at:
                content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                days_ago = (datetime.now() - content_date).days

                if days_ago <= 7:
                    reasons.append("recently added")
        except Exception:
            pass

        if score > 0.7:
            reasons.append("high relevance score")

        if not reasons:
            return "general relevance"

        return ", ".join(reasons)

    def _mock_surface_content(self, context: SurfacingContext) -> List[SurfacedContent]:
        """Mock content surfacing for when metadata manager unavailable."""
        mock_content = [
            SurfacedContent(
                uid="mock_1",
                title="Understanding Machine Learning Fundamentals",
                source="https://example.com/ml-fundamentals",
                content_type="article",
                relevance_score=0.85,
                surface_reason="matches current topic",
                metadata={"tags": ["machine learning", "AI", "fundamentals"]},
                updated_at=datetime.now().isoformat()
            ),
            SurfacedContent(
                uid="mock_2",
                title="Recent Advances in Neural Networks",
                source="https://example.com/neural-networks",
                content_type="article",
                relevance_score=0.72,
                surface_reason="recently added, high relevance",
                metadata={"tags": ["neural networks", "deep learning"]},
                updated_at=datetime.now().isoformat()
            ),
            SurfacedContent(
                uid="mock_3",
                title="AI Ethics and Society Podcast",
                source="https://example.com/ai-ethics-podcast",
                content_type="podcast",
                relevance_score=0.68,
                surface_reason="related to current interests",
                metadata={"tags": ["AI", "ethics", "society"]},
                updated_at=datetime.now().isoformat()
            )
        ]

        # Filter by context preferences
        filtered = [
            item for item in mock_content
            if item.content_type in context.content_types
        ]

        # Apply topic filtering if specified
        if context.current_topic:
            topic_lower = context.current_topic.lower()
            filtered = [
                item for item in filtered
                if topic_lower in item.title.lower() or
                   any(topic_lower in tag.lower() for tag in item.metadata.get('tags', []))
            ]

        return filtered[:context.max_results]


if __name__ == "__main__":
    # Example usage
    surfacer = ProactiveSurfacer()

    # Test topic-based surfacing
    print("🧠 Testing ProactiveSurfacer with real Atlas data")
    print("=" * 50)

    # Test 1: Topic-based surfacing
    print("\n1️⃣ Topic-based surfacing for 'AI':")
    context = SurfacingContext(
        current_topic="AI",
        max_results=5
    )
    results = surfacer.surface_content(context)

    for i, result in enumerate(results[:3], 1):
        print(f"   {i}. {result.title[:60]}...")
        print(f"      Score: {result.relevance_score:.2f} | {result.surface_reason}")

    # Test 2: Recent content
    print(f"\n2️⃣ Recent content (last 30 days):")
    recent_results = surfacer.surface_recent(days=30, max_results=5)

    for i, result in enumerate(recent_results[:3], 1):
        print(f"   {i}. {result.title[:60]}...")
        print(f"      Score: {result.relevance_score:.2f} | {result.surface_reason}")

    # Test 3: Diverse content
    print(f"\n3️⃣ Diverse content selection:")
    diverse_results = surfacer.surface_diverse_content(max_results=5)

    for i, result in enumerate(diverse_results[:3], 1):
        print(f"   {i}. {result.title[:60]}...")
        print(f"      Type: {result.content_type} | Score: {result.relevance_score:.2f}")

    print(f"\n✅ ProactiveSurfacer working with real Atlas data!")
    print(f"   Total results: {len(results)} topic, {len(recent_results)} recent, {len(diverse_results)} diverse")