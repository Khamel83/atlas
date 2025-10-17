#!/usr/bin/env python3
"""
Recall Engine

Intelligent content recall system that helps users rediscover relevant information
based on context, keywords, time, and semantic relationships. Also includes
spaced repetition for learning reinforcement.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import re

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from helpers.metadata_manager import MetadataManager
    from helpers.config import load_config
except ImportError:
    MetadataManager = None
    load_config = lambda: {}


@dataclass
class RecallResult:
    """Represents a recalled content item with relevance information."""
    uid: str
    title: str
    content_type: str
    source: str
    relevance_score: float
    recall_reason: str
    metadata: Dict[str, Any]
    recalled_at: str
    snippet: Optional[str] = None

    def __post_init__(self):
        if self.recalled_at is None:
            self.recalled_at = datetime.now().isoformat()


@dataclass
class RecallContext:
    """Context for content recall operations."""
    query: Optional[str] = None
    keywords: List[str] = None
    time_period: Optional[str] = None  # recent, week, month, year, all
    content_types: List[str] = None
    tags: List[str] = None
    max_results: int = 10
    min_relevance: float = 0.3
    include_snippets: bool = True
    semantic_search: bool = False

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.content_types is None:
            self.content_types = ["article", "podcast", "video"]
        if self.tags is None:
            self.tags = []


@dataclass
class SpacedRepetitionItem:
    """Item scheduled for spaced repetition review."""
    metadata: Any
    review_data: Dict[str, Any]
    difficulty_score: float
    review_urgency: float
    next_review_date: Optional[str] = None


class RecallEngine:
    """
    Comprehensive recall engine for Atlas.

    Provides both intelligent content search and spaced repetition:
    - Keyword-based search
    - Semantic similarity (when available)
    - Time-based filtering
    - Tag-based categorization
    - Context-aware ranking
    - Spaced repetition scheduling
    - Learning progress tracking
    """

    def __init__(self, metadata_manager=None, config: Dict[str, Any] = None):
        """Initialize RecallEngine."""
        self.config = config or {}
        if not config and load_config:
            self.config = load_config()

        # Support both direct injection and automatic initialization
        if metadata_manager:
            self.metadata_manager = metadata_manager
        else:
            self.metadata_manager = None
            if MetadataManager:
                try:
                    self.metadata_manager = MetadataManager(self.config)
                except Exception:
                    pass

        # Search configuration
        self.relevance_weights = {
            "title_match": 0.4,
            "tag_match": 0.3,
            "content_match": 0.2,
            "recency": 0.1
        }

        # Time period mappings
        self.time_periods = {
            "recent": 7,    # days
            "week": 7,
            "month": 30,
            "quarter": 90,
            "year": 365,
            "all": None
        }

    # ========================================
    # CONTENT SEARCH & RECALL METHODS
    # ========================================

    def recall(self, context: RecallContext) -> List[RecallResult]:
        """
        Recall content based on provided context.

        Args:
            context: Recall context with search parameters

        Returns:
            List of recalled content items ordered by relevance
        """
        start_time = datetime.now()

        if not self.metadata_manager:
            return self._mock_recall(context)

        try:
            # Get all available content
            all_content = self._get_searchable_content()

            # Apply filters
            filtered_content = self._apply_filters(all_content, context)

            # Score and rank results
            scored_results = self._score_and_rank(filtered_content, context)

            # Convert to RecallResult objects
            recall_results = self._create_recall_results(scored_results, context)

            # Calculate search stats
            search_time = (datetime.now() - start_time).total_seconds() * 1000
            self._log_recall_stats(all_content, recall_results, search_time)

            return recall_results[:context.max_results]

        except Exception as e:
            print(f"Error during recall: {e}")
            return self._mock_recall(context)

    def quick_search(self, query: str, max_results: int = 5) -> List[RecallResult]:
        """Quick search for immediate results."""
        context = RecallContext(
            query=query,
            max_results=max_results,
            time_period="all",
            min_relevance=0.2
        )
        return self.recall(context)

    def recall_by_tags(self, tags: List[str], max_results: int = 10) -> List[RecallResult]:
        """Recall content by specific tags."""
        context = RecallContext(
            tags=tags,
            max_results=max_results,
            time_period="all"
        )
        return self.recall(context)

    def recall_recent(self, days: int = 7, max_results: int = 10) -> List[RecallResult]:
        """Recall recent content."""
        context = RecallContext(
            time_period="recent" if days <= 7 else "month",
            max_results=max_results,
            min_relevance=0.1  # Lower threshold for recent content
        )
        return self.recall(context)

    def recall_similar(self, reference_uid: str, max_results: int = 5) -> List[RecallResult]:
        """Recall content similar to a reference item."""
        if not self.metadata_manager:
            return []

        try:
            # Find the reference content
            reference_item = None
            all_content = self._get_searchable_content()

            for item in all_content:
                if getattr(item, 'uid', None) == reference_uid:
                    reference_item = item
                    break

            if not reference_item:
                return []

            # Extract keywords from reference item
            keywords = []
            if hasattr(reference_item, 'tags'):
                keywords.extend(reference_item.tags[:3])
            if hasattr(reference_item, 'title'):
                title_words = re.findall(r'\b[a-zA-Z]{4,}\b', reference_item.title.lower())
                keywords.extend(title_words[:3])

            context = RecallContext(
                keywords=keywords,
                tags=getattr(reference_item, 'tags', [])[:2],
                content_types=[getattr(reference_item, 'content_type', 'article')],
                max_results=max_results + 1,  # +1 to exclude reference item
                min_relevance=0.2
            )

            results = self.recall(context)

            # Filter out the reference item itself
            filtered_results = [r for r in results if r.uid != reference_uid]

            return filtered_results[:max_results]

        except Exception as e:
            print(f"Error finding similar content: {e}")
            return []

    # ========================================
    # SPACED REPETITION METHODS (Legacy Support)
    # ========================================

    def get_items_for_review(self, limit=10) -> List[SpacedRepetitionItem]:
        """
        Get optimally scheduled review items using enhanced MetadataManager methods.
        Enhanced with difficulty adjustment and progress tracking.
        """
        if not self.metadata_manager:
            return []

        try:
            # Use the new get_recall_items method if available
            if hasattr(self.metadata_manager, 'get_recall_items'):
                recall_items = self.metadata_manager.get_recall_items(limit)
            else:
                # Fallback to getting all metadata
                all_items = self.metadata_manager.get_all_metadata()
                # Simple filtering for items needing review
                recall_items = [item for item in all_items if self._needs_review(item)][:limit]

            # Enhance with difficulty adjustment and user feedback
            enhanced_items = []
            for item in recall_items:
                review_data = self._get_review_data(item)
                enhanced_items.append(SpacedRepetitionItem(
                    metadata=item,
                    review_data=review_data,
                    difficulty_score=self._calculate_difficulty_score(item, review_data),
                    review_urgency=self._calculate_urgency(item, review_data),
                    next_review_date=review_data.get('next_review_date')
                ))

            # Sort by urgency (highest first)
            enhanced_items.sort(key=lambda x: x.review_urgency, reverse=True)

            return enhanced_items

        except Exception as e:
            print(f"Error getting review items: {e}")
            return []

    def mark_reviewed(self, content_metadata, success=True, difficulty_rating=None):
        """
        Mark a content item as reviewed with enhanced feedback tracking.
        """
        try:
            if not hasattr(content_metadata, "type_specific") or content_metadata.type_specific is None:
                content_metadata.type_specific = {}

            # Update review timestamp and count
            content_metadata.type_specific["last_reviewed"] = datetime.now().isoformat()
            review_count = content_metadata.type_specific.get("review_count", 0) + 1
            content_metadata.type_specific["review_count"] = review_count

            # Update success rate (exponential moving average)
            current_success_rate = content_metadata.type_specific.get("review_success_rate", 1.0)
            alpha = 0.3  # Learning rate
            new_success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * current_success_rate
            content_metadata.type_specific["review_success_rate"] = new_success_rate

            # Update difficulty rating if provided
            if difficulty_rating is not None:
                content_metadata.type_specific["difficulty_rating"] = max(1, min(5, difficulty_rating))

            # Calculate next review date based on performance
            next_review_interval = self._calculate_next_interval(review_count, success, new_success_rate)
            next_review_date = datetime.now() + timedelta(days=next_review_interval)
            content_metadata.type_specific["next_review_date"] = next_review_date.isoformat()

            self.metadata_manager.save_metadata(content_metadata)

        except Exception as e:
            print(f"Error marking content as reviewed: {e}")

    def schedule_spaced_repetition(self, n=5):
        """Legacy method for backward compatibility."""
        try:
            items = self.get_items_for_review(n)
            result = []
            for item in items:
                # Convert to format expected by web interface
                recall_item = type('Item', (), {
                    'title': getattr(item, 'title', 'Unknown'),
                    'type_specific': {'last_reviewed': getattr(item, 'last_reviewed', 'Never')}
                })()
                result.append(recall_item)
            return result
        except Exception as e:
            print(f"Error in schedule_spaced_repetition: {e}")
            return []

    # ========================================
    # ANALYTICS AND INSIGHTS
    # ========================================

    def get_recall_suggestions(self) -> List[str]:
        """Get suggestions for what to recall based on content analysis."""
        if not self.metadata_manager:
            return ["machine learning", "productivity", "technology"]

        try:
            all_content = self._get_searchable_content()

            # Analyze tags for popular topics
            tag_counts = Counter()
            for item in all_content:
                if hasattr(item, 'tags'):
                    for tag in item.tags:
                        if tag:
                            tag_counts[tag.lower()] += 1

            # Get most common tags as suggestions
            suggestions = [tag for tag, count in tag_counts.most_common(10) if count >= 2]

            return suggestions[:8]

        except Exception as e:
            print(f"Error generating suggestions: {e}")
            return ["recent content", "articles", "podcasts"]

    def analyze_recall_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in content for better recall recommendations."""
        if not self.metadata_manager:
            return {"error": "No metadata manager available"}

        try:
            all_content = self._get_searchable_content()

            # Content type distribution
            type_counts = Counter()
            tag_counts = Counter()
            monthly_counts = defaultdict(int)

            for item in all_content:
                # Content type analysis
                if hasattr(item, 'content_type'):
                    content_type = getattr(item.content_type, 'value', item.content_type) if hasattr(item.content_type, 'value') else item.content_type
                    type_counts[content_type] += 1

                # Tag analysis
                if hasattr(item, 'tags'):
                    for tag in item.tags:
                        if tag:
                            tag_counts[tag.lower()] += 1

                # Time analysis
                if hasattr(item, 'created_at'):
                    try:
                        created_at = item.created_at
                        if created_at:
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            month_key = dt.strftime('%Y-%m')
                            monthly_counts[month_key] += 1
                    except Exception:
                        pass

            return {
                "total_items": len(all_content),
                "content_types": dict(type_counts.most_common()),
                "popular_tags": dict(tag_counts.most_common(15)),
                "monthly_distribution": dict(sorted(monthly_counts.items())[-12:]),  # Last 12 months
                "searchable_items": len([item for item in all_content if self._is_searchable(item)])
            }

        except Exception as e:
            return {"error": f"Analysis failed: {e}"}

    def get_content_gaps(self) -> List[str]:
        """Identify gaps in content coverage by topics or domains."""
        if not self.metadata_manager:
            return ["AI ethics", "sustainability", "digital privacy"]

        try:
            all_content = self._get_searchable_content()

            # Extract all tags and topics
            all_tags = set()
            for item in all_content:
                if hasattr(item, 'tags'):
                    for tag in item.tags:
                        if tag:
                            all_tags.add(tag.lower())

            # Define common knowledge domains
            knowledge_domains = {
                "technology": ["ai", "machine learning", "software", "programming", "data science"],
                "science": ["biology", "physics", "chemistry", "research", "scientific method"],
                "business": ["strategy", "marketing", "finance", "entrepreneurship", "management"],
                "philosophy": ["ethics", "epistemology", "metaphysics", "logic", "existentialism"],
                "health": ["medicine", "nutrition", "exercise", "mental health", "wellness"],
                "environment": ["climate", "sustainability", "ecology", "conservation", "renewable energy"],
                "education": ["learning", "pedagogy", "curriculum", "assessment", "cognitive science"],
                "psychology": ["cognition", "behavior", "emotion", "development", "social psychology"]
            }

            # Find underrepresented domains
            gaps = []
            for domain, keywords in knowledge_domains.items():
                domain_tags = [tag for tag in all_tags if any(keyword in tag for keyword in keywords)]
                if len(domain_tags) < 2:  # Less than 2 tags in this domain
                    gaps.append(domain)

            return gaps

        except Exception as e:
            print(f"Error identifying content gaps: {e}")
            return ["interdisciplinary topics", "emerging fields", "historical context"]

    def get_reading_progress(self) -> Dict[str, Any]:
        """Get insights into reading/consumption progress."""
        if not self.metadata_manager:
            return {"total_items": 100, "consumed_items": 65, "completion_rate": 0.65}

        try:
            all_content = self._get_searchable_content()

            # Count consumed items (would need integration with actual consumption tracking)
            consumed_count = 0
            word_count_total = 0
            word_count_consumed = 0

            for item in all_content:
                # For now, we'll assume 50% are "consumed" - in a real implementation,
                # this would check against actual consumption data
                if hasattr(item, 'uid') and hash(item.uid) % 2 == 0:  # Mock consumption check
                    consumed_count += 1

                    if hasattr(item, 'word_count'):
                        word_count_consumed += item.word_count or 0

                if hasattr(item, 'word_count'):
                    word_count_total += item.word_count or 0

            completion_rate = consumed_count / len(all_content) if all_content else 0
            word_completion_rate = word_count_consumed / word_count_total if word_count_total > 0 else 0

            return {
                "total_items": len(all_content),
                "consumed_items": consumed_count,
                "completion_rate": completion_rate,
                "total_word_count": word_count_total,
                "consumed_word_count": word_count_consumed,
                "word_completion_rate": word_completion_rate,
                "reading_pace": word_count_consumed / max(len(all_content), 1)  # Words per item
            }

        except Exception as e:
            print(f"Error calculating reading progress: {e}")
            return {"error": "Failed to calculate reading progress"}

    def get_review_analytics(self):
        """Get analytics about review performance and patterns (legacy method)."""
        if not self.metadata_manager:
            return {"error": "No metadata manager available"}

        try:
            all_items = self.metadata_manager.get_all_metadata()

            total_items = len(all_items)
            reviewed_items = []
            never_reviewed = 0

            for item in all_items:
                if hasattr(item, 'type_specific') and item.type_specific and item.type_specific.get("last_reviewed"):
                    reviewed_items.append(item)
                else:
                    never_reviewed += 1

            if not reviewed_items:
                return {
                    "total_items": total_items,
                    "never_reviewed": never_reviewed,
                    "review_completion_rate": 0,
                    "average_success_rate": 0,
                    "average_review_count": 0,
                }

            # Calculate statistics
            total_reviews = sum(item.type_specific.get("review_count", 0) for item in reviewed_items)
            total_success_rate = sum(item.type_specific.get("review_success_rate", 1.0) for item in reviewed_items)

            return {
                "total_items": total_items,
                "reviewed_items": len(reviewed_items),
                "never_reviewed": never_reviewed,
                "review_completion_rate": len(reviewed_items) / total_items,
                "average_success_rate": total_success_rate / len(reviewed_items),
                "average_review_count": total_reviews / len(reviewed_items),
                "items_due_today": len(self.get_items_for_review(100)),
            }
        except Exception as e:
            return {"error": f"Review analytics failed: {e}"}

    # ========================================
    # PRIVATE HELPER METHODS
    # ========================================

    def _get_searchable_content(self) -> List[Any]:
        """Get all content available for search."""
        if hasattr(self.metadata_manager, 'list_all_content'):
            all_content = self.metadata_manager.list_all_content()
        else:
            all_content = self.metadata_manager.get_all_metadata()

        # Filter to searchable items
        return [item for item in all_content if self._is_searchable(item)]

    def _is_searchable(self, item: Any) -> bool:
        """Determine if an item is searchable."""
        # Must have at least title or tags
        has_title = hasattr(item, 'title') and item.title
        has_tags = hasattr(item, 'tags') and item.tags

        return has_title or has_tags

    def _needs_review(self, item: Any) -> bool:
        """Determine if an item needs review (for spaced repetition)."""
        if not hasattr(item, 'type_specific') or not item.type_specific:
            return True  # Never reviewed

        next_review = item.type_specific.get('next_review_date')
        if not next_review:
            return True

        try:
            next_review_date = datetime.fromisoformat(next_review.replace('Z', '+00:00'))
            return datetime.now() >= next_review_date
        except Exception:
            return True

    def _apply_filters(self, content_items: List[Any], context: RecallContext) -> List[Any]:
        """Apply context filters to content items."""
        filtered = content_items

        # Time period filter
        if context.time_period and context.time_period != "all":
            days = self.time_periods.get(context.time_period)
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                time_filtered = []

                for item in filtered:
                    try:
                        if hasattr(item, 'created_at'):
                            created_at = item.created_at
                        else:
                            created_at = getattr(item, 'date', '')

                        if created_at:
                            content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            if content_date >= cutoff_date:
                                time_filtered.append(item)
                    except Exception:
                        # Include items without valid dates
                        time_filtered.append(item)

                filtered = time_filtered

        # Content type filter
        if context.content_types:
            type_filtered = []
            for item in filtered:
                if hasattr(item, 'content_type'):
                    content_type = getattr(item.content_type, 'value', item.content_type) if hasattr(item.content_type, 'value') else item.content_type
                    if content_type in context.content_types:
                        type_filtered.append(item)
                else:
                    # Include items without content type
                    type_filtered.append(item)
            filtered = type_filtered

        # Tag filter
        if context.tags:
            tag_filtered = []
            for item in filtered:
                if hasattr(item, 'tags'):
                    item_tags = [tag.lower() for tag in item.tags]
                    if any(tag.lower() in item_tags for tag in context.tags):
                        tag_filtered.append(item)
            filtered = tag_filtered

        return filtered

    def _score_and_rank(self, content_items: List[Any], context: RecallContext) -> List[Tuple[Any, float]]:
        """Score and rank content items by relevance."""
        scored_items = []

        for item in content_items:
            score = self._calculate_relevance_score(item, context)
            if score >= context.min_relevance:
                scored_items.append((item, score))

        # Sort by score (descending)
        scored_items.sort(key=lambda x: x[1], reverse=True)

        return scored_items

    def _calculate_relevance_score(self, item: Any, context: RecallContext) -> float:
        """Calculate relevance score for an item."""
        score = 0.0

        # Title matching
        if context.query or context.keywords:
            title_score = self._calculate_title_score(item, context)
            score += title_score * self.relevance_weights["title_match"]

        # Tag matching
        if context.tags or context.keywords:
            tag_score = self._calculate_tag_score(item, context)
            score += tag_score * self.relevance_weights["tag_match"]

        # Content matching (if available)
        content_score = self._calculate_content_score(item, context)
        score += content_score * self.relevance_weights["content_match"]

        # Recency boost
        recency_score = self._calculate_recency_score(item)
        score += recency_score * self.relevance_weights["recency"]

        return min(score, 1.0)  # Cap at 1.0

    def _calculate_title_score(self, item: Any, context: RecallContext) -> float:
        """Calculate title-based relevance score."""
        if not hasattr(item, 'title') or not item.title:
            return 0.0

        title = item.title.lower()
        score = 0.0

        # Query matching
        if context.query:
            query_lower = context.query.lower()
            if query_lower in title:
                score += 0.8
            else:
                # Partial word matching
                query_words = query_lower.split()
                matches = sum(1 for word in query_words if word in title)
                if matches > 0:
                    score += 0.4 * (matches / len(query_words))

        # Keyword matching
        if context.keywords:
            keyword_matches = sum(1 for keyword in context.keywords if keyword.lower() in title)
            if keyword_matches > 0:
                score += 0.6 * (keyword_matches / len(context.keywords))

        return min(score, 1.0)

    def _calculate_tag_score(self, item: Any, context: RecallContext) -> float:
        """Calculate tag-based relevance score."""
        if not hasattr(item, 'tags') or not item.tags:
            return 0.0

        item_tags = [tag.lower() for tag in item.tags]
        score = 0.0

        # Direct tag matches
        if context.tags:
            tag_matches = sum(1 for tag in context.tags if tag.lower() in item_tags)
            if tag_matches > 0:
                score += 0.8 * (tag_matches / len(context.tags))

        # Keyword matches in tags
        if context.keywords:
            keyword_matches = 0
            for keyword in context.keywords:
                if any(keyword.lower() in tag for tag in item_tags):
                    keyword_matches += 1
            if keyword_matches > 0:
                score += 0.6 * (keyword_matches / len(context.keywords))

        return min(score, 1.0)

    def _calculate_content_score(self, item: Any, context: RecallContext) -> float:
        """Calculate content-based relevance score."""
        if not context.query and not context.keywords:
            return 0.0

        # For now, return moderate score based on content availability
        if hasattr(item, 'content_path') and item.content_path:
            return 0.3
        elif hasattr(item, 'content') and item.content:
            return 0.5

        return 0.0

    def _calculate_recency_score(self, item: Any) -> float:
        """Calculate recency-based relevance score."""
        try:
            if hasattr(item, 'created_at'):
                created_at = item.created_at
            else:
                created_at = getattr(item, 'date', '')

            if not created_at:
                return 0.0

            content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            days_ago = (datetime.now() - content_date).days

            # Exponential decay: newer content gets higher scores
            if days_ago <= 7:
                return 1.0
            elif days_ago <= 30:
                return 0.8
            elif days_ago <= 90:
                return 0.5
            elif days_ago <= 365:
                return 0.2
            else:
                return 0.1

        except Exception:
            return 0.0

    def _create_recall_results(self, scored_items: List[Tuple[Any, float]], context: RecallContext) -> List[RecallResult]:
        """Create RecallResult objects from scored items."""
        results = []

        for item, score in scored_items:
            # Generate recall reason
            reason = self._generate_recall_reason(item, context, score)

            # Extract snippet if requested
            snippet = None
            if context.include_snippets:
                snippet = self._extract_snippet(item, context)

            # Create result
            result = RecallResult(
                uid=getattr(item, 'uid', 'unknown'),
                title=getattr(item, 'title', 'Untitled'),
                content_type=getattr(getattr(item, 'content_type', None), 'value', 'unknown') if hasattr(getattr(item, 'content_type', None), 'value') else getattr(item, 'content_type', 'unknown'),
                source=getattr(item, 'source', getattr(item, 'url', 'Unknown')),
                relevance_score=score,
                recall_reason=reason,
                metadata=self._extract_metadata(item),
                recalled_at=datetime.now().isoformat(),
                snippet=snippet
            )

            results.append(result)

        return results

    def _generate_recall_reason(self, item: Any, context: RecallContext, score: float) -> str:
        """Generate human-readable reason for why item was recalled."""
        reasons = []

        if context.query:
            if hasattr(item, 'title') and context.query.lower() in item.title.lower():
                reasons.append(f"title matches '{context.query}'")

        if context.tags and hasattr(item, 'tags'):
            matching_tags = [tag for tag in context.tags if tag.lower() in [t.lower() for t in item.tags]]
            if matching_tags:
                reasons.append(f"tagged as {', '.join(matching_tags[:2])}")

        if context.keywords:
            # Check for keyword matches
            if hasattr(item, 'title'):
                title_keywords = [kw for kw in context.keywords if kw.lower() in item.title.lower()]
                if title_keywords:
                    reasons.append(f"contains keywords: {', '.join(title_keywords[:2])}")

        # Recency
        try:
            if hasattr(item, 'created_at'):
                created_at = item.created_at
                if created_at:
                    content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_ago = (datetime.now() - content_date).days
                    if days_ago <= 7:
                        reasons.append("recently added")
        except Exception:
            pass

        if score > 0.8:
            reasons.append("high relevance")

        if not reasons:
            return "general match"

        return ", ".join(reasons[:3])

    def _extract_snippet(self, item: Any, context: RecallContext) -> Optional[str]:
        """Extract a relevant snippet from the content."""
        # Simple snippet extraction - would be enhanced with full content access
        if hasattr(item, 'title') and item.title:
            return item.title[:200] + "..." if len(item.title) > 200 else item.title

        return None

    def _extract_metadata(self, item: Any) -> Dict[str, Any]:
        """Extract metadata from item for result."""
        metadata = {}

        if hasattr(item, 'tags'):
            metadata['tags'] = item.tags
        if hasattr(item, 'created_at'):
            metadata['created_at'] = item.created_at
        if hasattr(item, 'word_count'):
            metadata['word_count'] = item.word_count
        if hasattr(item, 'author'):
            metadata['author'] = item.author

        return metadata

    def _log_recall_stats(self, all_content: List[Any], results: List[RecallResult], search_time: float):
        """Log recall operation statistics."""
        # This could be enhanced to log to a proper analytics system
        pass

    # ========================================
    # SPACED REPETITION HELPER METHODS
    # ========================================

    def _get_review_data(self, metadata):
        """Extract review-specific data from metadata."""
        if not hasattr(metadata, 'type_specific') or not metadata.type_specific:
            return {
                "last_reviewed": None,
                "review_count": 0,
                "success_rate": 1.0,
                "difficulty_rating": 3,
                "next_review_date": None
            }

        return {
            "last_reviewed": metadata.type_specific.get("last_reviewed"),
            "review_count": metadata.type_specific.get("review_count", 0),
            "success_rate": metadata.type_specific.get("review_success_rate", 1.0),
            "difficulty_rating": metadata.type_specific.get("difficulty_rating", 3),  # 1-5 scale
            "next_review_date": metadata.type_specific.get("next_review_date")
        }

    def _calculate_difficulty_score(self, metadata, review_data):
        """Calculate difficulty score based on content characteristics and review history."""
        difficulty = 1.0

        # Base difficulty from user rating
        difficulty += (review_data["difficulty_rating"] - 3) * 0.2  # Normalize around 3

        # Content complexity factors
        if hasattr(metadata, 'tags') and len(metadata.tags) > 5:  # Highly tagged content might be more complex
            difficulty += 0.3

        # Content type difficulty
        content_type = getattr(metadata, 'content_type', 'article')
        if hasattr(content_type, 'value'):
            content_type = content_type.value

        type_difficulty = {
            "article": 1.0,
            "youtube": 0.8,
            "podcast": 0.9,
            "instapaper": 1.1,
        }
        difficulty *= type_difficulty.get(content_type, 1.0)

        # Historical performance
        if review_data["success_rate"] < 0.7:  # Poor performance = higher difficulty
            difficulty += 0.4
        elif review_data["success_rate"] > 0.9:  # Good performance = lower difficulty
            difficulty -= 0.2

        return max(difficulty, 0.1)  # Minimum difficulty

    def _calculate_urgency(self, metadata, review_data):
        """Calculate review urgency based on spaced repetition principles."""
        urgency = 1.0

        # Time-based urgency
        if review_data["last_reviewed"]:
            try:
                last_reviewed = datetime.fromisoformat(review_data["last_reviewed"].replace("Z", "+00:00"))
                days_since_review = (datetime.now() - last_reviewed).days

                # Exponential urgency growth based on spaced repetition intervals
                review_intervals = [1, 3, 7, 14, 30, 60, 120]
                expected_interval = review_intervals[min(review_data["review_count"], len(review_intervals) - 1)]

                if days_since_review > expected_interval:
                    overdue_factor = days_since_review / expected_interval
                    urgency *= 1.0 + overdue_factor

            except (ValueError, AttributeError):
                pass
        else:
            # Never reviewed = high urgency
            urgency += 1.0

        # Difficulty affects urgency (harder items need more frequent review)
        difficulty_score = self._calculate_difficulty_score(metadata, review_data)
        urgency *= 1.0 + difficulty_score * 0.2

        # Success rate affects urgency (poor performance = higher urgency)
        if review_data["success_rate"] < 0.8:
            urgency *= 1.3

        return urgency

    def _calculate_next_interval(self, review_count, success, success_rate):
        """Calculate the next review interval based on spaced repetition algorithms."""
        base_intervals = [1, 3, 7, 14, 30, 60, 120, 240]  # days

        # Get base interval
        base_interval = base_intervals[min(review_count - 1, len(base_intervals) - 1)]

        # Adjust based on success
        if success:
            # Success = increase interval
            if success_rate > 0.9:
                multiplier = 1.5  # High success rate = longer intervals
            elif success_rate > 0.7:
                multiplier = 1.2
            else:
                multiplier = 1.0  # Normal progression
        else:
            # Failure = decrease interval significantly
            multiplier = 0.3

        return max(1, int(base_interval * multiplier))

    def _mock_recall(self, context: RecallContext) -> List[RecallResult]:
        """Mock recall when metadata manager unavailable."""
        mock_results = [
            RecallResult(
                uid="mock_1",
                title="Introduction to Machine Learning",
                content_type="article",
                source="https://example.com/ml-intro",
                relevance_score=0.85,
                recall_reason="matches query, contains keywords",
                metadata={"tags": ["machine learning", "AI"], "word_count": 2500},
                recalled_at=datetime.now().isoformat(),
                snippet="A comprehensive introduction to machine learning concepts..."
            ),
            RecallResult(
                uid="mock_2",
                title="Remote Work Best Practices",
                content_type="article",
                source="https://example.com/remote-work",
                relevance_score=0.72,
                recall_reason="tagged as productivity, recently added",
                metadata={"tags": ["productivity", "remote work"], "word_count": 1800},
                recalled_at=datetime.now().isoformat(),
                snippet="Essential tips for effective remote work..."
            ),
            RecallResult(
                uid="mock_3",
                title="The Future of AI Podcast",
                content_type="podcast",
                source="https://example.com/ai-podcast",
                relevance_score=0.68,
                recall_reason="general match, high relevance",
                metadata={"tags": ["AI", "future"], "word_count": 8500},
                recalled_at=datetime.now().isoformat(),
                snippet="A deep dive into artificial intelligence trends..."
            )
        ]

        # Filter by context
        filtered = []
        for result in mock_results:
            # Apply content type filter
            if context.content_types and result.content_type not in context.content_types:
                continue

            # Apply relevance filter
            if result.relevance_score < context.min_relevance:
                continue

            # Apply query filter (simple check)
            if context.query:
                if context.query.lower() not in result.title.lower():
                    continue

            filtered.append(result)

        return filtered[:context.max_results]


