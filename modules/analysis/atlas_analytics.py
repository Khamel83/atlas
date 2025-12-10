#!/usr/bin/env python3
"""
Atlas Real-Time Analytics Engine
Processes log-stream data to provide instant analytics without database queries
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
import time

class AtlasAnalytics:
    """Real-time analytics engine for Atlas log-stream data"""

    def __init__(self, log_file: str = "atlas_operations.log"):
        self.log_file = log_file
        self.processed_log_file = "logs/processed_episodes.log"

        # Real-time analytics cache
        self.cache = {
            'total_discovered': 0,
            'total_processed': 0,
            'total_failed': 0,
            'sources': Counter(),
            'networks': Counter(),
            'recent_activity': [],
            'hourly_stats': defaultdict(lambda: {'discovered': 0, 'processed': 0, 'failed': 0}),
            'daily_stats': defaultdict(lambda: {'discovered': 0, 'processed': 0, 'failed': 0}),
            'last_update': time.time()
        }

        # Performance metrics
        self.cache_update_time = 0
        self.cache_size = 0

    def parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single log line and extract structured data"""
        try:
            parts = line.strip().split('|')
            if len(parts) < 6:
                return None

            timestamp, event_type, content_type, source, item_id, data_json = parts[:6]

            # Parse timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                dt = datetime.now(timezone.utc)

            # Parse JSON data
            try:
                data = json.loads(data_json)
            except (json.JSONDecodeError, TypeError):
                data = {}

            return {
                'timestamp': dt,
                'event_type': event_type,
                'content_type': content_type,
                'source': source,
                'item_id': item_id,
                'data': data,
                'raw_line': line.strip()
            }

        except Exception as e:
            return None

    def update_cache(self, force: bool = False) -> bool:
        """Update analytics cache from log files"""
        current_time = time.time()

        # Only update cache every 30 seconds unless forced
        if not force and (current_time - self.cache_update_time) < 30:
            return False

        try:
            # Reset recent activity (keep last 100 events)
            self.cache['recent_activity'] = self.cache['recent_activity'][-100:]

            # Process main operations log
            if os.path.exists(self.log_file):
                self._process_log_file(self.log_file, self.cache)

            # Process completed episodes log
            if os.path.exists(self.processed_log_file):
                self._process_log_file(self.processed_log_file, self.cache)

            # Update cache metadata
            self.cache_update_time = current_time
            self.cache_size = sum(len(v) if isinstance(v, list) else 1 for v in self.cache.values() if isinstance(v, (list, dict, Counter)))

            return True

        except Exception as e:
            print(f"Error updating analytics cache: {e}")
            return False

    def _process_log_file(self, log_file: str, cache: Dict[str, Any]):
        """Process a single log file and update cache"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # Get file size for efficient processing
                file_size = os.path.getsize(log_file)
                if file_size > 10 * 1024 * 1024:  # 10MB+ files
                    # Process only last 1000 lines for large files
                    lines = f.readlines()[-1000:]
                else:
                    lines = f.readlines()

                for line in lines:
                    event = self.parse_log_line(line)
                    if not event:
                        continue

                    # Update counters based on event type
                    if event['event_type'] == 'DISCOVER':
                        cache['total_discovered'] += 1
                        cache['sources'][event['source']] += 1

                        # Extract network from data if available
                        if 'network' in event['data']:
                            cache['networks'][event['data']['network']] += 1

                    elif event['event_type'] == 'COMPLETE':
                        cache['total_processed'] += 1

                    elif event['event_type'] == 'FAIL':
                        cache['total_failed'] += 1

                    # Add to recent activity
                    cache['recent_activity'].append(event)

                    # Update time-based stats
                    hour_key = event['timestamp'].strftime('%Y-%m-%d-%H')
                    day_key = event['timestamp'].strftime('%Y-%m-%d')

                    if event['event_type'] == 'DISCOVER':
                        cache['hourly_stats'][hour_key]['discovered'] += 1
                        cache['daily_stats'][day_key]['discovered'] += 1
                    elif event['event_type'] == 'COMPLETE':
                        cache['hourly_stats'][hour_key]['processed'] += 1
                        cache['daily_stats'][day_key]['processed'] += 1
                    elif event['event_type'] == 'FAIL':
                        cache['hourly_stats'][hour_key]['failed'] += 1
                        cache['daily_stats'][day_key]['failed'] += 1

        except Exception as e:
            print(f"Error processing log file {log_file}: {e}")

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics"""
        self.update_cache()

        current_time = datetime.now(timezone.utc)
        recent_hour = current_time - timedelta(hours=1)
        recent_day = current_time - timedelta(days=1)

        # Count recent activity
        recent_discoveries = sum(1 for event in self.cache['recent_activity']
                                if event['event_type'] == 'DISCOVER' and event['timestamp'] > recent_hour)

        recent_processing = sum(1 for event in self.cache['recent_activity']
                              if event['event_type'] in ['COMPLETE', 'FAIL'] and event['timestamp'] > recent_hour)

        # Calculate success rate
        total_attempts = self.cache['total_processed'] + self.cache['total_failed']
        success_rate = (self.cache['total_processed'] / total_attempts * 100) if total_attempts > 0 else 0

        # Get top performing sources
        top_sources = dict(self.cache['sources'].most_common(10))

        # Get top networks
        top_networks = dict(self.cache['networks'].most_common(10))

        # Calculate processing rate (episodes per hour)
        current_hour = current_time.strftime('%Y-%m-%d-%H')
        hourly_processed = self.cache['hourly_stats'].get(current_hour, {}).get('processed', 0)

        return {
            'timestamp': current_time.isoformat(),
            'cache_updated': self.cache_update_time,
            'totals': {
                'discovered': self.cache['total_discovered'],
                'processed': self.cache['total_processed'],
                'failed': self.cache['total_failed'],
                'success_rate': round(success_rate, 2)
            },
            'recent_activity': {
                'last_hour_discoveries': recent_discoveries,
                'last_hour_processing': recent_processing,
                'current_hour_processed': hourly_processed
            },
            'top_sources': top_sources,
            'top_networks': top_networks,
            'performance': {
                'episodes_per_hour': hourly_processed,
                'cache_size': self.cache_size,
                'recent_events': len(self.cache['recent_activity'])
            }
        }

    def get_hourly_trends(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly processing trends"""
        self.update_cache()

        current_time = datetime.now(timezone.utc)
        trends = []

        for i in range(hours):
            hour_time = current_time - timedelta(hours=i)
            hour_key = hour_time.strftime('%Y-%m-%d-%H')

            stats = self.cache['hourly_stats'].get(hour_key, {'discovered': 0, 'processed': 0, 'failed': 0})

            trends.append({
                'hour': hour_key,
                'timestamp': hour_time.isoformat(),
                'discovered': stats['discovered'],
                'processed': stats['processed'],
                'failed': stats['failed'],
                'success_rate': round((stats['processed'] / (stats['processed'] + stats['failed']) * 100), 2) if (stats['processed'] + stats['failed']) > 0 else 0
            })

        return list(reversed(trends))  # Most recent first

    def get_daily_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily processing summary"""
        self.update_cache()

        current_time = datetime.now(timezone.utc)
        summary = []

        for i in range(days):
            day_time = current_time - timedelta(days=i)
            day_key = day_time.strftime('%Y-%m-%d')

            stats = self.cache['daily_stats'].get(day_key, {'discovered': 0, 'processed': 0, 'failed': 0})

            summary.append({
                'day': day_key,
                'date': day_time.strftime('%Y-%m-%d'),
                'discovered': stats['discovered'],
                'processed': stats['processed'],
                'failed': stats['failed'],
                'success_rate': round((stats['processed'] / (stats['processed'] + stats['failed']) * 100), 2) if (stats['processed'] + stats['failed']) > 0 else 0
            })

        return list(reversed(summary))  # Most recent first

    def get_source_performance(self, source: str = None) -> Dict[str, Any]:
        """Get performance metrics for a specific source or all sources"""
        self.update_cache()

        if source:
            # Filter events for specific source
            source_events = [e for e in self.cache['recent_activity'] if e['source'] == source]

            discovered = sum(1 for e in source_events if e['event_type'] == 'DISCOVER')
            processed = sum(1 for e in source_events if e['event_type'] == 'COMPLETE')
            failed = sum(1 for e in source_events if e['event_type'] == 'FAIL')

            return {
                'source': source,
                'discovered': discovered,
                'processed': processed,
                'failed': failed,
                'success_rate': round((processed / (processed + failed) * 100), 2) if (processed + failed) > 0 else 0,
                'total_events': len(source_events)
            }
        else:
            # Return summary for all sources
            return dict(self.cache['sources'])

    def get_health_score(self) -> Dict[str, Any]:
        """Calculate real-time health score (0-100)"""
        self.update_cache()

        current_time = datetime.now(timezone.utc)
        recent_activity = [e for e in self.cache['recent_activity'] if e['timestamp'] > current_time - timedelta(minutes=30)]

        # Activity score (0-40 points)
        activity_score = min(len(recent_activity) * 2, 40)

        # Success rate score (0-30 points)
        total_attempts = self.cache['total_processed'] + self.cache['total_failed']
        success_rate = (self.cache['total_processed'] / total_attempts * 100) if total_attempts > 0 else 0
        success_score = min(success_rate * 0.3, 30)

        # Processing rate score (0-20 points)
        current_hour = current_time.strftime('%Y-%m-%d-%H')
        hourly_processed = self.cache['hourly_stats'].get(current_hour, {}).get('processed', 0)
        processing_score = min(hourly_processed * 0.2, 20)

        # Source diversity score (0-10 points)
        source_diversity = min(len(self.cache['sources']) * 0.5, 10)

        total_score = activity_score + success_score + processing_score + source_diversity

        # Determine status
        if total_score >= 80:
            status = "ACTIVE"
        elif total_score >= 60:
            status = "RUNNING"
        elif total_score >= 40:
            status = "IDLE"
        elif total_score >= 20:
            status = "DEGRADED"
        else:
            status = "STOPPED"

        return {
            'health_score': round(total_score, 1),
            'status': status,
            'components': {
                'activity_score': activity_score,
                'success_score': success_score,
                'processing_score': processing_score,
                'diversity_score': source_diversity
            },
            'timestamp': current_time.isoformat()
        }

    def export_analytics(self, format: str = 'json') -> str:
        """Export analytics data in specified format"""
        self.update_cache()

        data = {
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'real_time_metrics': self.get_real_time_metrics(),
            'hourly_trends': self.get_hourly_trends(24),
            'daily_summary': self.get_daily_summary(7),
            'health_score': self.get_health_score()
        }

        if format.lower() == 'json':
            return json.dumps(data, indent=2)
        elif format.lower() == 'csv':
            # Generate CSV summary
            csv_lines = []
            csv_lines.append("timestamp,discovered,processed,failed,success_rate")
            for day_data in data['daily_summary']:
                csv_lines.append(f"{day_data['date']},{day_data['discovered']},{day_data['processed']},{day_data['failed']},{day_data['success_rate']}")
            return '\n'.join(csv_lines)
        else:
            return json.dumps(data, indent=2)

def main():
    """Test the analytics engine"""
    analytics = AtlasAnalytics()

    print("🔍 Atlas Analytics Engine Test")
    print("=" * 40)

    # Update cache
    print("📊 Updating analytics cache...")
    analytics.update_cache(force=True)

    # Get real-time metrics
    metrics = analytics.get_real_time_metrics()
    print(f"\n📈 Real-Time Metrics:")
    print(f"   Total Discovered: {metrics['totals']['discovered']}")
    print(f"   Total Processed: {metrics['totals']['processed']}")
    print(f"   Total Failed: {metrics['totals']['failed']}")
    print(f"   Success Rate: {metrics['totals']['success_rate']}%")

    # Get health score
    health = analytics.get_health_score()
    print(f"\n💚 Health Score: {health['health_score']}/100 ({health['status']})")

    # Get hourly trends
    trends = analytics.get_hourly_trends(6)
    print(f"\n📊 Hourly Trends (last 6 hours):")
    for trend in trends:
        print(f"   {trend['hour']}: {trend['processed']} processed, {trend['success_rate']}% success")

    # Export analytics
    export_json = analytics.export_analytics('json')
    export_file = "atlas_analytics_export.json"

    with open(export_file, 'w') as f:
        f.write(export_json)

    print(f"\n💾 Analytics exported to: {export_file}")

if __name__ == "__main__":
    main()