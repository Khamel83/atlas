#!/usr/bin/env python3
"""
Trend Detection for Atlas

This module implements trending topic detection and content velocity analysis
to identify emerging topics and viral content.
"""

import re
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json


class TrendDetector:
    """Content trend detection system"""

    def __init__(self):
        """Initialize the trend detector"""
        # Time periods for trend analysis
        self.time_windows = {
            'emerging': 24,  # hours
            'trending': 72,  # hours
            'seasonal': 168  # hours (1 week)
        }

        # Velocity thresholds for content classification
        self.velocity_thresholds = {
            'viral': 100,  # mentions per hour
            'hot': 50,     # mentions per hour
            'rising': 20   # mentions per hour
        }

    def detect_trending_topics(self, content_data: List[Dict[str, Any]],
                              time_window_hours: int = 72) -> List[Dict[str, Any]]:
        """
        Detect trending topics from content data within a time window

        Args:
            content_data (List[Dict[str, Any]]): Content data with timestamps and topics
            time_window_hours (int): Time window in hours to analyze

        Returns:
            List[Dict[str, Any]]: Trending topics with scores
        """
        print(f"Detecting trending topics in last {time_window_hours} hours...")

        # Filter content within time window
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        recent_content = [
            item for item in content_data
            if self._parse_timestamp(item.get('timestamp', '')) > cutoff_time
        ]

        if not recent_content:
            return []

        # Extract and count topics
        topic_counts = defaultdict(int)
        topic_timestamps = defaultdict(list)

        for item in recent_content:
            # Extract topics from tags
            tags = item.get('tags', [])
            for tag in tags:
                topic_counts[tag] += 1
                topic_timestamps[tag].append(self._parse_timestamp(item.get('timestamp', '')))

            # Extract topics from title and content
            title = item.get('title', '').lower()
            content = item.get('content', '').lower()
            text = title + ' ' + content

            # Simple topic extraction (in a real implementation, use NLP)
            words = re.findall(r'\b\w+\b', text)
            for word in words:
                if len(word) > 3:  # Filter out short words
                    topic_counts[word] += 1
                    topic_timestamps[word].append(self._parse_timestamp(item.get('timestamp', '')))

        # Calculate trend scores
        trends = []
        for topic, count in topic_counts.items():
            if count < 2:  # Filter out rare topics
                continue

            timestamps = topic_timestamps[topic]
            if not timestamps:
                continue

            # Calculate velocity (mentions per hour)
            first_mention = min(timestamps)
            last_mention = max(timestamps)
            duration_hours = max((last_mention - first_mention).total_seconds() / 3600, 1)
            velocity = count / duration_hours

            # Calculate recency score (more recent = higher score)
            latest_mention = max(timestamps)
            hours_since_latest = (datetime.now() - latest_mention).total_seconds() / 3600
            recency_score = max(0, 1 - (hours_since_latest / time_window_hours))

            # Calculate trend score
            trend_score = count * velocity * (0.5 + 0.5 * recency_score)

            trends.append({
                'topic': topic,
                'count': count,
                'velocity': velocity,
                'first_mention': first_mention.isoformat(),
                'last_mention': last_mention.isoformat(),
                'trend_score': trend_score,
                'time_window_hours': time_window_hours
            })

        # Sort by trend score and return top trends
        trends.sort(key=lambda x: x['trend_score'], reverse=True)
        return trends[:50]  # Return top 50 trends

    def detect_emerging_topics(self, content_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect emerging topics that are just starting to gain traction

        Args:
            content_data (List[Dict[str, Any]]): Content data with timestamps and topics

        Returns:
            List[Dict[str, Any]]: Emerging topics
        """
        print("Detecting emerging topics...")

        # Use shorter time window for emerging topics
        emerging_trends = self.detect_trending_topics(content_data, time_window_hours=24)

        # Filter for truly emerging topics (low count but high velocity)
        emerging = []
        for trend in emerging_trends:
            if trend['count'] >= 3 and trend['count'] <= 15 and trend['velocity'] >= 2:
                emerging.append(trend)

        return emerging[:20]  # Return top 20 emerging topics

    def analyze_content_velocity(self, content_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze content velocity to identify viral content

        Args:
            content_items (List[Dict[str, Any]]): Content items with engagement data

        Returns:
            List[Dict[str, Any]]: Content items with velocity classification
        """
        print("Analyzing content velocity...")

        viral_content = []

        for item in content_items:
            # Extract engagement metrics
            views = item.get('views', 0)
            shares = item.get('shares', 0)
            comments = item.get('comments', 0)
            timestamp = self._parse_timestamp(item.get('timestamp', ''))

            if not timestamp:
                continue

            # Calculate engagement velocity
            hours_since_creation = max((datetime.now() - timestamp).total_seconds() / 3600, 1)
            engagement_velocity = (views + shares * 3 + comments * 2) / hours_since_creation

            # Classify content based on velocity
            classification = 'normal'
            if engagement_velocity >= self.velocity_thresholds['viral']:
                classification = 'viral'
            elif engagement_velocity >= self.velocity_thresholds['hot']:
                classification = 'hot'
            elif engagement_velocity >= self.velocity_thresholds['rising']:
                classification = 'rising'

            # Add velocity data to item
            item_with_velocity = item.copy()
            item_with_velocity.update({
                'engagement_velocity': engagement_velocity,
                'velocity_classification': classification,
                'hours_since_creation': hours_since_creation
            })

            viral_content.append(item_with_velocity)

        # Sort by velocity (highest first)
        viral_content.sort(key=lambda x: x['engagement_velocity'], reverse=True)
        return viral_content

    def detect_seasonal_patterns(self, content_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect seasonal and cyclical patterns in content

        Args:
            content_data (List[Dict[str, Any]]): Content data with timestamps

        Returns:
            Dict[str, Any]: Seasonal pattern analysis
        """
        print("Detecting seasonal patterns...")

        # Group content by month and day of week
        monthly_content = defaultdict(int)
        daily_content = defaultdict(int)

        for item in content_data:
            timestamp = self._parse_timestamp(item.get('timestamp', ''))
            if timestamp:
                month_key = timestamp.strftime('%Y-%m')
                day_key = timestamp.strftime('%A')
                monthly_content[month_key] += 1
                daily_content[day_key] += 1

        # Identify peak months and days
        peak_months = sorted(monthly_content.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_days = sorted(daily_content.items(), key=lambda x: x[1], reverse=True)[:3]

        # Calculate average content per month and day
        avg_monthly = sum(monthly_content.values()) / len(monthly_content) if monthly_content else 0
        avg_daily = sum(daily_content.values()) / len(daily_content) if daily_content else 0

        seasonal_analysis = {
            'monthly_patterns': dict(monthly_content),
            'daily_patterns': dict(daily_content),
            'peak_months': peak_months,
            'peak_days': peak_days,
            'average_monthly_content': avg_monthly,
            'average_daily_content': avg_daily,
            'total_analyzed_items': len(content_data)
        }

        return seasonal_analysis

    def prioritize_trending_content(self, trends: List[Dict[str, Any]],
                                  user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Prioritize trending content based on user interests

        Args:
            trends (List[Dict[str, Any]]): Trending topics
            user_profile (Dict[str, Any]): User's interest profile

        Returns:
            List[Dict[str, Any]]: Prioritized trending content
        """
        print("Prioritizing trending content...")

        # Get user's top topics
        user_topics = set(topic for topic, _ in user_profile.get('top_topics', []))

        # Score trends based on user interest
        scored_trends = []
        for trend in trends:
            topic = trend['topic']
            base_score = trend['trend_score']

            # Boost score if topic matches user interests
            interest_boost = 1.0
            if topic in user_topics:
                interest_boost = 2.0  # Double score for matching interests

            # Calculate final score
            final_score = base_score * interest_boost

            trend_with_score = trend.copy()
            trend_with_score['user_interest_score'] = final_score
            trend_with_score['interest_match'] = topic in user_topics

            scored_trends.append(trend_with_score)

        # Sort by user interest score
        scored_trends.sort(key=lambda x: x['user_interest_score'], reverse=True)
        return scored_trends

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp string to datetime object

        Args:
            timestamp_str (str): Timestamp string

        Returns:
            datetime: Parsed datetime object
        """
        if not timestamp_str:
            return datetime.min

        # Try different timestamp formats
        formats = [
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S%z'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # If all formats fail, return minimum datetime
        return datetime.min


def main():
    """Example usage of TrendDetector"""
    # Create trend detector
    trend_detector = TrendDetector()

    # Sample content data
    sample_content = [
        {
            'title': 'Python 3.12 New Features',
            'tags': ['python', 'programming', 'release'],
            'timestamp': '2023-06-01T10:00:00Z',
            'views': 1500,
            'shares': 50,
            'comments': 25
        },
        {
            'title': 'JavaScript Framework Performance Comparison',
            'tags': ['javascript', 'web-development', 'performance'],
            'timestamp': '2023-06-01T12:00:00Z',
            'views': 2200,
            'shares': 80,
            'comments': 40
        },
        {
            'title': 'Machine Learning Model Optimization',
            'tags': ['machine-learning', 'ai', 'optimization'],
            'timestamp': '2023-06-01T14:00:00Z',
            'views': 1800,
            'shares': 60,
            'comments': 30
        },
        {
            'title': 'Docker Security Best Practices',
            'tags': ['devops', 'docker', 'security'],
            'timestamp': '2023-06-01T16:00:00Z',
            'views': 1200,
            'shares': 40,
            'comments': 20
        },
        {
            'title': 'Cybersecurity Threat Landscape 2023',
            'tags': ['cybersecurity', 'security', 'threats'],
            'timestamp': '2023-06-01T18:00:00Z',
            'views': 2500,
            'shares': 90,
            'comments': 50
        }
    ]

    # Add more recent content to simulate trends
    recent_time = datetime.now() - timedelta(hours=12)
    for i in range(10):
        sample_content.append({
            'title': f'Emerging Tech Trend {i+1}',
            'tags': ['ai', 'emerging-tech'],
            'timestamp': recent_time.isoformat() + 'Z',
            'views': 100 + i * 50,
            'shares': 5 + i * 2,
            'comments': 2 + i
        })

    # Detect trending topics
    print("Detecting trending topics...")
    trends = trend_detector.detect_trending_topics(sample_content, time_window_hours=72)

    # Display top trends
    print(f"\nTop 5 Trending Topics:")
    for trend in trends[:5]:
        print(f"  - {trend['topic']}: {trend['count']} mentions, "
              f"velocity: {trend['velocity']:.2f}, score: {trend['trend_score']:.2f}")

    # Detect emerging topics
    print("\nDetecting emerging topics...")
    emerging = trend_detector.detect_emerging_topics(sample_content)

    # Display emerging topics
    print(f"\nTop 5 Emerging Topics:")
    for topic in emerging[:5]:
        print(f"  - {topic['topic']}: {topic['count']} mentions, "
              f"velocity: {topic['velocity']:.2f}, score: {topic['trend_score']:.2f}")

    # Analyze content velocity
    print("\nAnalyzing content velocity...")
    viral_content = trend_detector.analyze_content_velocity(sample_content)

    # Display viral content
    print(f"\nTop 5 Viral Content Items:")
    for item in viral_content[:5]:
        print(f"  - {item['title']}: velocity {item['engagement_velocity']:.2f}, "
              f"classification: {item['velocity_classification']}")

    # Detect seasonal patterns
    print("\nDetecting seasonal patterns...")
    seasonal_patterns = trend_detector.detect_seasonal_patterns(sample_content)

    # Display seasonal patterns
    print(f"\nSeasonal Patterns:")
    print(f"  Peak Months: {seasonal_patterns['peak_months']}")
    print(f"  Peak Days: {seasonal_patterns['peak_days']}")
    print(f"  Average Monthly Content: {seasonal_patterns['average_monthly_content']:.2f}")
    print(f"  Average Daily Content: {seasonal_patterns['average_daily_content']:.2f}")


if __name__ == "__main__":
    main()