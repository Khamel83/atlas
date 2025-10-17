#!/usr/bin/env python3
"""
Intelligence Dashboard - Advanced insights and knowledge graph visualization
Provides sophisticated analytics beyond basic content stats.
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntelligenceDashboard:
    """Advanced intelligence dashboard with knowledge graph and deep insights."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize intelligence dashboard."""
        self.config = config or {}
        self.main_db = self.config.get('main_db', 'data/atlas.db')
        self.search_db = self.config.get('search_db', 'data/enhanced_search.db')
        self.insights_db = self.config.get('insights_db', 'data/processed_content.db')

    def _get_connection(self, db_path: str) -> sqlite3.Connection:
        """Get database connection."""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def generate_knowledge_graph_data(self, max_nodes: int = 100) -> Dict[str, Any]:
        """Generate knowledge graph visualization data."""
        try:
            # Get content with insights
            conn = self._get_connection(self.main_db)
            cursor = conn.cursor()

            # Get content with metadata
            cursor.execute("""
                SELECT id, title, content_type, url, created_at, metadata
                FROM content
                WHERE title IS NOT NULL AND title != ''
                ORDER BY created_at DESC
                LIMIT ?
            """, (max_nodes,))

            content_items = cursor.fetchall()

            # Build nodes and edges
            nodes = []
            edges = []
            topics = defaultdict(list)

            for item in content_items:
                # Create content node
                node = {
                    'id': f"content_{item['id']}",
                    'label': item['title'][:50] + ('...' if len(item['title']) > 50 else ''),
                    'type': 'content',
                    'content_type': item['content_type'],
                    'url': item['url'],
                    'size': min(20, max(8, len(item['title']) // 5)),
                    'created_at': item['created_at']
                }
                nodes.append(node)

                # Extract topics from metadata
                if item['metadata']:
                    try:
                        metadata = json.loads(item['metadata']) if isinstance(item['metadata'], str) else item['metadata']
                        content_topics = []

                        # Look for topics in various metadata fields
                        if 'tags' in metadata and isinstance(metadata['tags'], list):
                            content_topics.extend(metadata['tags'][:3])  # Limit to top 3
                        if 'categories' in metadata and isinstance(metadata['categories'], list):
                            content_topics.extend(metadata['categories'][:2])
                        if 'domain' in metadata:
                            content_topics.append(metadata['domain'])

                        for topic in content_topics[:5]:  # Limit topics per content
                            if isinstance(topic, str) and len(topic) > 2:
                                topic_clean = topic.strip().lower()
                                topics[topic_clean].append(item['id'])

                    except (json.JSONDecodeError, TypeError):
                        continue

            # Create topic nodes and edges
            for topic, content_ids in topics.items():
                if len(content_ids) >= 2:  # Only topics with multiple content items
                    topic_node = {
                        'id': f"topic_{topic.replace(' ', '_')}",
                        'label': topic.title(),
                        'type': 'topic',
                        'size': min(30, max(12, len(content_ids) * 3)),
                        'content_count': len(content_ids)
                    }
                    nodes.append(topic_node)

                    # Create edges from topic to content
                    for content_id in content_ids:
                        edges.append({
                            'from': topic_node['id'],
                            'to': f"content_{content_id}",
                            'type': 'relates_to'
                        })

            conn.close()

            return {
                'nodes': nodes,
                'edges': edges,
                'stats': {
                    'total_nodes': len(nodes),
                    'content_nodes': len([n for n in nodes if n['type'] == 'content']),
                    'topic_nodes': len([n for n in nodes if n['type'] == 'topic']),
                    'total_edges': len(edges)
                }
            }

        except Exception as e:
            logger.error(f"Error generating knowledge graph: {e}")
            return {'nodes': [], 'edges': [], 'stats': {}}

    def analyze_consumption_patterns(self, days: int = 30) -> Dict[str, Any]:
        """Analyze content consumption patterns."""
        try:
            conn = self._get_connection(self.main_db)
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')

            # Daily consumption patterns
            cursor.execute("""
                SELECT DATE(created_at) as day,
                       COUNT(*) as count,
                       content_type,
                       AVG(CASE WHEN json_extract(metadata, '$.word_count')
                               THEN CAST(json_extract(metadata, '$.word_count') AS INTEGER)
                               ELSE 1000 END) as avg_words
                FROM content
                WHERE created_at >= ?
                GROUP BY DATE(created_at), content_type
                ORDER BY day DESC
            """, (cutoff_str,))

            daily_data = cursor.fetchall()

            # Content type distribution
            cursor.execute("""
                SELECT content_type, COUNT(*) as count,
                       SUM(CASE WHEN json_extract(metadata, '$.word_count')
                               THEN CAST(json_extract(metadata, '$.word_count') AS INTEGER)
                               ELSE 1000 END) as total_words
                FROM content
                WHERE created_at >= ?
                GROUP BY content_type
                ORDER BY count DESC
            """, (cutoff_str,))

            type_distribution = cursor.fetchall()

            # Time patterns (hour of day)
            cursor.execute("""
                SELECT strftime('%H', created_at) as hour, COUNT(*) as count
                FROM content
                WHERE created_at >= ?
                GROUP BY strftime('%H', created_at)
                ORDER BY hour
            """, (cutoff_str,))

            hourly_patterns = cursor.fetchall()

            # Most productive domains
            cursor.execute("""
                SELECT CASE
                    WHEN json_extract(metadata, '$.domain') IS NOT NULL
                    THEN json_extract(metadata, '$.domain')
                    ELSE 'unknown'
                END as domain,
                COUNT(*) as count
                FROM content
                WHERE created_at >= ?
                GROUP BY domain
                HAVING count > 1
                ORDER BY count DESC
                LIMIT 10
            """, (cutoff_str,))

            top_domains = cursor.fetchall()

            conn.close()

            return {
                'period_days': days,
                'daily_consumption': [dict(row) for row in daily_data],
                'content_type_distribution': [dict(row) for row in type_distribution],
                'hourly_patterns': [dict(row) for row in hourly_patterns],
                'top_domains': [dict(row) for row in top_domains],
                'insights': self._generate_consumption_insights(daily_data, hourly_patterns, type_distribution)
            }

        except Exception as e:
            logger.error(f"Error analyzing consumption patterns: {e}")
            return {}

    def _generate_consumption_insights(self, daily_data, hourly_patterns, type_distribution) -> List[str]:
        """Generate insights from consumption patterns."""
        insights = []

        try:
            # Daily pattern insights
            if daily_data:
                daily_counts = [row['count'] for row in daily_data]
                avg_daily = sum(daily_counts) / len(daily_counts)
                if avg_daily > 10:
                    insights.append(f"High content consumption: averaging {avg_daily:.1f} items per day")

                # Most productive day
                if daily_data:
                    max_day = max(daily_data, key=lambda x: x['count'])
                    insights.append(f"Most productive day: {max_day['day']} with {max_day['count']} items")

            # Hourly pattern insights
            if hourly_patterns:
                hourly_counts = {int(row['hour']): row['count'] for row in hourly_patterns}
                peak_hours = sorted(hourly_counts.keys(), key=lambda h: hourly_counts[h], reverse=True)[:3]
                insights.append(f"Peak reading hours: {', '.join([f'{h:02d}:00' for h in peak_hours])}")

            # Content type insights
            if type_distribution:
                total_content = sum(row['count'] for row in type_distribution)
                if total_content > 0:
                    top_type = type_distribution[0]
                    percentage = (top_type['count'] / total_content) * 100
                    insights.append(f"Primary content type: {top_type['content_type']} ({percentage:.1f}%)")

                    # Diversity insight
                    if len(type_distribution) > 3:
                        insights.append(f"Diverse consumption: {len(type_distribution)} different content types")

            return insights

        except Exception as e:
            logger.error(f"Error generating consumption insights: {e}")
            return ["Analysis in progress..."]

    def generate_learning_recommendations(self, user_profile: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Generate intelligent learning recommendations."""
        try:
            conn = self._get_connection(self.main_db)
            cursor = conn.cursor()

            recommendations = []

            # Get content frequency by type and domain
            cursor.execute("""
                SELECT content_type,
                       json_extract(metadata, '$.domain') as domain,
                       COUNT(*) as frequency,
                       AVG(CASE WHEN json_extract(metadata, '$.word_count')
                               THEN CAST(json_extract(metadata, '$.word_count') AS INTEGER)
                               ELSE 1000 END) as avg_length
                FROM content
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY content_type, domain
                HAVING frequency > 2
                ORDER BY frequency DESC
                LIMIT 20
            """)

            content_patterns = cursor.fetchall()

            # Knowledge gap analysis
            cursor.execute("""
                SELECT DISTINCT json_extract(metadata, '$.domain') as domain
                FROM content
                WHERE json_extract(metadata, '$.domain') IS NOT NULL
                  AND created_at >= datetime('now', '-7 days')
            """)
            recent_domains = [row['domain'] for row in cursor.fetchall() if row['domain']]

            cursor.execute("""
                SELECT DISTINCT json_extract(metadata, '$.domain') as domain,
                       COUNT(*) as historical_count
                FROM content
                WHERE json_extract(metadata, '$.domain') IS NOT NULL
                  AND created_at < datetime('now', '-7 days')
                GROUP BY domain
                HAVING historical_count > 5
                ORDER BY historical_count DESC
            """)
            historical_domains = cursor.fetchall()

            # Find domains you used to read but haven't recently
            dormant_domains = []
            for row in historical_domains:
                if row['domain'] not in recent_domains:
                    dormant_domains.append(row)

            # Generate recommendations
            for pattern in content_patterns[:5]:
                if pattern['frequency'] > 5:
                    recommendations.append({
                        'type': 'continue_pattern',
                        'title': f"Continue exploring {pattern['domain'] or pattern['content_type']}",
                        'reason': f"You've engaged with {pattern['frequency']} items in this area",
                        'priority': min(10, pattern['frequency'] // 2),
                        'category': 'pattern_continuation'
                    })

            for domain_info in dormant_domains[:3]:
                recommendations.append({
                    'type': 'revisit_topic',
                    'title': f"Revisit {domain_info['domain']} content",
                    'reason': f"You used to read {domain_info['historical_count']} items from this domain",
                    'priority': min(8, domain_info['historical_count'] // 3),
                    'category': 'knowledge_revival'
                })

            # Diversification recommendations
            if len(content_patterns) < 5:
                recommendations.append({
                    'type': 'diversify',
                    'title': "Explore new content types",
                    'reason': "Adding variety could enhance your learning experience",
                    'priority': 6,
                    'category': 'diversification'
                })

            conn.close()

            # Sort by priority and return top recommendations
            recommendations.sort(key=lambda x: x['priority'], reverse=True)
            return recommendations[:8]

        except Exception as e:
            logger.error(f"Error generating learning recommendations: {e}")
            return []

    def get_content_quality_analysis(self) -> Dict[str, Any]:
        """Analyze content quality metrics."""
        try:
            # Try to get structured insights if available
            if os.path.exists(self.insights_db):
                insights_conn = self._get_connection(self.insights_db)
                cursor = insights_conn.cursor()

                cursor.execute("""
                    SELECT AVG(quality_score) as avg_quality,
                           COUNT(*) as analyzed_count,
                           AVG(readability_score) as avg_readability,
                           COUNT(DISTINCT category) as category_diversity
                    FROM content_insights
                    WHERE quality_score IS NOT NULL
                """)

                quality_stats = cursor.fetchone()

                # Get quality distribution
                cursor.execute("""
                    SELECT
                        CASE
                            WHEN quality_score >= 0.8 THEN 'Excellent'
                            WHEN quality_score >= 0.6 THEN 'Good'
                            WHEN quality_score >= 0.4 THEN 'Average'
                            ELSE 'Below Average'
                        END as quality_tier,
                        COUNT(*) as count
                    FROM content_insights
                    WHERE quality_score IS NOT NULL
                    GROUP BY quality_tier
                    ORDER BY quality_score DESC
                """)

                quality_distribution = cursor.fetchall()
                insights_conn.close()

                return {
                    'average_quality': round(quality_stats['avg_quality'] or 0, 2),
                    'analyzed_content_count': quality_stats['analyzed_count'] or 0,
                    'average_readability': round(quality_stats['avg_readability'] or 0, 2),
                    'category_diversity': quality_stats['category_diversity'] or 0,
                    'quality_distribution': [dict(row) for row in quality_distribution],
                    'has_quality_analysis': True
                }
            else:
                # Fallback to basic content analysis
                conn = self._get_connection(self.main_db)
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) as total FROM content")
                total_content = cursor.fetchone()['total']

                cursor.execute("SELECT COUNT(DISTINCT content_type) as types FROM content")
                content_types = cursor.fetchone()['types']

                conn.close()

                return {
                    'total_content': total_content,
                    'content_types': content_types,
                    'has_quality_analysis': False,
                    'message': 'Quality analysis available after content processing'
                }

        except Exception as e:
            logger.error(f"Error analyzing content quality: {e}")
            return {'has_quality_analysis': False, 'error': str(e)}

    def generate_comprehensive_intelligence_report(self) -> Dict[str, Any]:
        """Generate comprehensive intelligence dashboard data."""
        try:
            logger.info("Generating comprehensive intelligence report...")

            report = {
                'generated_at': datetime.now().isoformat(),
                'knowledge_graph': self.generate_knowledge_graph_data(max_nodes=50),
                'consumption_patterns': self.analyze_consumption_patterns(days=30),
                'learning_recommendations': self.generate_learning_recommendations(),
                'content_quality': self.get_content_quality_analysis(),
                'system_status': {
                    'databases_available': {
                        'main_db': os.path.exists(self.main_db),
                        'search_db': os.path.exists(self.search_db),
                        'insights_db': os.path.exists(self.insights_db)
                    },
                    'intelligence_level': 'advanced' if os.path.exists(self.insights_db) else 'basic'
                }
            }

            logger.info(f"Intelligence report generated with {len(report['knowledge_graph']['nodes'])} graph nodes")
            return report

        except Exception as e:
            logger.error(f"Error generating intelligence report: {e}")
            return {
                'generated_at': datetime.now().isoformat(),
                'error': str(e),
                'system_status': {'intelligence_level': 'error'}
            }