if __name__ == "__main__":
    # Example usage
    engine = RecallEngine()

    # Quick search
    print("Quick Search Results:")
    print("=" * 40)
    quick_results = engine.quick_search("machine learning", max_results=3)

    for i, result in enumerate(quick_results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Type: {result.content_type}")
        print(f"   Relevance: {result.relevance_score:.2f}")
        print(f"   Reason: {result.recall_reason}")
        if result.snippet:
            print(f"   Snippet: {result.snippet}")

    # Contextual recall
    print(f"\n\nContextual Recall:")
    print("=" * 40)
    context = RecallContext(
        keywords=["productivity", "remote"],
        time_period="month",
        content_types=["article"],
        max_results=5
    )

    contextual_results = engine.recall(context)
    for i, result in enumerate(contextual_results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Relevance: {result.relevance_score:.2f}")
        print(f"   Reason: {result.recall_reason}")

    # Spaced repetition
    print(f"\n\nSpaced Repetition Review:")
    print("=" * 40)
    review_items = engine.get_items_for_review(limit=3)
    for i, item in enumerate(review_items, 1):
        print(f"\n{i}. {getattr(item.metadata, 'title', 'Unknown Title')}")
        print(f"   Urgency: {item.review_urgency:.2f}")
        print(f"   Difficulty: {item.difficulty_score:.2f}")

    # Get suggestions
    print(f"\n\nRecall Suggestions:")
    print("=" * 40)
    suggestions = engine.get_recall_suggestions()
    print(", ".join(suggestions))