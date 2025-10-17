#!/usr/bin/env python3
"""
Temporal Pattern Analysis Engine

Analyzes temporal patterns in content consumption and provides time-based insights.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from helpers.metadata_manager import MetadataManager
    from helpers.config import load_config
except ImportError:
    MetadataManager = None
    load_config = lambda: {}


@dataclass
class TemporalPattern:
    """Represents a discovered temporal pattern."""
    pattern_type: str  # daily, weekly, monthly, seasonal
    pattern_data: Dict[str, Any]
    confidence: float
    frequency: int
    last_occurrence: str
    description: str


@dataclass
class TemporalInsight:
    """Time-based insight about content consumption."""
    insight_type: str
    title: str
    description: str
    confidence: float
    supporting_data: Dict[str, Any]
    action_suggestions: List[str]
    discovered_at: str

    def __post_init__(self):
        if self.discovered_at is None:
            self.discovered_at = datetime.now().isoformat()


@dataclass
class TimeContext:
    """Context for temporal analysis."""
    analysis_period: str = "30d"  # 7d, 30d, 90d, 1y
    time_zones: List[str] = None
    granularity: str = "hour"  # hour, day, week, month
    include_weekends: bool = True
    content_types: List[str] = None

    def __post_init__(self):
        if self.time_zones is None:
            self.time_zones = ["UTC"]
        if self.content_types is None:
            self.content_types = ["article", "podcast", "video"]


class TemporalEngine:
    """
    Temporal pattern analysis engine for Atlas.

    Analyzes when content is consumed, discovers patterns,
    and provides time-based insights and recommendations.
    """

    def __init__(self, metadata_manager=None, config: Dict[str, Any] = None):
        """Initialize TemporalEngine."""
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

    def analyze_patterns(self, context: TimeContext = None) -> List[TemporalPattern]:
        """
        Analyze temporal patterns in content consumption.

        Args:
            context: Time context for analysis

        Returns:
            List of discovered temporal patterns
        """
        if context is None:
            context = TimeContext()

        if not self.metadata_manager:
            return self._mock_analyze_patterns(context)

        try:
            # Get content within analysis period
            content_items = self._get_content_for_period(context)

            patterns = []

            # Analyze daily patterns
            daily_patterns = self._analyze_daily_patterns(content_items)
            patterns.extend(daily_patterns)

            # Analyze weekly patterns
            weekly_patterns = self._analyze_weekly_patterns(content_items)
            patterns.extend(weekly_patterns)

            # Analyze content type patterns
            type_patterns = self._analyze_content_type_patterns(content_items)
            patterns.extend(type_patterns)

            # Analyze reading time patterns
            time_patterns = self._analyze_reading_time_patterns(content_items)
            patterns.extend(time_patterns)

            return sorted(patterns, key=lambda x: x.confidence, reverse=True)

        except Exception as e:
            print(f"Error analyzing patterns: {e}")
            return self._mock_analyze_patterns(context)

    def generate_insights(self, patterns: List[TemporalPattern] = None) -> List[TemporalInsight]:
        """Generate actionable insights from temporal patterns."""
        if patterns is None:
            patterns = self.analyze_patterns()

        insights = []

        for pattern in patterns:
            if pattern.confidence < 0.6:
                continue

            insight = self._pattern_to_insight(pattern)
            if insight:
                insights.append(insight)

        # Add time-based recommendations
        schedule_insights = self._generate_schedule_insights(patterns)
        insights.extend(schedule_insights)

        return sorted(insights, key=lambda x: x.confidence, reverse=True)

    def analyze_productivity_cycles(self) -> Dict[str, Any]:
        """Analyze productivity cycles based on content consumption patterns."""
        patterns = self.analyze_patterns()

        # Identify peak productivity hours from daily patterns
        daily_patterns = [p for p in patterns if p.pattern_type == "daily"]
        productivity_hours = []

        for pattern in daily_patterns:
            peak_hours = pattern.pattern_data.get("peak_hours", [])
            hourly_activity = pattern.pattern_data.get("hourly_activity", {})

            # Find hours with above-average activity
            avg_activity = sum(hourly_activity.values()) / len(hourly_activity) if hourly_activity else 0
            productive_hours = [hour for hour, count in hourly_activity.items() if count > avg_activity * 1.2]
            productivity_hours.extend(productive_hours)

        # Identify weekly productivity patterns
        weekly_patterns = [p for p in patterns if p.pattern_type == "weekly"]
        productive_days = []

        for pattern in weekly_patterns:
            peak_days = pattern.pattern_data.get("peak_days", [])
            weekday_activity = pattern.pattern_data.get("weekday_activity", {})

            # Find days with above-average activity
            avg_activity = sum(weekday_activity.values()) / len(weekday_activity) if weekday_activity else 0
            productive_days = [day for day, count in weekday_activity.items() if count > avg_activity * 1.1]

        # Categorize productivity periods
        morning_hours = [h for h in productivity_hours if 6 <= h <= 11]
        afternoon_hours = [h for h in productivity_hours if 12 <= h <= 17]
        evening_hours = [h for h in productivity_hours if 18 <= h <= 23]

        return {
            "peak_hours": sorted(list(set(productivity_hours))),
            "productive_days": productive_days,
            "morning_productivity": len(morning_hours) > 0,
            "afternoon_productivity": len(afternoon_hours) > 0,
            "evening_productivity": len(evening_hours) > 0,
            "optimal_focus_blocks": self._suggest_focus_blocks(productivity_hours),
            "weekly_pattern": "weekday" if all(d < 5 for d in productive_days) else "mixed"
        }

    def _suggest_focus_blocks(self, productive_hours: List[int]) -> List[Tuple[int, int]]:
        """Suggest optimal focus blocks based on productive hours."""
        if not productive_hours:
            return [(9, 11), (14, 16)]  # Default focus blocks

        # Group consecutive hours into blocks
        productive_hours = sorted(list(set(productive_hours)))
        blocks = []
        start = productive_hours[0]
        end = start

        for hour in productive_hours[1:]:
            if hour == end + 1:
                end = hour
            else:
                blocks.append((start, end))
                start = hour
                end = hour
        blocks.append((start, end))

        # Limit to 2-3 best blocks
        return blocks[:3]

    def get_optimal_times(self, content_type: str = None) -> List[Tuple[int, float]]:
        """
        Get optimal times for content consumption.

        Returns:
            List of (hour, confidence) tuples
        """
        patterns = self.analyze_patterns()

        time_scores = defaultdict(float)

        for pattern in patterns:
            if pattern.pattern_type == "daily" and pattern.confidence > 0.5:
                if content_type is None or pattern.pattern_data.get("content_type") == content_type:
                    for hour, activity in pattern.pattern_data.get("hourly_activity", {}).items():
                        time_scores[int(hour)] += activity * pattern.confidence

        # Normalize scores
        if time_scores:
            max_score = max(time_scores.values())
            time_scores = {hour: score/max_score for hour, score in time_scores.items()}

        return sorted(time_scores.items(), key=lambda x: x[1], reverse=True)

    def predict_next_session(self) -> Dict[str, Any]:
        """Predict when the next content session is likely."""
        patterns = self.analyze_patterns()

        now = datetime.now()
        current_hour = now.hour
        current_weekday = now.weekday()

        # Find patterns for current time context
        relevant_patterns = []
        for pattern in patterns:
            if pattern.pattern_type in ["daily", "weekly"] and pattern.confidence > 0.5:
                relevant_patterns.append(pattern)

        if not relevant_patterns:
            return {
                "predicted_time": None,
                "confidence": 0.0,
                "reasoning": "Insufficient pattern data"
            }

        # Simple prediction based on strongest patterns
        next_hours = []
        confidences = []

        for pattern in relevant_patterns[:3]:  # Top 3 patterns
            if pattern.pattern_type == "daily":
                hourly_data = pattern.pattern_data.get("hourly_activity", {})
                for hour_str, activity in hourly_data.items():
                    hour = int(hour_str)
                    if hour > current_hour:  # Future hour today
                        next_hours.append(hour)
                        confidences.append(activity * pattern.confidence)
                        break

        if next_hours:
            # Weight by confidence and select most likely
            best_idx = max(range(len(confidences)), key=confidences.__getitem__)
            predicted_hour = next_hours[best_idx]

            predicted_time = now.replace(hour=predicted_hour, minute=0, second=0, microsecond=0)

            return {
                "predicted_time": predicted_time.isoformat(),
                "confidence": confidences[best_idx],
                "reasoning": f"Based on {len(relevant_patterns)} temporal patterns"
            }

        return {
            "predicted_time": None,
            "confidence": 0.0,
            "reasoning": "No strong future patterns found"
        }

    # Legacy methods for backward compatibility
    def find_temporal_relationships(self, max_delta_days=7):
        """Legacy method - find temporal relationships using enhanced MetadataManager methods."""
        if not self.metadata_manager:
            return {"relationships": [], "temporal_patterns": {}, "seasonal_insights": {}, "content_velocity": {}}

        try:
            # Use the new temporal patterns method if available
            if hasattr(self.metadata_manager, 'get_temporal_patterns'):
                temporal_patterns = self.metadata_manager.get_temporal_patterns("week")
            else:
                temporal_patterns = {}

            # Get all metadata for relationship analysis
            all_items = self.metadata_manager.get_all_metadata()

            # Enhanced temporal relationship detection
            relationships = self._detect_temporal_clusters(all_items, max_delta_days)

            # Add temporal pattern insights
            insights = {
                "relationships": relationships,
                "temporal_patterns": temporal_patterns,
                "seasonal_insights": self._analyze_seasonal_patterns(temporal_patterns),
                "content_velocity": self._calculate_content_velocity(temporal_patterns),
            }

            return insights
        except Exception as e:
            print(f"Error in find_temporal_relationships: {e}")
            return {"relationships": [], "temporal_patterns": {}, "seasonal_insights": {}, "content_velocity": {}}

    def get_time_aware_relationships(self, max_delta_days=1):
        """Get time-aware relationships - existing method."""
        try:
            insights = self.find_temporal_relationships(max_delta_days)
            relationships = insights["relationships"]

            # Convert to tuple format expected by web interface
            result = []
            for rel in relationships[:10]:  # Limit results
                item1 = type('Item', (), {'title': rel.get('content1', 'Unknown')})()
                item2 = type('Item', (), {'title': rel.get('content2', 'Unknown')})()
                days = rel.get('time_delta_days', 0)
                result.append((item1, item2, days))
            return result
        except Exception as e:
            print(f"Error in get_time_aware_relationships: {e}")
            return []

    def identify_temporal_relationships(self, n=10):
        """Alias for web interface compatibility."""
        return self.get_time_aware_relationships(max_delta_days=7)  # Broader search

        # Convert to old format
        return [
            (rel["item1"], rel["item2"], rel["time_delta_days"])
            for rel in relationships
        ]

    def _get_content_for_period(self, context: TimeContext) -> List[Dict[str, Any]]:
        """Get content items for the analysis period."""
        # Parse period
        period_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = period_map.get(context.analysis_period, 30)

        cutoff_date = datetime.now() - timedelta(days=days)

        if hasattr(self.metadata_manager, 'list_all_content'):
            all_content = self.metadata_manager.list_all_content()
        else:
            all_content = self.metadata_manager.get_all_metadata()

        filtered = []
        for item in all_content:
            try:
                # Handle both dict and object formats
                if hasattr(item, 'created_at'):
                    created_at = item.created_at
                else:
                    created_at = item.get('created_at', item.get('date', ''))

                if created_at:
                    content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if content_date >= cutoff_date:
                        filtered.append(item)
            except Exception:
                pass

        return filtered

    def _analyze_daily_patterns(self, content_items: List[Dict[str, Any]]) -> List[TemporalPattern]:
        """Analyze daily consumption patterns."""
        hourly_activity = defaultdict(int)
        total_items = len(content_items)

        for item in content_items:
            try:
                if hasattr(item, 'created_at'):
                    created_at = item.created_at
                else:
                    created_at = item.get('created_at', item.get('date', ''))

                if created_at:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    hourly_activity[dt.hour] += 1
            except Exception:
                continue

        if not hourly_activity or total_items < 5:
            return []

        # Normalize and find peak hours
        peak_hours = []
        avg_activity = sum(hourly_activity.values()) / len(hourly_activity)

        for hour, count in hourly_activity.items():
            if count > avg_activity * 1.5:  # 50% above average
                peak_hours.append(hour)

        if not peak_hours:
            return []

        confidence = min(0.9, len(peak_hours) / 24 * total_items / 10)

        return [TemporalPattern(
            pattern_type="daily",
            pattern_data={
                "peak_hours": peak_hours,
                "hourly_activity": dict(hourly_activity),
                "total_items": total_items
            },
            confidence=confidence,
            frequency=len(peak_hours),
            last_occurrence=datetime.now().isoformat(),
            description=f"Peak activity during hours: {', '.join(map(str, sorted(peak_hours)))}"
        )]

    def _analyze_weekly_patterns(self, content_items: List[Dict[str, Any]]) -> List[TemporalPattern]:
        """Analyze weekly consumption patterns."""
        weekday_activity = defaultdict(int)
        total_items = len(content_items)

        for item in content_items:
            try:
                if hasattr(item, 'created_at'):
                    created_at = item.created_at
                else:
                    created_at = item.get('created_at', item.get('date', ''))

                if created_at:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    weekday_activity[dt.weekday()] += 1
            except Exception:
                continue

        if not weekday_activity or total_items < 10:
            return []

        # Find peak days
        avg_activity = sum(weekday_activity.values()) / len(weekday_activity)
        peak_days = [day for day, count in weekday_activity.items() if count > avg_activity * 1.3]

        if not peak_days:
            return []

        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        peak_day_names = [weekday_names[day] for day in sorted(peak_days)]

        confidence = min(0.8, len(peak_days) / 7 * total_items / 20)

        return [TemporalPattern(
            pattern_type="weekly",
            pattern_data={
                "peak_days": peak_days,
                "weekday_activity": dict(weekday_activity),
                "peak_day_names": peak_day_names
            },
            confidence=confidence,
            frequency=len(peak_days),
            last_occurrence=datetime.now().isoformat(),
            description=f"Higher activity on: {', '.join(peak_day_names)}"
        )]

    def _analyze_content_type_patterns(self, content_items: List[Dict[str, Any]]) -> List[TemporalPattern]:
        """Analyze content type timing patterns."""
        type_time_patterns = defaultdict(lambda: defaultdict(int))

        for item in content_items:
            try:
                if hasattr(item, 'content_type'):
                    content_type = getattr(item.content_type, 'value', item.content_type) if hasattr(item.content_type, 'value') else item.content_type
                else:
                    content_type = item.get('content_type', 'unknown')

                if hasattr(item, 'created_at'):
                    created_at = item.created_at
                else:
                    created_at = item.get('created_at', item.get('date', ''))

                if created_at:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    type_time_patterns[content_type][dt.hour] += 1
            except Exception:
                continue

        patterns = []
        for content_type, hourly_data in type_time_patterns.items():
            if sum(hourly_data.values()) < 3:  # Need at least 3 items
                continue

            # Find peak hour for this content type
            peak_hour = max(hourly_data.items(), key=lambda x: x[1])[0]
            total_for_type = sum(hourly_data.values())
            peak_concentration = hourly_data[peak_hour] / total_for_type

            if peak_concentration > 0.3:  # 30% of content consumed at peak hour
                patterns.append(TemporalPattern(
                    pattern_type="content_type_timing",
                    pattern_data={
                        "content_type": content_type,
                        "peak_hour": peak_hour,
                        "concentration": peak_concentration,
                        "hourly_activity": dict(hourly_data)
                    },
                    confidence=min(0.7, peak_concentration + total_for_type / 50),
                    frequency=total_for_type,
                    last_occurrence=datetime.now().isoformat(),
                    description=f"{content_type.title()} content typically consumed around {peak_hour}:00"
                ))

        return patterns

    def _analyze_reading_time_patterns(self, content_items: List[Dict[str, Any]]) -> List[TemporalPattern]:
        """Analyze patterns in reading time duration."""
        long_content_hours = defaultdict(int)
        short_content_hours = defaultdict(int)

        for item in content_items:
            try:
                if hasattr(item, 'word_count'):
                    word_count = item.word_count or 0
                else:
                    word_count = item.get('word_count', 0)

                if hasattr(item, 'created_at'):
                    created_at = item.created_at
                else:
                    created_at = item.get('created_at', item.get('date', ''))

                if created_at:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if word_count > 1500:  # Long content
                        long_content_hours[dt.hour] += 1
                    elif word_count > 0:  # Short content
                        short_content_hours[dt.hour] += 1
            except Exception:
                continue

        patterns = []

        # Long content pattern
        if long_content_hours:
            peak_hour = max(long_content_hours.items(), key=lambda x: x[1])[0]
            total_long = sum(long_content_hours.values())
            if total_long >= 3:
                patterns.append(TemporalPattern(
                    pattern_type="reading_duration",
                    pattern_data={
                        "duration_type": "long",
                        "peak_hour": peak_hour,
                        "total_items": total_long,
                        "hourly_activity": dict(long_content_hours)
                    },
                    confidence=min(0.6, total_long / 10),
                    frequency=total_long,
                    last_occurrence=datetime.now().isoformat(),
                    description=f"Long content typically consumed around {peak_hour}:00"
                ))

        return patterns

    def _pattern_to_insight(self, pattern: TemporalPattern) -> Optional[TemporalInsight]:
        """Convert a temporal pattern to an actionable insight."""
        if pattern.pattern_type == "daily":
            peak_hours = pattern.pattern_data.get("peak_hours", [])
            if peak_hours:
                return TemporalInsight(
                    insight_type="optimal_timing",
                    title="Peak Content Consumption Hours Identified",
                    description=f"You're most active during {', '.join(map(str, sorted(peak_hours)))}:00. Consider scheduling content consumption during these times.",
                    confidence=pattern.confidence,
                    supporting_data=pattern.pattern_data,
                    action_suggestions=[
                        "Schedule important reading during peak hours",
                        "Set up notifications for new content during active periods",
                        "Block distractions during peak consumption times"
                    ],
                    discovered_at=datetime.now().isoformat()
                )

        elif pattern.pattern_type == "content_type_timing":
            content_type = pattern.pattern_data.get("content_type")
            peak_hour = pattern.pattern_data.get("peak_hour")
            if content_type and peak_hour is not None:
                return TemporalInsight(
                    insight_type="content_timing",
                    title=f"Optimal {content_type.title()} Consumption Time",
                    description=f"You typically consume {content_type} content around {peak_hour}:00.",
                    confidence=pattern.confidence,
                    supporting_data=pattern.pattern_data,
                    action_suggestions=[
                        f"Queue {content_type} content for {peak_hour}:00",
                        f"Set up {content_type} notifications for this time",
                        f"Batch {content_type} processing around {peak_hour}:00"
                    ],
                    discovered_at=datetime.now().isoformat()
                )

        return None

    def _generate_schedule_insights(self, patterns: List[TemporalPattern]) -> List[TemporalInsight]:
        """Generate schedule-based insights."""
        insights = []

        # Find content type distribution
        content_patterns = [p for p in patterns if p.pattern_type == "content_type_timing"]

        if len(content_patterns) >= 2:
            insights.append(TemporalInsight(
                insight_type="schedule_optimization",
                title="Content Type Schedule Detected",
                description="Different content types have distinct optimal consumption times. Consider creating a content schedule.",
                confidence=0.7,
                supporting_data={"patterns": len(content_patterns)},
                action_suggestions=[
                    "Create a weekly content consumption schedule",
                    "Batch similar content types together",
                    "Use calendar reminders for optimal timing"
                ],
                discovered_at=datetime.now().isoformat()
            ))

        return insights

    def _detect_temporal_clusters(self, all_items, max_delta_days):
        """Detect clusters of content created/updated in temporal proximity."""
        try:
            # Sort by created_at
            all_items.sort(key=lambda m: getattr(m, 'created_at', ''))
            relationships = []

            for i in range(len(all_items) - 1):
                item1 = all_items[i]
                item2 = all_items[i + 1]
                try:
                    created_at1 = getattr(item1, 'created_at', '')
                    created_at2 = getattr(item2, 'created_at', '')

                    t1 = datetime.fromisoformat(created_at1.replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(created_at2.replace("Z", "+00:00"))
                    delta_days = (t2 - t1).days

                    if 0 < delta_days <= max_delta_days:
                        # Calculate relationship strength based on shared tags and content type
                        strength = self._calculate_relationship_strength(item1, item2, delta_days)

                        relationships.append({
                            "item1": item1,
                            "item2": item2,
                            "time_delta_days": delta_days,
                            "relationship_strength": strength,
                            "shared_tags": list(set(getattr(item1, 'tags', [])) & set(getattr(item2, 'tags', []))),
                            "relationship_type": self._classify_relationship(item1, item2),
                        })
                except (ValueError, AttributeError):
                    continue

            return relationships
        except Exception as e:
            print(f"Error detecting temporal clusters: {e}")
            return []

    def _calculate_relationship_strength(self, item1, item2, delta_days):
        """Calculate the strength of temporal relationship between two items."""
        strength = 1.0

        # Closer in time = stronger relationship (exponential decay)
        time_factor = 1.0 / (1.0 + delta_days * 0.5)
        strength *= time_factor

        # Shared tags increase strength
        tags1 = getattr(item1, 'tags', [])
        tags2 = getattr(item2, 'tags', [])
        shared_tags = set(tags1) & set(tags2)
        tag_factor = len(shared_tags) * 0.2
        strength += tag_factor

        # Same content type increases strength
        type1 = getattr(item1, 'content_type', None)
        type2 = getattr(item2, 'content_type', None)
        if type1 == type2:
            strength += 0.3

        return min(strength, 2.0)  # Cap at 2.0

    def _classify_relationship(self, item1, item2):
        """Classify the type of temporal relationship."""
        tags1 = getattr(item1, 'tags', [])
        tags2 = getattr(item2, 'tags', [])
        shared_tags = set(tags1) & set(tags2)

        if len(shared_tags) >= 2:
            return "thematic_continuation"
        elif getattr(item1, 'content_type', None) == getattr(item2, 'content_type', None):
            return "content_type_cluster"
        else:
            return "temporal_proximity"

    def _analyze_seasonal_patterns(self, temporal_patterns):
        """Analyze seasonal and cyclical patterns in content."""
        content_volume = temporal_patterns.get("content_volume", {})

        if len(content_volume) < 3:
            return {"insight": "Insufficient data for seasonal analysis"}

        # Simple seasonal analysis
        volumes = list(content_volume.values())
        avg_volume = sum(volumes) / len(volumes)
        peak_periods = [
            period
            for period, volume in content_volume.items()
            if volume > avg_volume * 1.5
        ]
        low_periods = [
            period
            for period, volume in content_volume.items()
            if volume < avg_volume * 0.5
        ]

        return {
            "average_volume": avg_volume,
            "peak_periods": peak_periods,
            "low_periods": low_periods,
            "volume_variance": max(volumes) - min(volumes) if volumes else 0,
        }

    def _calculate_content_velocity(self, temporal_patterns):
        """Calculate the velocity (rate of change) of content ingestion."""
        growth_analysis = temporal_patterns.get("growth_analysis", {})

        return {
            "growth_rate": growth_analysis.get("growth_rate_percent", 0),
            "trend": growth_analysis.get("trend", "unknown"),
            "recent_average": growth_analysis.get("recent_average", 0),
            "velocity_classification": self._classify_velocity(
                growth_analysis.get("growth_rate_percent", 0)
            ),
        }

    def _classify_velocity(self, growth_rate):
        """Classify content velocity based on growth rate."""
        if growth_rate > 50:
            return "accelerating"
        elif growth_rate > 10:
            return "growing"
        elif growth_rate > -10:
            return "stable"
        elif growth_rate > -50:
            return "declining"
        else:
            return "rapidly_declining"

    def _mock_analyze_patterns(self, context: TimeContext) -> List[TemporalPattern]:
        """Mock temporal pattern analysis."""
        return [
            TemporalPattern(
                pattern_type="daily",
                pattern_data={
                    "peak_hours": [9, 13, 20],
                    "hourly_activity": {9: 5, 13: 4, 20: 6},
                    "total_items": 45
                },
                confidence=0.75,
                frequency=3,
                last_occurrence=datetime.now().isoformat(),
                description="Peak activity during hours: 9, 13, 20"
            ),
            TemporalPattern(
                pattern_type="content_type_timing",
                pattern_data={
                    "content_type": "article",
                    "peak_hour": 9,
                    "concentration": 0.4,
                    "hourly_activity": {9: 8, 10: 3, 11: 2}
                },
                confidence=0.65,
                frequency=13,
                last_occurrence=datetime.now().isoformat(),
                description="Article content typically consumed around 9:00"
            )
        ]


if __name__ == "__main__":
    # Example usage
    engine = TemporalEngine()

    # Analyze patterns
    patterns = engine.analyze_patterns()
    print("Temporal Patterns Discovered:")
    print("=" * 40)

    for pattern in patterns:
        print(f"\nType: {pattern.pattern_type}")
        print(f"Confidence: {pattern.confidence:.2f}")
        print(f"Description: {pattern.description}")

    # Generate insights
    insights = engine.generate_insights(patterns)
    print("\n\nTemporal Insights:")
    print("=" * 40)

    for insight in insights:
        print(f"\nTitle: {insight.title}")
        print(f"Confidence: {insight.confidence:.2f}")
        print(f"Description: {insight.description}")
        print(f"Actions: {', '.join(insight.action_suggestions[:2])}")

    # Get optimal times
    optimal_times = engine.get_optimal_times()
    print("\n\nOptimal Consumption Times:")
    print("=" * 40)

    for hour, confidence in optimal_times[:5]:
        print(f"{hour:02d}:00 - Confidence: {confidence:.2f}")