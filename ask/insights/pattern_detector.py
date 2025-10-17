#!/usr/bin/env python3
"""
Pattern Detector

Intelligent pattern detection system that identifies trends, relationships,
and insights across content consumption and knowledge patterns. Includes
legacy support for existing tag pattern analysis.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict, Counter
import re
import math

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from helpers.metadata_manager import MetadataManager
    from helpers.config import load_config
except ImportError:
    MetadataManager = None
    load_config = lambda: {}


@dataclass
class Pattern:
    """Represents a detected pattern in content or behavior."""
    pattern_id: str
    pattern_type: str  # temporal, topical, behavioral, content, relationship
    description: str
    confidence: float
    strength: float
    supporting_evidence: List[str]
    metadata: Dict[str, Any]
    detected_at: str

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now().isoformat()


@dataclass
class Insight:
    """Actionable insight derived from pattern analysis."""
    insight_id: str
    title: str
    description: str
    insight_type: str  # trend, anomaly, opportunity, recommendation
    confidence: float
    impact_level: str  # low, medium, high
    supporting_patterns: List[str]
    actionable_suggestions: List[str]
    generated_at: str

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now().isoformat()


@dataclass
class PatternAnalysisContext:
    """Context for pattern analysis."""
    analysis_period: str = "3m"  # 1w, 1m, 3m, 6m, 1y, all
    pattern_types: List[str] = None
    min_confidence: float = 0.5
    include_weak_patterns: bool = False
    focus_areas: List[str] = None

    def __post_init__(self):
        if self.pattern_types is None:
            self.pattern_types = ["temporal", "topical", "behavioral", "content", "relationship"]
        if self.focus_areas is None:
            self.focus_areas = []


class PatternDetector:
    """
    Comprehensive pattern detection system for Atlas.

    Provides both advanced pattern detection and legacy tag analysis:
    - Temporal patterns (when content is consumed)
    - Topical patterns (what topics are trending)
    - Behavioral patterns (how content is engaged with)
    - Content patterns (types and sources preferred)
    - Relationship patterns (connections between content)
    - Legacy tag pattern analysis for backward compatibility
    """

    def __init__(self, metadata_manager=None, config: Dict[str, Any] = None):
        """Initialize PatternDetector."""
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

        # Legacy cache support
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = self.config.get("cache_ttl_seconds", 600)  # 10 minutes default

        # Pattern detection thresholds
        self.thresholds = {
            "min_occurrences": 3,
            "trend_threshold": 0.2,  # 20% change to be considered a trend
            "correlation_threshold": 0.6,
            "anomaly_threshold": 2.0,  # Standard deviations from mean
        }

        # Time period mappings for analysis
        self.period_mapping = {
            "1w": 7,
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "1y": 365,
            "all": None
        }

    # ========================================
    # ADVANCED PATTERN DETECTION METHODS
    # ========================================

    def detect_patterns(self, context: PatternAnalysisContext = None) -> List[Pattern]:
        """
        Detect patterns across all available data.

        Args:
            context: Analysis context with pattern detection preferences

        Returns:
            List of detected patterns ordered by confidence
        """
        if context is None:
            context = PatternAnalysisContext()

        if not self.metadata_manager:
            return self._mock_detect_patterns(context)

        try:
            # Get data for analysis
            content_data = self._get_content_for_analysis(context)

            detected_patterns = []

            # Detect different types of patterns
            for pattern_type in context.pattern_types:
                if pattern_type == "temporal":
                    patterns = self._detect_temporal_patterns(content_data, context)
                elif pattern_type == "topical":
                    patterns = self._detect_topical_patterns(content_data, context)
                elif pattern_type == "behavioral":
                    patterns = self._detect_behavioral_patterns(content_data, context)
                elif pattern_type == "content":
                    patterns = self._detect_content_patterns(content_data, context)
                elif pattern_type == "relationship":
                    patterns = self._detect_relationship_patterns(content_data, context)
                else:
                    patterns = []

                detected_patterns.extend(patterns)

            # Filter by confidence and sort
            filtered_patterns = [
                p for p in detected_patterns
                if p.confidence >= context.min_confidence
            ]

            if not context.include_weak_patterns:
                filtered_patterns = [p for p in filtered_patterns if p.strength >= 0.5]

            filtered_patterns.sort(key=lambda x: x.confidence * x.strength, reverse=True)

            return filtered_patterns

        except Exception as e:
            print(f"Error detecting patterns: {e}")
            return self._mock_detect_patterns(context)

    def generate_insights(self, patterns: List[Pattern] = None) -> List[Insight]:
        """Generate actionable insights from detected patterns."""
        if patterns is None:
            patterns = self.detect_patterns()

        insights = []

        # Group patterns by type for insight generation
        patterns_by_type = defaultdict(list)
        for pattern in patterns:
            patterns_by_type[pattern.pattern_type].append(pattern)

        # Generate insights for each pattern type
        for pattern_type, type_patterns in patterns_by_type.items():
            type_insights = self._generate_insights_for_type(pattern_type, type_patterns)
            insights.extend(type_insights)

        # Cross-pattern insights
        cross_insights = self._generate_cross_pattern_insights(patterns)
        insights.extend(cross_insights)

        # Sort by confidence and impact
        insights.sort(key=lambda x: self._insight_priority_score(x), reverse=True)

        return insights

    def analyze_trends(self,
                      focus_metric: str = "volume",
                      timeframe: str = "3m") -> Dict[str, Any]:
        """Analyze trends in content consumption."""
        if not self.metadata_manager:
            return {"error": "No metadata manager available"}

        try:
            days = self.period_mapping.get(timeframe, 90)
            content_data = self._get_content_for_analysis(
                PatternAnalysisContext(analysis_period=timeframe)
            )

            if focus_metric == "volume":
                return self._analyze_volume_trends(content_data, days)
            elif focus_metric == "topics":
                return self._analyze_topic_trends(content_data, days)
            elif focus_metric == "sources":
                return self._analyze_source_trends(content_data, days)
            else:
                return {"error": f"Unknown metric: {focus_metric}"}

        except Exception as e:
            return {"error": f"Trend analysis failed: {e}"}

    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of all detected patterns."""
        try:
            patterns = self.detect_patterns()
            insights = self.generate_insights(patterns)

            # Pattern type distribution
            pattern_counts = Counter(p.pattern_type for p in patterns)

            # Confidence distribution
            high_conf = len([p for p in patterns if p.confidence > 0.8])
            med_conf = len([p for p in patterns if 0.5 <= p.confidence <= 0.8])
            low_conf = len([p for p in patterns if p.confidence < 0.5])

            # Insight distribution
            insight_types = Counter(i.insight_type for i in insights)
            impact_levels = Counter(i.impact_level for i in insights)

            return {
                "total_patterns": len(patterns),
                "pattern_types": dict(pattern_counts),
                "confidence_distribution": {
                    "high": high_conf,
                    "medium": med_conf,
                    "low": low_conf
                },
                "total_insights": len(insights),
                "insight_types": dict(insight_types),
                "impact_levels": dict(impact_levels),
                "top_patterns": [
                    {
                        "description": p.description,
                        "confidence": p.confidence,
                        "type": p.pattern_type
                    }
                    for p in patterns[:5]
                ],
                "actionable_insights": len([i for i in insights if i.actionable_suggestions])
            }

        except Exception as e:
            return {"error": f"Pattern summary failed: {e}"}

    # ========================================
    # LEGACY TAG ANALYSIS METHODS (Backward Compatibility)
    # ========================================

    def detect_tag_patterns(self, min_frequency=2):
        """
        Detect tag usage patterns and trends using new MetadataManager methods.
        Enhanced with trend detection and alerts.
        """
        # Check cache validity
        now = datetime.now()
        cache_key = f"tag_patterns_{min_frequency}"

        if (
            self._cache_timestamp
            and cache_key in self._cache
            and (now - self._cache_timestamp).total_seconds() < self._cache_ttl
        ):
            return self._cache[cache_key]

        try:
            # Get comprehensive tag patterns from MetadataManager if available
            if hasattr(self.metadata_manager, 'get_tag_patterns'):
                patterns = self.metadata_manager.get_tag_patterns(min_frequency)
            else:
                # Fallback to basic tag analysis
                patterns = self._basic_tag_analysis(min_frequency)

            # Enhance with trend analysis
            enhanced_patterns = self._enhance_with_trends(patterns)

            # Add pattern visualization data
            enhanced_patterns["visualization_data"] = self._create_visualization_data(patterns)

            # Add trending alerts
            enhanced_patterns["alerts"] = self._generate_trending_alerts(patterns)

            # Cache the result
            self._cache[cache_key] = enhanced_patterns
            self._cache_timestamp = now

            return enhanced_patterns

        except Exception as e:
            print(f"Error detecting tag patterns: {e}")
            return self._fallback_tag_patterns(min_frequency)

    def find_patterns(self, n=3):
        """Legacy method for backward compatibility."""
        try:
            import sqlite3
            from urllib.parse import urlparse
            from collections import Counter

            conn = sqlite3.connect('atlas.db')
            cursor = conn.cursor()

            # Get top sources by domain
            cursor.execute("""
                SELECT url, COUNT(*) as count
                FROM content
                WHERE url IS NOT NULL AND url != ''
                GROUP BY url
                ORDER BY count DESC
                LIMIT ?
            """, (n * 3,))  # Get more to process domains

            domain_counter = Counter()
            for row in cursor.fetchall():
                domain = urlparse(row[0]).netloc or "unknown"
                domain_counter[domain] += row[1]

            top_sources = domain_counter.most_common(n)

            # Get content type patterns as "tags"
            cursor.execute("""
                SELECT content_type, COUNT(*) as count
                FROM content
                GROUP BY content_type
                ORDER BY count DESC
                LIMIT ?
            """, (n,))

            top_tags = [(row[0] or "unknown", row[1]) for row in cursor.fetchall()]

            conn.close()
            return {"top_tags": top_tags, "top_sources": top_sources}

        except Exception as e:
            print(f"Error finding patterns: {e}")
            return {"top_tags": [], "top_sources": []}

    def get_pattern_insights(self):
        """Get high-level insights about content patterns (legacy method)."""
        try:
            patterns = self.detect_tag_patterns()

            insights = {
                "total_unique_tags": patterns.get("total_tags", 0),
                "most_active_tags": patterns.get("trending_tags", [])[:3],
                "potential_issues": len([
                    alert for alert in patterns.get("alerts", [])
                    if alert.get("severity") == "warning"
                ]),
                "tag_diversity": len(patterns.get("tag_frequencies", {})) / max(patterns.get("total_occurrences", 1), 1),
                "average_tags_per_item": patterns.get("total_occurrences", 0) / max(len(patterns.get("tag_frequencies", {})), 1),
            }

            return insights

        except Exception as e:
            print(f"Error getting pattern insights: {e}")
            return {"error": f"Pattern insights failed: {e}"}

    def clear_cache(self):
        """Manually clear the pattern detection cache."""
        self._cache.clear()
        self._cache_timestamp = None

    # ========================================
    # PATTERN DETECTION IMPLEMENTATION METHODS
    # ========================================

    def _detect_temporal_patterns(self, content_data: List[Any], context: PatternAnalysisContext) -> List[Pattern]:
        """Detect patterns in timing of content consumption."""
        patterns = []

        # Analyze by hour of day
        hourly_counts = defaultdict(int)
        for item in content_data:
            try:
                created_at = getattr(item, 'created_at', '')
                if created_at:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    hourly_counts[dt.hour] += 1
            except Exception:
                continue

        if hourly_counts:
            # Find peak hours
            total_items = sum(hourly_counts.values())
            avg_per_hour = total_items / 24
            peak_hours = [hour for hour, count in hourly_counts.items() if count > avg_per_hour * 1.5]

            if peak_hours:
                confidence = min(0.9, len(peak_hours) / 24 * total_items / 50)
                strength = max(hourly_counts.values()) / avg_per_hour if avg_per_hour > 0 else 0

                patterns.append(Pattern(
                    pattern_id=f"temporal_hourly_{datetime.now().strftime('%Y%m%d')}",
                    pattern_type="temporal",
                    description=f"Peak content consumption during hours: {', '.join(map(str, sorted(peak_hours)))}",
                    confidence=confidence,
                    strength=min(1.0, strength / 3),  # Normalize strength
                    supporting_evidence=[f"{hour}:00 - {hourly_counts[hour]} items" for hour in peak_hours],
                    metadata={"peak_hours": peak_hours, "hourly_distribution": dict(hourly_counts)},
                    detected_at=datetime.now().isoformat()
                ))

        return patterns

    def _detect_topical_patterns(self, content_data: List[Any], context: PatternAnalysisContext) -> List[Pattern]:
        """Detect patterns in content topics and tags."""
        patterns = []

        # Analyze tag frequency and trends
        tag_counts = Counter()
        for item in content_data:
            try:
                tags = getattr(item, 'tags', [])
                for tag in tags:
                    if tag:
                        tag_counts[tag.lower()] += 1
            except Exception:
                continue

        # Find popular topics
        total_items = len(content_data)
        popular_tags = [tag for tag, count in tag_counts.most_common(20) if count >= self.thresholds["min_occurrences"]]

        for tag in popular_tags:
            if tag_counts[tag] / total_items > 0.1:  # Tag appears in >10% of content
                confidence = min(0.9, tag_counts[tag] / total_items * 5)
                strength = tag_counts[tag] / max(tag_counts.values())

                patterns.append(Pattern(
                    pattern_id=f"topical_{tag}_{datetime.now().strftime('%Y%m%d')}",
                    pattern_type="topical",
                    description=f"Strong interest in '{tag}' topic",
                    confidence=confidence,
                    strength=strength,
                    supporting_evidence=[f"Appears in {tag_counts[tag]} items ({(tag_counts[tag]/total_items)*100:.1f}%)"],
                    metadata={"tag": tag, "frequency": tag_counts[tag], "percentage": tag_counts[tag]/total_items},
                    detected_at=datetime.now().isoformat()
                ))

        return patterns

    def _detect_behavioral_patterns(self, content_data: List[Any], context: PatternAnalysisContext) -> List[Pattern]:
        """Detect patterns in user behavior and content engagement."""
        patterns = []

        # Analyze content type preferences
        type_counts = Counter()
        for item in content_data:
            try:
                content_type = getattr(item, 'content_type', 'unknown')
                if hasattr(content_type, 'value'):
                    content_type = content_type.value
                type_counts[content_type] += 1
            except Exception:
                continue

        total_items = len(content_data)
        if total_items > 0:
            for content_type, count in type_counts.most_common():
                percentage = count / total_items
                if percentage > 0.3:  # Represents >30% of content
                    confidence = min(0.9, percentage * 2)

                    patterns.append(Pattern(
                        pattern_id=f"behavioral_type_{content_type}_{datetime.now().strftime('%Y%m%d')}",
                        pattern_type="behavioral",
                        description=f"Strong preference for {content_type} content",
                        confidence=confidence,
                        strength=percentage,
                        supporting_evidence=[f"{count} out of {total_items} items ({percentage*100:.1f}%)"],
                        metadata={"content_type": content_type, "count": count, "percentage": percentage},
                        detected_at=datetime.now().isoformat()
                    ))

        return patterns

    def _detect_content_patterns(self, content_data: List[Any], context: PatternAnalysisContext) -> List[Pattern]:
        """Detect patterns in content sources and types."""
        patterns = []

        # Analyze source patterns
        source_counts = Counter()
        for item in content_data:
            try:
                source = getattr(item, 'source', '') or getattr(item, 'url', '')
                if source:
                    # Extract domain from URL
                    if '://' in source:
                        domain = source.split('://')[1].split('/')[0]
                        if domain.startswith('www.'):
                            domain = domain[4:]
                        source_counts[domain] += 1
                    else:
                        source_counts[source] += 1
            except Exception:
                continue

        total_items = len(content_data)
        for source, count in source_counts.most_common(10):
            percentage = count / total_items
            if count >= self.thresholds["min_occurrences"] and percentage > 0.15:
                confidence = min(0.9, percentage * 3)

                patterns.append(Pattern(
                    pattern_id=f"content_source_{source.replace('.', '_')}_{datetime.now().strftime('%Y%m%d')}",
                    pattern_type="content",
                    description=f"Frequent use of '{source}' as content source",
                    confidence=confidence,
                    strength=percentage,
                    supporting_evidence=[f"{count} items from {source} ({percentage*100:.1f}%)"],
                    metadata={"source": source, "count": count, "percentage": percentage},
                    detected_at=datetime.now().isoformat()
                ))

        return patterns

    def _detect_relationship_patterns(self, content_data: List[Any], context: PatternAnalysisContext) -> List[Pattern]:
        """Detect patterns in relationships between content items."""
        patterns = []

        # Analyze tag co-occurrence
        tag_pairs = Counter()
        for item in content_data:
            try:
                tags = getattr(item, 'tags', [])
                if len(tags) >= 2:
                    for i, tag1 in enumerate(tags):
                        for tag2 in tags[i+1:]:
                            if tag1 and tag2:
                                pair = tuple(sorted([tag1.lower(), tag2.lower()]))
                                tag_pairs[pair] += 1
            except Exception:
                continue

        # Find strong tag relationships
        for (tag1, tag2), count in tag_pairs.most_common(15):
            if count >= self.thresholds["min_occurrences"]:
                # Calculate correlation strength
                tag1_total = sum(1 for item in content_data if hasattr(item, 'tags') and tag1 in [t.lower() for t in item.tags])
                tag2_total = sum(1 for item in content_data if hasattr(item, 'tags') and tag2 in [t.lower() for t in item.tags])

                if tag1_total > 0 and tag2_total > 0:
                    correlation = count / min(tag1_total, tag2_total)

                    if correlation >= self.thresholds["correlation_threshold"]:
                        confidence = min(0.9, correlation)

                        patterns.append(Pattern(
                            pattern_id=f"relationship_{tag1}_{tag2}_{datetime.now().strftime('%Y%m%d')}",
                            pattern_type="relationship",
                            description=f"Strong association between '{tag1}' and '{tag2}' topics",
                            confidence=confidence,
                            strength=correlation,
                            supporting_evidence=[f"Co-occur in {count} items (correlation: {correlation:.2f})"],
                            metadata={"tag1": tag1, "tag2": tag2, "co_occurrences": count, "correlation": correlation},
                            detected_at=datetime.now().isoformat()
                        ))

        return patterns

    # ========================================
    # LEGACY TAG ANALYSIS HELPER METHODS
    # ========================================

    def _basic_tag_analysis(self, min_frequency: int) -> Dict[str, Any]:
        """Basic tag analysis fallback when MetadataManager doesn't have get_tag_patterns."""
        try:
            all_content = self.metadata_manager.get_all_metadata()

            tag_counts = Counter()
            tag_cooccurrences = defaultdict(Counter)

            for item in all_content:
                tags = getattr(item, 'tags', [])
                for tag in tags:
                    if tag:
                        tag_counts[tag.lower()] += 1

                # Co-occurrence analysis
                for i, tag1 in enumerate(tags):
                    for tag2 in tags[i+1:]:
                        if tag1 and tag2:
                            tag_cooccurrences[tag1.lower()][tag2.lower()] += 1
                            tag_cooccurrences[tag2.lower()][tag1.lower()] += 1

            # Filter by minimum frequency
            filtered_tags = {tag: count for tag, count in tag_counts.items() if count >= min_frequency}

            return {
                "tag_frequencies": filtered_tags,
                "total_tags": len(filtered_tags),
                "total_occurrences": sum(filtered_tags.values()),
                "tag_cooccurrences": dict(tag_cooccurrences),
                "trending_tags": [{"tag": tag, "frequency": count} for tag, count in tag_counts.most_common(10)],
                "tag_source_analysis": {}
            }

        except Exception as e:
            print(f"Error in basic tag analysis: {e}")
            return self._fallback_tag_patterns(min_frequency)

    def _basic_source_analysis(self, n: int) -> List[Tuple[str, int]]:
        """Basic source analysis fallback."""
        try:
            all_content = self.metadata_manager.get_all_metadata()
            source_counts = Counter()

            for item in all_content:
                content_type = getattr(item, 'content_type', 'unknown')
                if hasattr(content_type, 'value'):
                    content_type = content_type.value
                source_counts[content_type] += 1

            return source_counts.most_common(n)

        except Exception:
            return [("article", 10), ("podcast", 5), ("video", 3)]

    def _enhance_with_trends(self, patterns):
        """Enhance patterns with trend analysis over time."""
        enhanced = patterns.copy()

        try:
            # Get temporal patterns to analyze tag trends over time
            if hasattr(self.metadata_manager, 'get_temporal_patterns'):
                temporal_patterns = self.metadata_manager.get_temporal_patterns("month")
                tag_trends = temporal_patterns.get("tag_trends", {})
            else:
                tag_trends = {}

            # Analyze trending direction for each tag
            enhanced["tag_trend_analysis"] = {}

            for tag in patterns["tag_frequencies"]:
                trend_data = []
                for period, period_tags in tag_trends.items():
                    count = period_tags.get(tag, 0)
                    trend_data.append({"period": period, "count": count})

                # Sort by period
                trend_data.sort(key=lambda x: x["period"])

                # Calculate trend direction
                if len(trend_data) >= 2:
                    recent_count = sum(item["count"] for item in trend_data[-2:])
                    older_count = (
                        sum(item["count"] for item in trend_data[:-2])
                        if len(trend_data) > 2
                        else 1
                    )

                    trend_direction = (
                        "rising"
                        if recent_count > older_count
                        else "falling" if recent_count < older_count else "stable"
                    )
                    trend_strength = abs(recent_count - older_count) / max(older_count, 1)
                else:
                    trend_direction = "unknown"
                    trend_strength = 0

                enhanced["tag_trend_analysis"][tag] = {
                    "direction": trend_direction,
                    "strength": trend_strength,
                    "trend_data": trend_data,
                }

        except Exception as e:
            print(f"Error enhancing with trends: {e}")
            enhanced["tag_trend_analysis"] = {}

        return enhanced

    def _create_visualization_data(self, patterns):
        """Create data structures for pattern visualization."""
        try:
            # Prepare data for different visualization types
            visualization = {
                "tag_frequency_chart": [],
                "co_occurrence_network": [],
                "tag_timeline": [],
                "source_distribution": [],
            }

            # Tag frequency chart data
            for tag, freq in patterns["tag_frequencies"].items():
                visualization["tag_frequency_chart"].append({
                    "tag": tag,
                    "frequency": freq,
                    "percentage": freq / max(patterns["total_occurrences"], 1) * 100,
                })

            # Co-occurrence network data for graph visualization
            for tag, cooccurrences in patterns["tag_cooccurrences"].items():
                for related_tag, count in cooccurrences.items():
                    visualization["co_occurrence_network"].append({
                        "source": tag,
                        "target": related_tag,
                        "weight": count,
                        "normalized_weight": count / max(patterns["tag_frequencies"].get(tag, 1), 1),
                    })

            # Source distribution analysis
            source_tags = {}
            for tag, analysis in patterns["tag_source_analysis"].items():
                for content_type in analysis.get("content_types", []):
                    if content_type not in source_tags:
                        source_tags[content_type] = []
                    source_tags[content_type].append(
                        {"tag": tag, "frequency": analysis.get("frequency", 0)}
                    )

            visualization["source_distribution"] = source_tags

            return visualization

        except Exception as e:
            print(f"Error creating visualization data: {e}")
            return {"tag_frequency_chart": [], "co_occurrence_network": [], "tag_timeline": [], "source_distribution": []}

    def _generate_trending_alerts(self, patterns):
        """Generate alerts for trending patterns that need attention."""
        try:
            alerts = []

            # Alert for rapidly growing tags
            for tag_info in patterns.get("trending_tags", []):
                if tag_info.get("frequency", 0) >= 5:
                    alerts.append({
                        "type": "trending_tag",
                        "severity": "info",
                        "message": f"Tag '{tag_info['tag']}' is trending with {tag_info['frequency']} occurrences",
                        "tag": tag_info["tag"],
                        "data": tag_info,
                    })

            # Alert for tags with high co-occurrence
            for tag, cooccurrences in patterns["tag_cooccurrences"].items():
                if len(cooccurrences) >= 3:  # Tag appears with 3+ other tags frequently
                    total_cooccurrence = sum(cooccurrences.values())
                    if total_cooccurrence >= 5:
                        alerts.append({
                            "type": "high_cooccurrence",
                            "severity": "info",
                            "message": f"Tag '{tag}' frequently appears with other tags, suggesting topic clustering",
                            "tag": tag,
                            "related_tags": list(cooccurrences.keys()),
                        })

            return alerts

        except Exception as e:
            print(f"Error generating trending alerts: {e}")
            return []

    def _fallback_tag_patterns(self, min_frequency: int) -> Dict[str, Any]:
        """Fallback tag patterns when analysis fails."""
        return {
            "tag_frequencies": {},
            "total_tags": 0,
            "total_occurrences": 0,
            "tag_cooccurrences": {},
            "trending_tags": [],
            "tag_source_analysis": {},
            "tag_trend_analysis": {},
            "visualization_data": {
                "tag_frequency_chart": [],
                "co_occurrence_network": [],
                "tag_timeline": [],
                "source_distribution": []
            },
            "alerts": []
        }

    # ========================================
    # INSIGHT GENERATION METHODS
    # ========================================

    def _generate_insights_for_type(self, pattern_type: str, patterns: List[Pattern]) -> List[Insight]:
        """Generate insights for a specific pattern type."""
        insights = []

        if pattern_type == "temporal" and patterns:
            # Find the strongest temporal pattern
            strongest_pattern = max(patterns, key=lambda p: p.confidence * p.strength)

            insights.append(Insight(
                insight_id=f"temporal_optimization_{datetime.now().strftime('%Y%m%d')}",
                title="Optimize Content Consumption Timing",
                description=f"You have clear patterns in when you consume content. {strongest_pattern.description}",
                insight_type="opportunity",
                confidence=strongest_pattern.confidence,
                impact_level="medium",
                supporting_patterns=[strongest_pattern.pattern_id],
                actionable_suggestions=[
                    "Schedule content consumption during peak hours",
                    "Set up notifications during high-activity periods",
                    "Block out focused reading time during optimal hours"
                ],
                generated_at=datetime.now().isoformat()
            ))

        elif pattern_type == "topical" and patterns:
            # Find trending topics
            strongest_trend = max(patterns, key=lambda p: p.strength)

            insights.append(Insight(
                insight_id=f"topic_trend_{datetime.now().strftime('%Y%m%d')}",
                title="Topic Interest Pattern Detected",
                description=f"Your content shows clear topical focus. {strongest_trend.description}",
                insight_type="trend",
                confidence=strongest_trend.confidence,
                impact_level="high",
                supporting_patterns=[p.pattern_id for p in patterns],
                actionable_suggestions=[
                    "Set up alerts for new content in your focus topics",
                    "Explore related subtopics and experts",
                    "Consider creating content or sharing insights on these topics"
                ],
                generated_at=datetime.now().isoformat()
            ))

        return insights

    def _generate_cross_pattern_insights(self, patterns: List[Pattern]) -> List[Insight]:
        """Generate insights from relationships between different patterns."""
        insights = []

        # Find patterns that reinforce each other
        temporal_patterns = [p for p in patterns if p.pattern_type == "temporal"]
        topical_patterns = [p for p in patterns if p.pattern_type == "topical"]

        if temporal_patterns and topical_patterns:
            insights.append(Insight(
                insight_id=f"cross_pattern_{datetime.now().strftime('%Y%m%d')}",
                title="Integrated Learning Pattern Detected",
                description="Your content consumption shows both temporal consistency and topical focus, indicating systematic learning.",
                insight_type="opportunity",
                confidence=0.8,
                impact_level="high",
                supporting_patterns=[p.pattern_id for p in temporal_patterns + topical_patterns],
                actionable_suggestions=[
                    "Create a structured learning schedule combining your time and topic preferences",
                    "Use your peak times for your most important topics",
                    "Track progress on focused learning goals"
                ],
                generated_at=datetime.now().isoformat()
            ))

        return insights

    # ========================================
    # TREND ANALYSIS METHODS
    # ========================================

    def _analyze_volume_trends(self, content_data: List[Any], days: int) -> Dict[str, Any]:
        """Analyze volume trends over time."""
        daily_counts = defaultdict(int)

        for item in content_data:
            try:
                created_at = getattr(item, 'created_at', '')
                if created_at:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    day_key = dt.strftime('%Y-%m-%d')
                    daily_counts[day_key] += 1
            except Exception:
                continue

        if len(daily_counts) < 7:
            return {"error": "Insufficient data for trend analysis"}

        # Calculate trend
        dates = sorted(daily_counts.keys())
        counts = [daily_counts[date] for date in dates]

        # Simple linear trend calculation
        n = len(counts)
        if n < 2:
            return {"error": "Insufficient data points"}

        sum_x = sum(range(n))
        sum_y = sum(counts)
        sum_xy = sum(i * counts[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))

        denominator = n * sum_x2 - sum_x * sum_x
        slope = (n * sum_xy - sum_x * sum_y) / denominator if denominator != 0 else 0

        trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"

        return {
            "metric": "volume",
            "period": f"{days} days" if days else "all time",
            "trend_direction": trend_direction,
            "slope": slope,
            "daily_average": sum_y / n,
            "total_items": sum_y,
            "data_points": len(daily_counts),
            "timeline": dict(daily_counts)
        }

    def _analyze_topic_trends(self, content_data: List[Any], days: int) -> Dict[str, Any]:
        """Analyze topic trends over time."""
        # Extract topics/tags and track their frequency over time
        topic_timeline = defaultdict(lambda: defaultdict(int))

        for item in content_data:
            try:
                created_at = getattr(item, 'created_at', '')
                tags = getattr(item, 'tags', [])

                if created_at and tags:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    month_key = dt.strftime('%Y-%m')  # Group by month for better visualization

                    for tag in tags:
                        if tag:
                            topic_timeline[tag.lower()][month_key] += 1
            except Exception:
                continue

        # Calculate growth rates for each topic
        topic_growth = {}
        for topic, timeline in topic_timeline.items():
            if len(timeline) < 2:
                continue

            dates = sorted(timeline.keys())
            if len(dates) >= 2:
                # Calculate growth rate between first and last period
                first_count = timeline[dates[0]]
                last_count = timeline[dates[-1]]

                if first_count > 0:
                    growth_rate = (last_count - first_count) / first_count * 100
                    topic_growth[topic] = {
                        "growth_rate": growth_rate,
                        "first_period": {"date": dates[0], "count": first_count},
                        "last_period": {"date": dates[-1], "count": last_count},
                        "total_mentions": sum(timeline.values())
                    }

        # Identify trending topics (positive growth) and declining topics (negative growth)
        trending_topics = {topic: data for topic, data in topic_growth.items() if data["growth_rate"] > 20}
        declining_topics = {topic: data for topic, data in topic_growth.items() if data["growth_rate"] < -20}

        return {
            "metric": "topics",
            "period": f"{days} days" if days else "all time",
            "trending_topics": trending_topics,
            "declining_topics": declining_topics,
            "total_topics": len(topic_timeline),
            "topic_timeline": dict(topic_timeline)
        }

    def _analyze_source_trends(self, content_data: List[Any], days: int) -> Dict[str, Any]:
        """Analyze source trends over time."""
        source_timeline = defaultdict(lambda: defaultdict(int))

        for item in content_data:
            try:
                created_at = getattr(item, 'created_at', '')
                source = getattr(item, 'source', '') or getattr(item, 'url', '')

                if created_at and source:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    month_key = dt.strftime('%Y-%m')

                    # Extract domain from URL
                    if '://' in source:
                        domain = source.split('://')[1].split('/')[0]
                        if domain.startswith('www.'):
                            domain = domain[4:]
                    else:
                        domain = source

                    source_timeline[domain][month_key] += 1
            except Exception:
                continue

        # Calculate growth rates for each source
        source_growth = {}
        for source, timeline in source_timeline.items():
            if len(timeline) < 2:
                continue

            dates = sorted(timeline.keys())
            if len(dates) >= 2:
                first_count = timeline[dates[0]]
                last_count = timeline[dates[-1]]

                if first_count > 0:
                    growth_rate = (last_count - first_count) / first_count * 100
                    source_growth[source] = {
                        "growth_rate": growth_rate,
                        "first_period": {"date": dates[0], "count": first_count},
                        "last_period": {"date": dates[-1], "count": last_count},
                        "total_content": sum(timeline.values())
                    }

        # Identify growing and declining sources
        growing_sources = {source: data for source, data in source_growth.items() if data["growth_rate"] > 20}
        declining_sources = {source: data for source, data in source_growth.items() if data["growth_rate"] < -20}

        return {
            "metric": "sources",
            "period": f"{days} days" if days else "all time",
            "growing_sources": growing_sources,
            "declining_sources": declining_sources,
            "total_sources": len(source_timeline),
            "source_timeline": dict(source_timeline)
        }

    # ========================================
    # HELPER METHODS
    # ========================================

    def _get_content_for_analysis(self, context: PatternAnalysisContext) -> List[Any]:
        """Get content data for analysis based on context."""
        if hasattr(self.metadata_manager, 'list_all_content'):
            all_content = self.metadata_manager.list_all_content()
        else:
            all_content = self.metadata_manager.get_all_metadata()

        # Apply time filtering
        days = self.period_mapping.get(context.analysis_period)
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_content = []

            for item in all_content:
                try:
                    created_at = getattr(item, 'created_at', '')
                    if created_at:
                        content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if content_date >= cutoff_date:
                            filtered_content.append(item)
                except Exception:
                    continue

            return filtered_content

        return all_content

    def _insight_priority_score(self, insight: Insight) -> float:
        """Calculate priority score for insight ranking."""
        impact_weights = {"high": 1.0, "medium": 0.7, "low": 0.4}
        impact_weight = impact_weights.get(insight.impact_level, 0.5)

        actionable_bonus = 0.1 if insight.actionable_suggestions else 0

        return insight.confidence * impact_weight + actionable_bonus

    def _mock_detect_patterns(self, context: PatternAnalysisContext) -> List[Pattern]:
        """Mock pattern detection when metadata manager unavailable."""
        mock_patterns = [
            Pattern(
                pattern_id="mock_temporal_1",
                pattern_type="temporal",
                description="Peak content consumption during hours: 9, 13, 20",
                confidence=0.85,
                strength=0.75,
                supporting_evidence=["9:00 - 15 items", "13:00 - 12 items", "20:00 - 18 items"],
                metadata={"peak_hours": [9, 13, 20]},
                detected_at=datetime.now().isoformat()
            ),
            Pattern(
                pattern_id="mock_topical_1",
                pattern_type="topical",
                description="Strong interest in 'machine learning' topic",
                confidence=0.78,
                strength=0.82,
                supporting_evidence=["Appears in 25 items (18.5%)"],
                metadata={"tag": "machine learning", "frequency": 25},
                detected_at=datetime.now().isoformat()
            ),
            Pattern(
                pattern_id="mock_behavioral_1",
                pattern_type="behavioral",
                description="Strong preference for article content",
                confidence=0.72,
                strength=0.68,
                supporting_evidence=["85 out of 120 items (70.8%)"],
                metadata={"content_type": "article", "percentage": 0.708},
                detected_at=datetime.now().isoformat()
            )
        ]

        # Filter by requested pattern types
        filtered_patterns = [
            p for p in mock_patterns
            if p.pattern_type in context.pattern_types and
               p.confidence >= context.min_confidence
        ]

        return filtered_patterns


