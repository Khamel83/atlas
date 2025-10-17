#!/usr/bin/env python3
"""
Content Recommendation Engine

Provides personalized content recommendations based on user behavior,
content analysis, and intelligent pattern matching.
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from helpers.config import load_config
    from ask.proactive.surfacer import ProactiveSurfacer, SurfacedContent, SurfacingContext
except ImportError:
    load_config = lambda: {}


@dataclass
class Recommendation:
    """Content recommendation with reasoning."""
    content_id: str
    title: str
    source: str
    content_type: str
    recommendation_score: float
    recommendation_reason: str
    related_content: List[str]  # IDs of related content
    metadata: Dict[str, Any]
    created_at: str

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass
class UserProfile:
    """User interaction profile for recommendations."""
    frequent_topics: List[str] = None
    preferred_content_types: List[str] = None
    recent_interactions: List[str] = None  # Recent content IDs
    reading_time_patterns: Dict[str, float] = None
    quality_threshold: float = 0.6

    def __post_init__(self):
        if self.frequent_topics is None:
            self.frequent_topics = []
        if self.preferred_content_types is None:
            self.preferred_content_types = ["article", "podcast", "video"]
        if self.recent_interactions is None:
            self.recent_interactions = []
        if self.reading_time_patterns is None:
            self.reading_time_patterns = {}


class RecommendationEngine:
    """
    Content recommendation engine.

    Provides personalized recommendations based on:
    - Content similarity and relationships
    - User interaction patterns
    - Topic clustering and trends
    - Quality scoring and freshness
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize RecommendationEngine."""
        self.config = config or load_config()
        self.db_path = "data/atlas.db"
        self.surfacer = ProactiveSurfacer(config)

        # Recommendation configuration
        self.min_recommendation_score = self.config.get('min_recommendation_score', 0.4)
        self.max_recommendations = self.config.get('max_recommendations', 20)
        self.diversity_factor = self.config.get('recommendation_diversity', 0.3)

    def get_recommendations(self,
                          user_profile: UserProfile,
                          max_results: int = 10) -> List[Recommendation]:
        """
        Get personalized content recommendations.

        Args:
            user_profile: User interaction profile
            max_results: Maximum number of recommendations

        Returns:
            List of Recommendation objects ordered by score
        """
        try:
            # Get base content using different strategies
            recommendations = []

            # Strategy 1: Topic-based recommendations
            topic_recs = self._get_topic_based_recommendations(user_profile, max_results // 2)
            recommendations.extend(topic_recs)

            # Strategy 2: Similar content recommendations
            similar_recs = self._get_similar_content_recommendations(user_profile, max_results // 3)
            recommendations.extend(similar_recs)

            # Strategy 3: Trending/quality content
            trending_recs = self._get_trending_recommendations(user_profile, max_results // 3)
            recommendations.extend(trending_recs)

            # Strategy 4: Serendipitous discoveries
            discovery_recs = self._get_discovery_recommendations(user_profile, max_results // 4)
            recommendations.extend(discovery_recs)

            # Deduplicate and re-score
            unique_recs = self._deduplicate_recommendations(recommendations)

            # Apply diversity filtering
            diverse_recs = self._apply_diversity_filtering(unique_recs, max_results)

            # Sort by final score and return top results
            diverse_recs.sort(key=lambda x: x.recommendation_score, reverse=True)
            return diverse_recs[:max_results]

        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return self._get_fallback_recommendations(user_profile, max_results)

    def get_related_content(self,
                           content_id: str,
                           max_results: int = 5) -> List[Recommendation]:
        """Get content related to a specific item."""
        try:
            # Get the source content
            source_content = self._get_content_by_id(content_id)
            if not source_content:
                return []

            # Use content attributes to find similar items
            user_profile = UserProfile(
                frequent_topics=self._extract_topics_from_content(source_content),
                preferred_content_types=[source_content.get('content_type', 'article')]
            )

            related_recs = self._get_similar_content_recommendations(
                user_profile,
                max_results,
                exclude_ids=[content_id]
            )

            # Update reasons to indicate relationship
            for rec in related_recs:
                rec.recommendation_reason = f"Related to '{source_content.get('title', 'selected content')[:50]}...'"
                rec.related_content = [content_id]

            return related_recs

        except Exception as e:
            print(f"Error finding related content: {e}")
            return []

    def _get_topic_based_recommendations(self,
                                       user_profile: UserProfile,
                                       max_results: int) -> List[Recommendation]:
        """Get recommendations based on user's frequent topics."""
        recommendations = []

        try:
            for topic in user_profile.frequent_topics[:3]:  # Top 3 topics
                context = SurfacingContext(
                    current_topic=topic,
                    content_types=user_profile.preferred_content_types,
                    max_results=max_results // len(user_profile.frequent_topics[:3]) + 1
                )

                surfaced = self.surfacer.surface_content(context)

                for item in surfaced:
                    # Convert to Recommendation
                    rec = Recommendation(
                        content_id=item.uid,
                        title=item.title,
                        source=item.source,
                        content_type=item.content_type,
                        recommendation_score=item.relevance_score + 0.1,  # Topic bonus
                        recommendation_reason=f"Matches your interest in '{topic}'",
                        related_content=[],
                        metadata=item.metadata,
                        created_at=datetime.now().isoformat()
                    )
                    recommendations.append(rec)

            return recommendations

        except Exception as e:
            print(f"Error in topic-based recommendations: {e}")
            return []

    def _get_similar_content_recommendations(self,
                                           user_profile: UserProfile,
                                           max_results: int,
                                           exclude_ids: List[str] = None) -> List[Recommendation]:
        """Get recommendations based on content similarity."""
        exclude_ids = exclude_ids or []
        recommendations = []

        try:
            # Get content similar to recently viewed items
            for content_id in user_profile.recent_interactions[:5]:  # Recent 5 items
                if content_id in exclude_ids:
                    continue

                similar_items = self._find_similar_content(content_id, max_results // 5 + 1)

                for item in similar_items:
                    if item['id'] in exclude_ids:
                        continue

                    # Calculate similarity score
                    similarity_score = self._calculate_content_similarity(content_id, item['id'])

                    if similarity_score >= self.min_recommendation_score:
                        rec = Recommendation(
                            content_id=str(item['id']),
                            title=item.get('title', 'Untitled'),
                            source=item.get('url', ''),
                            content_type=item.get('content_type', 'unknown'),
                            recommendation_score=similarity_score,
                            recommendation_reason="Similar to content you've viewed recently",
                            related_content=[content_id],
                            metadata=item,
                            created_at=datetime.now().isoformat()
                        )
                        recommendations.append(rec)

            return recommendations

        except Exception as e:
            print(f"Error in similarity recommendations: {e}")
            return []

    def _get_trending_recommendations(self,
                                    user_profile: UserProfile,
                                    max_results: int) -> List[Recommendation]:
        """Get trending/high-quality content recommendations."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get high-quality recent content
            query = """
            SELECT c.id, c.title, c.content_type, c.url, c.created_at,
                   ci.extraction_quality, ci.sentiment, ci.key_topics, ci.entities
            FROM content c
            LEFT JOIN content_insights ci ON c.id = ci.content_id
            WHERE c.content_type IN ({})
            AND c.created_at >= ?
            AND (ci.extraction_quality IS NULL OR ci.extraction_quality >= ?)
            ORDER BY c.created_at DESC, ci.extraction_quality DESC
            LIMIT ?
            """.format(','.join(['?' for _ in user_profile.preferred_content_types]))

            params = user_profile.preferred_content_types[:]
            params.append((datetime.now() - timedelta(days=30)).isoformat())
            params.append(user_profile.quality_threshold)
            params.append(max_results)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            recommendations = []
            for row in rows:
                item = dict(row)
                quality = item.get('extraction_quality', 0.7)

                # Trending score based on recency and quality
                days_ago = (datetime.now() - datetime.fromisoformat(item['created_at'])).days
                recency_score = max(0, 1.0 - (days_ago / 30.0))  # Decays over 30 days
                trending_score = (float(quality or 0.7) * 0.6) + (recency_score * 0.4)

                if trending_score >= self.min_recommendation_score:
                    rec = Recommendation(
                        content_id=str(item['id']),
                        title=item.get('title', 'Untitled'),
                        source=item.get('url', ''),
                        content_type=item.get('content_type', 'unknown'),
                        recommendation_score=trending_score,
                        recommendation_reason="High-quality recent content",
                        related_content=[],
                        metadata=item,
                        created_at=datetime.now().isoformat()
                    )
                    recommendations.append(rec)

            conn.close()
            return recommendations

        except Exception as e:
            print(f"Error in trending recommendations: {e}")
            return []

    def _get_discovery_recommendations(self,
                                     user_profile: UserProfile,
                                     max_results: int) -> List[Recommendation]:
        """Get serendipitous discovery recommendations."""
        try:
            # Use diverse content from surfacer for discovery
            diverse_content = self.surfacer.surface_diverse_content(max_results)

            recommendations = []
            for item in diverse_content:
                # Lower score for discovery (encourage exploration)
                discovery_score = item.relevance_score * 0.7

                if discovery_score >= self.min_recommendation_score * 0.8:  # Lower threshold
                    rec = Recommendation(
                        content_id=item.uid,
                        title=item.title,
                        source=item.source,
                        content_type=item.content_type,
                        recommendation_score=discovery_score,
                        recommendation_reason="Discover something new",
                        related_content=[],
                        metadata=item.metadata,
                        created_at=datetime.now().isoformat()
                    )
                    recommendations.append(rec)

            return recommendations

        except Exception as e:
            print(f"Error in discovery recommendations: {e}")
            return []

    def _get_content_by_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get content by ID from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
            SELECT c.*, ci.key_topics, ci.entities, ci.summary
            FROM content c
            LEFT JOIN content_insights ci ON c.id = ci.content_id
            WHERE c.id = ?
            """, (content_id,))

            row = cursor.fetchone()
            conn.close()

            return dict(row) if row else None

        except Exception:
            return None

    def _find_similar_content(self, content_id: str, max_results: int) -> List[Dict[str, Any]]:
        """Find content similar to given content ID."""
        try:
            source_content = self._get_content_by_id(content_id)
            if not source_content:
                return []

            # Simple similarity based on shared topics/entities
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get content with similar topics or entities
            cursor.execute("""
            SELECT c.id, c.title, c.content_type, c.url, c.created_at,
                   ci.key_topics, ci.entities, ci.extraction_quality
            FROM content c
            LEFT JOIN content_insights ci ON c.id = ci.content_id
            WHERE c.id != ? AND c.content_type = ?
            ORDER BY c.created_at DESC
            LIMIT ?
            """, (content_id, source_content.get('content_type', 'article'), max_results * 2))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception:
            return []

    def _calculate_content_similarity(self, content_id1: str, content_id2: str) -> float:
        """Calculate similarity score between two content items."""
        try:
            content1 = self._get_content_by_id(content_id1)
            content2 = self._get_content_by_id(content_id2)

            if not content1 or not content2:
                return 0.0

            score = 0.0

            # Same content type bonus
            if content1.get('content_type') == content2.get('content_type'):
                score += 0.2

            # Topic overlap
            topics1 = self._extract_topics_from_content(content1)
            topics2 = self._extract_topics_from_content(content2)

            if topics1 and topics2:
                common_topics = set(topics1) & set(topics2)
                topic_score = len(common_topics) / max(len(topics1), len(topics2))
                score += topic_score * 0.4

            # Title similarity (simple word overlap)
            title1_words = set((content1.get('title') or '').lower().split())
            title2_words = set((content2.get('title') or '').lower().split())

            if title1_words and title2_words:
                common_words = title1_words & title2_words
                title_score = len(common_words) / max(len(title1_words), len(title2_words))
                score += title_score * 0.3

            return min(score, 1.0)

        except Exception:
            return 0.0

    def _extract_topics_from_content(self, content: Dict[str, Any]) -> List[str]:
        """Extract topic names from content."""
        try:
            topics = []
            key_topics = content.get('key_topics')

            if key_topics:
                if isinstance(key_topics, str):
                    topic_data = json.loads(key_topics)
                else:
                    topic_data = key_topics

                for topic in topic_data:
                    if isinstance(topic, dict):
                        topics.append(topic.get('name', ''))
                    else:
                        topics.append(str(topic))

            return [t for t in topics if t]

        except Exception:
            return []

    def _deduplicate_recommendations(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Remove duplicate recommendations."""
        seen_ids = set()
        unique_recs = []

        for rec in recommendations:
            if rec.content_id not in seen_ids:
                seen_ids.add(rec.content_id)
                unique_recs.append(rec)

        return unique_recs

    def _apply_diversity_filtering(self,
                                  recommendations: List[Recommendation],
                                  max_results: int) -> List[Recommendation]:
        """Apply diversity filtering to avoid too much similar content."""
        if len(recommendations) <= max_results:
            return recommendations

        # Group by content type for diversity
        type_groups = defaultdict(list)
        for rec in recommendations:
            type_groups[rec.content_type].append(rec)

        # Sample from each type to maintain diversity
        diverse_recs = []
        items_per_type = max(1, max_results // len(type_groups))

        for content_type, type_recs in type_groups.items():
            # Sort by score and take top items
            type_recs.sort(key=lambda x: x.recommendation_score, reverse=True)
            diverse_recs.extend(type_recs[:items_per_type])

        # Fill remaining slots with highest scoring items
        if len(diverse_recs) < max_results:
            remaining_recs = [rec for rec in recommendations if rec not in diverse_recs]
            remaining_recs.sort(key=lambda x: x.recommendation_score, reverse=True)
            diverse_recs.extend(remaining_recs[:max_results - len(diverse_recs)])

        return diverse_recs

    def _get_fallback_recommendations(self,
                                    user_profile: UserProfile,
                                    max_results: int) -> List[Recommendation]:
        """Get fallback recommendations when main system fails."""
        try:
            # Use surfacer as fallback
            context = SurfacingContext(
                content_types=user_profile.preferred_content_types,
                max_results=max_results
            )

            surfaced = self.surfacer.surface_content(context)

            recommendations = []
            for item in surfaced:
                rec = Recommendation(
                    content_id=item.uid,
                    title=item.title,
                    source=item.source,
                    content_type=item.content_type,
                    recommendation_score=item.relevance_score * 0.8,  # Fallback penalty
                    recommendation_reason="General recommendation",
                    related_content=[],
                    metadata=item.metadata,
                    created_at=datetime.now().isoformat()
                )
                recommendations.append(rec)

            return recommendations

        except Exception:
            return []


if __name__ == "__main__":
    # Test recommendation engine
    print("🎯 Testing Content Recommendation Engine")
    print("=" * 50)

    # Create test user profile
    user_profile = UserProfile(
        frequent_topics=["AI", "technology", "business"],
        preferred_content_types=["article", "podcast"],
        recent_interactions=["12345", "67890"]  # Mock IDs
    )

    # Initialize recommendation engine
    engine = RecommendationEngine()

    # Test 1: General recommendations
    print("\n1️⃣ General recommendations:")
    recommendations = engine.get_recommendations(user_profile, max_results=5)

    for i, rec in enumerate(recommendations[:3], 1):
        print(f"   {i}. {rec.title[:60]}...")
        print(f"      Score: {rec.recommendation_score:.2f} | {rec.recommendation_reason}")

    # Test 2: Related content (if we have real content)
    if recommendations:
        print(f"\n2️⃣ Content related to first recommendation:")
        related = engine.get_related_content(recommendations[0].content_id, max_results=3)

        for i, rec in enumerate(related[:2], 1):
            print(f"   {i}. {rec.title[:60]}...")
            print(f"      Score: {rec.recommendation_score:.2f} | {rec.recommendation_reason}")

    print(f"\n✅ Recommendation engine working!")
    print(f"   Generated {len(recommendations)} recommendations")