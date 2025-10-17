#!/usr/bin/env python3
"""
Analytics Engine - Core analytics and insights generation
Processes content metadata to generate consumption insights and analytics.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from collections import Counter, defaultdict

from helpers.utils import log_info, log_error
from helpers.metadata_manager import MetadataManager
from helpers.search_engine import AtlasSearchEngine as SearchEngine


class AnalyticsEngine:
    """
    Core analytics engine for personal content consumption insights.

    Analyzes content metadata to provide:
    - Consumption patterns and trends
    - Content type distribution
    - Reading/listening habits
    - Knowledge graph analysis
    - Progress tracking
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize AnalyticsEngine with configuration."""
        self.config = config or {}

        # Set up logging
        import os
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'analytics_engine.log')

        self.db_path = Path(self.config.get('analytics_db', 'data/analytics.db'))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize Atlas integration
        self.metadata_manager = MetadataManager(config)
        self.search_engine = SearchEngine(config)

        self._init_database()

        # Auto-sync with Atlas data on initialization
        self._sync_with_atlas_data()

    def _init_database(self):
        """Initialize analytics database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS content_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_type TEXT,
                        title TEXT,
                        url TEXT,
                        date_added TEXT,
                        word_count INTEGER,
                        tags TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS consumption_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_id INTEGER,
                        event_type TEXT,
                        timestamp TEXT,
                        duration INTEGER,
                        metadata TEXT,
                        FOREIGN KEY (content_id) REFERENCES content_analytics (id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS analytics_cache (
                        cache_key TEXT PRIMARY KEY,
                        data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                ''')

            log_info(self.log_path, "Analytics database initialized")

        except Exception as e:
            log_error(self.log_path, f"Error initializing analytics database: {str(e)}")

    def _sync_with_atlas_data(self):
        """Enhanced sync with Atlas data - production grade with performance optimization."""
        try:
            # Get all Atlas content with error handling
            try:
                atlas_content = self.metadata_manager.get_all_metadata()
                if not atlas_content:
                    log_info(self.log_path, "No Atlas content found for sync")
                    return
            except Exception as e:
                log_error(self.log_path, f"Failed to get Atlas metadata: {str(e)}")
                # Continue with empty list for graceful degradation
                atlas_content = []

            log_info(self.log_path, f"Syncing analytics with {len(atlas_content)} Atlas items")
            sync_start_time = datetime.now()

            # Performance optimization: batch processing
            batch_size = 100
            synced_count = 0
            error_count = 0

            with sqlite3.connect(self.db_path) as conn:
                # Optimize SQLite for bulk operations
                conn.execute('PRAGMA synchronous = OFF')
                conn.execute('PRAGMA journal_mode = WAL')
                conn.execute('PRAGMA cache_size = 10000')

                # Get existing URLs in one query for deduplication
                existing_urls = set()
                try:
                    existing_results = conn.execute('SELECT url FROM content_analytics').fetchall()
                    existing_urls = {row[0] for row in existing_results}
                except Exception as e:
                    log_error(self.log_path, f"Error getting existing URLs: {str(e)}")

                # Process in batches
                for i in range(0, len(atlas_content), batch_size):
                    batch = atlas_content[i:i + batch_size]

                    try:
                        conn.execute('BEGIN TRANSACTION')

                        for item in batch:
                            try:
                                # Handle both dict-like objects and ContentMetadata objects
                                if hasattr(item, 'get'):
                                    # Dict-like object
                                    url = item.get('url', '')
                                else:
                                    # ContentMetadata object
                                    url = getattr(item, 'source', '')

                                # Skip if already exists (fast lookup)
                                if url in existing_urls:
                                    continue

                                # Enhanced data extraction with fallbacks
                                # Handle both dict-like objects and ContentMetadata objects
                                if hasattr(item, 'get'):
                                    # Dict-like object
                                    content_type = self._normalize_content_type(item.get('content_type', 'unknown'))
                                    title = item.get('title', 'Untitled')[:500]  # Prevent oversized titles
                                    word_count = self._safe_int(item.get('word_count', 0))
                                    tags = item.get('tags', [])
                                    created_at = item.get('created_at', datetime.now().isoformat())

                                    # Enhanced metadata with Atlas-specific fields
                                    item_dict = item if isinstance(item, dict) else item.to_dict() if hasattr(item, 'to_dict') else dict(item)
                                    enhanced_metadata = {
                                        **item_dict,
                                        'sync_timestamp': datetime.now().isoformat(),
                                        'source': 'atlas_sync',
                                        'quality_score': item.get('evaluation', {}).get('overall_score', 0) if 'evaluation' in item else 0,
                                        'processing_status': item.get('status', 'unknown')
                                    }
                                else:
                                    # ContentMetadata object
                                    content_type = self._normalize_content_type(getattr(item, 'content_type', 'unknown').value if hasattr(getattr(item, 'content_type', 'unknown'), 'value') else getattr(item, 'content_type', 'unknown'))
                                    title = getattr(item, 'title', 'Untitled')[:500]  # Prevent oversized titles
                                    # Extract word count from metadata if available
                                    word_count = 0
                                    if hasattr(item, 'type_specific') and item.type_specific:
                                        word_count = self._safe_int(item.type_specific.get('word_count', 0))
                                    tags = getattr(item, 'tags', [])
                                    created_at = getattr(item, 'created_at', datetime.now().isoformat())

                                    # Enhanced metadata with Atlas-specific fields
                                    enhanced_metadata = {
                                        'sync_timestamp': datetime.now().isoformat(),
                                        'source': 'atlas_sync',
                                        'quality_score': 0,  # No evaluation data in ContentMetadata
                                        'processing_status': getattr(item, 'status', 'unknown').value if hasattr(getattr(item, 'status', 'unknown'), 'value') else getattr(item, 'status', 'unknown'),
                                        # Add other ContentMetadata fields
                                        'uid': getattr(item, 'uid', ''),
                                        'content_type': getattr(item, 'content_type', 'unknown').value if hasattr(getattr(item, 'content_type', 'unknown'), 'value') else getattr(item, 'content_type', 'unknown'),
                                        'source_url': getattr(item, 'source', ''),
                                        'title': getattr(item, 'title', ''),
                                        'tags': getattr(item, 'tags', []),
                                        'notes': getattr(item, 'notes', []),
                                        'fetch_method': getattr(item, 'fetch_method', ''),
                                        'type_specific': getattr(item, 'type_specific', {}),
                                    }

                                # Insert content analytics
                                cursor = conn.execute('''
                                    INSERT OR IGNORE INTO content_analytics
                                    (content_type, title, url, date_added, word_count, tags, metadata)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    content_type,
                                    title,
                                    url,
                                    created_at,
                                    word_count,
                                    json.dumps(tags) if tags else '[]',
                                    json.dumps(enhanced_metadata)
                                ))

                                # Only create event if content was actually inserted
                                if cursor.rowcount > 0:
                                    # Record ingestion event with metadata
                                    conn.execute('''
                                        INSERT INTO consumption_events
                                        (content_id, event_type, timestamp, duration, metadata)
                                        SELECT id, 'ingested', ?, 0, ?
                                        FROM content_analytics WHERE url = ? LIMIT 1
                                    ''', (created_at, json.dumps({
                                        'sync_batch': i // batch_size + 1,
                                        'content_length': len(getattr(item, 'content_path', '') or ''),
                                        'has_evaluation': hasattr(item, 'evaluation')
                                    }), url))

                                    existing_urls.add(url)  # Update our cache
                                    synced_count += 1

                            except Exception as e:
                                error_count += 1
                                # Handle both dict-like objects and ContentMetadata objects
                                if hasattr(item, 'get'):
                                    title = item.get('title', 'unknown')
                                else:
                                    title = getattr(item, 'title', 'unknown')
                                log_error(self.log_path, f"Error syncing item {title}: {str(e)}")
                                continue

                        conn.execute('COMMIT')

                    except Exception as e:
                        conn.execute('ROLLBACK')
                        log_error(self.log_path, f"Error syncing batch {i//batch_size + 1}: {str(e)}")
                        error_count += len(batch)

                # Restore SQLite settings
                conn.execute('PRAGMA synchronous = NORMAL')

            sync_duration = (datetime.now() - sync_start_time).total_seconds()
            log_info(self.log_path, f"Atlas sync complete: {synced_count} items synced, {error_count} errors, {sync_duration:.2f}s")

            # Update sync statistics
            self._update_sync_stats(synced_count, error_count, sync_duration)

        except Exception as e:
            log_error(self.log_path, f"Critical error in Atlas sync: {str(e)}")

    def _normalize_content_type(self, content_type: str) -> str:
        """Normalize content type to standard values."""
        if not content_type:
            return 'unknown'

        content_type = content_type.lower().strip()

        # Map common variations to standard types
        type_mapping = {
            'youtube': 'video',
            'youtube_video': 'video',
            'podcast_episode': 'podcast',
            'rss_entry': 'podcast',
            'blog_post': 'article',
            'web_article': 'article',
            'html_article': 'article'
        }

        return type_mapping.get(content_type, content_type)

    def _safe_int(self, value: Any) -> int:
        """Safely convert value to integer."""
        try:
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str) and value.isdigit():
                return int(value)
            return 0
        except (ValueError, TypeError):
            return 0

    def _update_sync_stats(self, synced_count: int, error_count: int, duration: float):
        """Update synchronization statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store sync statistics
                conn.execute('''
                    INSERT OR REPLACE INTO analytics_cache
                    (cache_key, data, created_at, expires_at)
                    VALUES (?, ?, datetime('now'), datetime('now', '+1 day'))
                ''', (
                    'last_sync_stats',
                    json.dumps({
                        'synced_count': synced_count,
                        'error_count': error_count,
                        'duration_seconds': duration,
                        'sync_timestamp': datetime.now().isoformat(),
                        'success_rate': (synced_count / (synced_count + error_count)) * 100 if (synced_count + error_count) > 0 else 100
                    })
                ))
        except Exception as e:
            log_error(self.log_path, f"Error updating sync stats: {str(e)}")

    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health metrics."""
        try:
            health = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'database': {},
                'sync': {},
                'performance': {},
                'recommendations': []
            }

            with sqlite3.connect(self.db_path) as conn:
                # Database health
                try:
                    # Get database size
                    db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

                    # Get record counts
                    content_count = conn.execute('SELECT COUNT(*) FROM content_analytics').fetchone()[0]
                    events_count = conn.execute('SELECT COUNT(*) FROM consumption_events').fetchone()[0]

                    health['database'] = {
                        'size_mb': round(db_size / (1024 * 1024), 2),
                        'content_records': content_count,
                        'event_records': events_count,
                        'status': 'healthy'
                    }

                    # Performance checks
                    if content_count > 10000:
                        health['recommendations'].append("Consider database optimization for large dataset")

                except Exception as e:
                    health['database'] = {'status': 'error', 'error': str(e)}
                    health['status'] = 'warning'

                # Sync health
                try:
                    sync_stats = conn.execute('''
                        SELECT data FROM analytics_cache
                        WHERE cache_key = 'last_sync_stats'
                        AND expires_at > datetime('now')
                    ''').fetchone()

                    if sync_stats:
                        sync_data = json.loads(sync_stats[0])
                        health['sync'] = sync_data

                        if sync_data.get('success_rate', 100) < 95:
                            health['status'] = 'warning'
                            health['recommendations'].append("Sync success rate is below 95%")
                    else:
                        health['sync'] = {'status': 'no_recent_sync'}

                except Exception as e:
                    health['sync'] = {'status': 'error', 'error': str(e)}

            return health

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def add_content(self,
                   content_type: str,
                   title: str,
                   url: str = None,
                   metadata: Dict[str, Any] = None) -> int:
        """Add content for analytics tracking."""
        try:
            metadata = metadata or {}

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO content_analytics
                    (content_type, title, url, date_added, word_count, tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    content_type,
                    title,
                    url or "",
                    datetime.now().isoformat(),
                    metadata.get('word_count', 0),
                    json.dumps(metadata.get('tags', [])),
                    json.dumps(metadata)
                ))

                content_id = cursor.lastrowid
                log_info(self.log_path, f"Added content for analytics: {title} (ID: {content_id})")
                return content_id

        except Exception as e:
            log_error(self.log_path, f"Error adding content to analytics: {str(e)}")
            return -1

    def record_event(self,
                    content_id: int,
                    event_type: str,
                    duration: int = None,
                    metadata: Dict[str, Any] = None):
        """Record consumption event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO consumption_events
                    (content_id, event_type, timestamp, duration, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    content_id,
                    event_type,
                    datetime.now().isoformat(),
                    duration or 0,
                    json.dumps(metadata or {})
                ))

            log_info(self.log_path, f"Recorded event: {event_type} for content {content_id}")

        except Exception as e:
            log_error(self.log_path, f"Error recording event: {str(e)}")

    def generate_insights(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive analytics insights."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            insights = {
                "period_days": days,
                "generated_at": datetime.now().isoformat(),
                "overview": self._generate_overview(cutoff_date),
                "content_distribution": self._analyze_content_distribution(cutoff_date),
                "consumption_patterns": self._analyze_consumption_patterns(cutoff_date),
                "trends": self._analyze_trends(cutoff_date),
                "top_content": self._get_top_content(cutoff_date),
                "recommendations": self._generate_recommendations(cutoff_date)
            }

            log_info(self.log_path, f"Generated insights for {days} days")
            return insights

        except Exception as e:
            log_error(self.log_path, f"Error generating insights: {str(e)}")
            return {"error": str(e)}

    def _generate_overview(self, cutoff_date: str) -> Dict[str, Any]:
        """Generate overview statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Total content
            total_content = conn.execute(
                'SELECT COUNT(*) FROM content_analytics WHERE date_added >= ?',
                (cutoff_date,)
            ).fetchone()[0]

            # Content by type
            content_types = conn.execute('''
                SELECT content_type, COUNT(*)
                FROM content_analytics
                WHERE date_added >= ?
                GROUP BY content_type
            ''', (cutoff_date,)).fetchall()

            # Total words
            total_words = conn.execute(
                'SELECT SUM(word_count) FROM content_analytics WHERE date_added >= ?',
                (cutoff_date,)
            ).fetchone()[0] or 0

            # Events
            total_events = conn.execute(
                'SELECT COUNT(*) FROM consumption_events WHERE timestamp >= ?',
                (cutoff_date,)
            ).fetchone()[0]

            return {
                "total_content": total_content,
                "content_by_type": dict(content_types),
                "total_words": total_words,
                "total_events": total_events,
                "estimated_reading_hours": round(total_words / 12000, 1)  # ~200 wpm
            }

    def _analyze_content_distribution(self, cutoff_date: str) -> Dict[str, Any]:
        """Analyze content type distribution."""
        with sqlite3.connect(self.db_path) as conn:
            # Content types with percentages
            content_data = conn.execute('''
                SELECT content_type, COUNT(*) as count, SUM(word_count) as words
                FROM content_analytics
                WHERE date_added >= ?
                GROUP BY content_type
                ORDER BY count DESC
            ''', (cutoff_date,)).fetchall()

            total_content = sum(row[1] for row in content_data)
            total_words = sum(row[2] or 0 for row in content_data)

            distribution = []
            for content_type, count, words in content_data:
                distribution.append({
                    "type": content_type,
                    "count": count,
                    "percentage": round((count / total_content) * 100, 1) if total_content > 0 else 0,
                    "words": words or 0,
                    "word_percentage": round(((words or 0) / total_words) * 100, 1) if total_words > 0 else 0
                })

            return {
                "distribution": distribution,
                "total_types": len(distribution)
            }

    def _analyze_consumption_patterns(self, cutoff_date: str) -> Dict[str, Any]:
        """Analyze consumption patterns."""
        with sqlite3.connect(self.db_path) as conn:
            # Events by type
            event_data = conn.execute('''
                SELECT event_type, COUNT(*)
                FROM consumption_events
                WHERE timestamp >= ?
                GROUP BY event_type
                ORDER BY COUNT(*) DESC
            ''', (cutoff_date,)).fetchall()

            # Daily consumption
            daily_data = conn.execute('''
                SELECT DATE(timestamp) as date, COUNT(*) as events
                FROM consumption_events
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (cutoff_date,)).fetchall()

            # Average per day
            avg_events_per_day = sum(row[1] for row in daily_data) / len(daily_data) if daily_data else 0

            return {
                "events_by_type": dict(event_data),
                "daily_activity": [{"date": date, "events": events} for date, events in daily_data],
                "average_events_per_day": round(avg_events_per_day, 1),
                "active_days": len(daily_data)
            }

    def _analyze_trends(self, cutoff_date: str) -> Dict[str, Any]:
        """Analyze trends over time."""
        with sqlite3.connect(self.db_path) as conn:
            # Weekly trends
            weekly_data = conn.execute('''
                SELECT
                    strftime('%Y-%W', date_added) as week,
                    content_type,
                    COUNT(*) as count
                FROM content_analytics
                WHERE date_added >= ?
                GROUP BY week, content_type
                ORDER BY week
            ''', (cutoff_date,)).fetchall()

            # Process into trend data
            trends_by_type = defaultdict(list)
            for week, content_type, count in weekly_data:
                trends_by_type[content_type].append({
                    "week": week,
                    "count": count
                })

            return {
                "weekly_trends": dict(trends_by_type),
                "trending_up": self._identify_trending_types(trends_by_type, direction="up"),
                "trending_down": self._identify_trending_types(trends_by_type, direction="down")
            }

    def _identify_trending_types(self, trends_data: Dict, direction: str) -> List[str]:
        """Identify trending content types."""
        trending = []

        for content_type, data in trends_data.items():
            if len(data) >= 2:
                recent_avg = sum(point["count"] for point in data[-2:]) / 2
                older_avg = sum(point["count"] for point in data[:-2]) / max(len(data) - 2, 1)

                if direction == "up" and recent_avg > older_avg * 1.2:
                    trending.append(content_type)
                elif direction == "down" and recent_avg < older_avg * 0.8:
                    trending.append(content_type)

        return trending

    def _get_top_content(self, cutoff_date: str) -> Dict[str, Any]:
        """Get top content by various metrics."""
        with sqlite3.connect(self.db_path) as conn:
            # Most viewed
            most_viewed = conn.execute('''
                SELECT ca.title, ca.content_type, COUNT(ce.id) as events
                FROM content_analytics ca
                LEFT JOIN consumption_events ce ON ca.id = ce.content_id
                WHERE ca.date_added >= ?
                GROUP BY ca.id
                ORDER BY events DESC
                LIMIT 10
            ''', (cutoff_date,)).fetchall()

            # Longest content
            longest_content = conn.execute('''
                SELECT title, content_type, word_count
                FROM content_analytics
                WHERE date_added >= ? AND word_count > 0
                ORDER BY word_count DESC
                LIMIT 10
            ''', (cutoff_date,)).fetchall()

            return {
                "most_engaged": [
                    {"title": title, "type": ctype, "events": events}
                    for title, ctype, events in most_viewed
                ],
                "longest_content": [
                    {"title": title, "type": ctype, "words": words}
                    for title, ctype, words in longest_content
                ]
            }

    def _generate_recommendations(self, cutoff_date: str) -> List[str]:
        """Generate personalized recommendations."""
        recommendations = []

        try:
            insights = self._get_cached_insights()

            if not insights:
                return ["Generate more content to see personalized recommendations."]

            overview = insights.get("overview", {})
            patterns = insights.get("consumption_patterns", {})

            # Reading volume recommendations
            total_words = overview.get("total_words", 0)
            if total_words < 50000:  # Less than ~4 hours of reading
                recommendations.append("Consider increasing your reading volume for deeper insights.")

            # Content diversity
            content_types = len(overview.get("content_by_type", {}))
            if content_types < 3:
                recommendations.append("Try diversifying content types for broader learning.")

            # Engagement patterns
            events = patterns.get("events_by_type", {})
            if "viewed" in events and events["viewed"] > events.get("completed", 0) * 3:
                recommendations.append("Focus on completing more content rather than just viewing.")

            # Activity consistency
            active_days = patterns.get("active_days", 0)
            if active_days < 7:
                recommendations.append("Try to engage with content more consistently throughout the week.")

            return recommendations or ["Keep up the great work with your learning habits!"]

        except Exception as e:
            log_error(self.log_path, f"Error generating recommendations: {str(e)}")
            return ["Unable to generate recommendations at this time."]

    def _get_cached_insights(self) -> Optional[Dict[str, Any]]:
        """Get cached insights if available."""
        try:
            cache_key = f"insights_30_days"
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute('''
                    SELECT data, expires_at FROM analytics_cache
                    WHERE cache_key = ? AND expires_at > datetime('now')
                ''', (cache_key,)).fetchone()

                if result:
                    return json.loads(result[0])

            return None

        except Exception as e:
            log_error(self.log_path, f"Error getting cached insights: {str(e)}")
            return None

    def export_analytics_data(self, format: str = "json") -> Union[str, Dict]:
        """Export analytics data in specified format."""
        try:
            insights = self.generate_insights(days=90)  # 3 months

            if format.lower() == "json":
                return json.dumps(insights, indent=2)
            elif format.lower() == "csv":
                return self._export_as_csv(insights)
            else:
                return insights

        except Exception as e:
            log_error(self.log_path, f"Error exporting analytics: {str(e)}")
            return {"error": str(e)}

    def _export_as_csv(self, insights: Dict[str, Any]) -> str:
        """Export insights as CSV format."""
        lines = ["Metric,Value,Type"]

        overview = insights.get("overview", {})
        for key, value in overview.items():
            lines.append(f"{key},{value},overview")

        distribution = insights.get("content_distribution", {}).get("distribution", [])
        for item in distribution:
            lines.append(f"{item['type']}_count,{item['count']},content_distribution")
            lines.append(f"{item['type']}_percentage,{item['percentage']}%,content_distribution")

        return "\n".join(lines)

    def get_consumption_patterns(self, days: int = 30) -> Dict[str, Any]:
        """
        Public method to get consumption patterns.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with consumption patterns analysis
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        return self._analyze_consumption_patterns(cutoff_date)


def get_analytics(days: int = 30, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Core analytics function for Block 8 validation.

    Args:
        days: Number of days to analyze
        config: Configuration dictionary

    Returns:
        Dict with analytics insights
    """
    try:
        engine = AnalyticsEngine(config)
        return engine.generate_insights(days)
    except Exception as e:
        return {"error": str(e), "days": days}