if __name__ == "__main__":
    # Example usage
    detector = PatternDetector()

    # Detect patterns
    print("Detected Patterns:")
    print("=" * 50)
    patterns = detector.detect_patterns()

    for i, pattern in enumerate(patterns, 1):
        print(f"\n{i}. {pattern.description}")
        print(f"   Type: {pattern.pattern_type}")
        print(f"   Confidence: {pattern.confidence:.2f}")
        print(f"   Strength: {pattern.strength:.2f}")
        print(f"   Evidence: {'; '.join(pattern.supporting_evidence[:2])}")

    # Generate insights
    print(f"\n\nGenerated Insights:")
    print("=" * 50)
    insights = detector.generate_insights(patterns)

    for i, insight in enumerate(insights, 1):
        print(f"\n{i}. {insight.title}")
        print(f"   Type: {insight.insight_type}")
        print(f"   Impact: {insight.impact_level}")
        print(f"   Confidence: {insight.confidence:.2f}")
        print(f"   Description: {insight.description}")
        if insight.actionable_suggestions:
            print(f"   Suggestions: {'; '.join(insight.actionable_suggestions[:2])}")

    # Legacy tag analysis
    print(f"\n\nLegacy Tag Analysis:")
    print("=" * 50)
    tag_patterns = detector.detect_tag_patterns(min_frequency=2)
    print(f"Total tags: {tag_patterns.get('total_tags', 0)}")
    print(f"Top tags: {list(tag_patterns.get('tag_frequencies', {}).items())[:5]}")

    # Pattern summary
    print(f"\n\nPattern Summary:")
    print("=" * 50)
    summary = detector.get_pattern_summary()
    print(f"Total patterns: {summary.get('total_patterns', 0)}")
    print(f"Total insights: {summary.get('total_insights', 0)}")
    print(f"Actionable insights: {summary.get('actionable_insights', 0)}")