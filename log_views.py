#!/usr/bin/env python3
"""
OOS Log-Stream Analytics Views
Virtual views derived from log events instead of database queries
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import os

class LogViews:
    """Analytics views derived from log events"""

    def __init__(self, log_file: str = "oos.log"):
        self.log_file = log_file
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    def _parse_event_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single log event line"""
        try:
            parts = line.strip().split('|')
            if len(parts) != 6:
                return None

            timestamp, event_type, content_type, source, item_id, data_json = parts

            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                # Make timezone-naive for comparison
                timestamp = timestamp.replace(tzinfo=None)
            except ValueError:
                return None

            # Parse JSON data
            try:
                data = json.loads(data_json)
            except json.JSONDecodeError:
                data = {}

            return {
                'timestamp': timestamp,
                'event_type': event_type,
                'content_type': content_type,
                'source': source,
                'item_id': item_id,
                'data': data,
                'raw_line': line.strip()
            }
        except Exception:
            return None

    def _read_log_events(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read and parse log events"""
        events = []

        if not os.path.exists(self.log_file):
            return events

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Process in reverse order for recent events first
            for line in reversed(lines):
                event = self._parse_event_line(line)
                if event:
                    if since and event['timestamp'] < since:
                        continue
                    events.append(event)
                    if limit and len(events) >= limit:
                        break

        except IOError as e:
            print(f"Error reading log file: {e}", file=os.sys.stderr)

        return events

    def podcast_status_view(self) -> Dict[str, int]:
        """Current podcast processing status"""
        cache_key = 'podcast_status'
        if cache_key in self.cache:
            return self.cache[cache_key]

        events = self._read_log_events()

        status = {
            'discovered': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
            'pending': 0
        }

        # Track item states
        item_states = {}

        for event in events:
            if event['content_type'] != 'podcast':
                continue

            item_id = event['item_id']
            event_type = event['event_type']

            if event_type == 'DISCOVER':
                if item_id not in item_states:
                    item_states[item_id] = 'discovered'
                    status['discovered'] += 1

            elif event_type == 'PROCESS':
                if item_states.get(item_id) in ['discovered', 'processing']:
                    item_states[item_id] = 'processing'
                    status['processing'] += 1
                    if item_states.get(item_id) == 'discovered':
                        status['discovered'] -= 1

            elif event_type == 'COMPLETE':
                if item_states.get(item_id) in ['processing', 'discovered']:
                    item_states[item_id] = 'completed'
                    status['completed'] += 1
                    if item_states.get(item_id) == 'processing':
                        status['processing'] -= 1
                    elif item_states.get(item_id) == 'discovered':
                        status['discovered'] -= 1

            elif event_type == 'FAIL':
                if item_states.get(item_id) in ['processing', 'discovered']:
                    item_states[item_id] = 'failed'
                    status['failed'] += 1
                    if item_states.get(item_id) == 'processing':
                        status['processing'] -= 1
                    elif item_states.get(item_id) == 'discovered':
                        status['discovered'] -= 1

        # Calculate pending as discovered - completed - failed
        status['pending'] = status['discovered'] - status['completed'] - status['failed']

        self.cache[cache_key] = status
        return status

    def throughput_view(self, timeframe: str = '1h') -> Dict[str, Any]:
        """Processing throughput over time"""
        cache_key = f'throughput_{timeframe}'
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Parse timeframe
        hours = 1
        if timeframe.endswith('h'):
            hours = int(timeframe[:-1])
        elif timeframe.endswith('d'):
            hours = int(timeframe[:-1]) * 24

        since = datetime.now() - timedelta(hours=hours)
        events = self._read_log_events(since=since)

        # Count completion events by time windows
        time_windows = defaultdict(int)
        current_time = datetime.now()

        # Create hourly buckets
        for i in range(hours):
            window_start = current_time - timedelta(hours=i+1)
            window_end = current_time - timedelta(hours=i)
            window_key = window_start.strftime('%Y-%m-%dT%H:00:00Z')
            time_windows[window_key] = 0

        # Count completions in each window
        for event in events:
            if event['event_type'] == 'COMPLETE':
                for window_start in time_windows:
                    window_start_dt = datetime.fromisoformat(window_start.replace('Z', '+00:00')).replace(tzinfo=None)
                    window_end_dt = window_start_dt + timedelta(hours=1)
                    if window_start_dt <= event['timestamp'] < window_end_dt:
                        time_windows[window_start] += 1
                        break

        result = {
            'timeframe': timeframe,
            'total_completed': sum(time_windows.values()),
            'hourly_breakdown': dict(time_windows),
            'average_per_hour': sum(time_windows.values()) / max(hours, 1)
        }

        self.cache[cache_key] = result
        return result

    def error_analysis_view(self) -> Dict[str, Any]:
        """Error patterns and analysis"""
        cache_key = 'error_analysis'
        if cache_key in self.cache:
            return self.cache[cache_key]

        events = self._read_log_events()

        analysis = {
            'total_failures': 0,
            'error_types': Counter(),
            'source_errors': Counter(),
            'content_type_errors': Counter(),
            'recent_failures': [],
            'retry_counts': defaultdict(int)
        }

        for event in events:
            if event['event_type'] == 'FAIL':
                analysis['total_failures'] += 1

                # Error type analysis
                error = event['data'].get('error', 'unknown')
                analysis['error_types'][error] += 1

                # Source analysis
                analysis['source_errors'][event['source']] += 1

                # Content type analysis
                analysis['content_type_errors'][event['content_type']] += 1

                # Recent failures (last 24 hours)
                if event['timestamp'] > datetime.now() - timedelta(hours=24):
                    analysis['recent_failures'].append({
                        'timestamp': event['timestamp'].isoformat(),
                        'source': event['source'],
                        'content_type': event['content_type'],
                        'error': error
                    })

                # Retry counts
                retry_count = event['data'].get('retry_count', 0)
                if retry_count > 0:
                    analysis['retry_counts'][retry_count] += 1

        # Convert Counter objects to dicts for JSON serialization
        analysis['error_types'] = dict(analysis['error_types'])
        analysis['source_errors'] = dict(analysis['source_errors'])
        analysis['content_type_errors'] = dict(analysis['content_type_errors'])
        analysis['retry_counts'] = dict(analysis['retry_counts'])

        self.cache[cache_key] = analysis
        return analysis

    def source_reliability_view(self) -> Dict[str, Any]:
        """Source system reliability metrics"""
        cache_key = 'source_reliability'
        if cache_key in self.cache:
            return self.cache[cache_key]

        events = self._read_log_events()

        source_stats = defaultdict(lambda: {
            'discovered': 0,
            'completed': 0,
            'failed': 0,
            'processing_times': []
        })

        # Track processing start times
        processing_starts = {}

        for event in events:
            source = event['source']
            item_id = event['item_id']
            event_type = event['event_type']
            timestamp = event['timestamp']

            if event_type == 'DISCOVER':
                source_stats[source]['discovered'] += 1

            elif event_type == 'PROCESS':
                processing_starts[(source, item_id)] = timestamp

            elif event_type == 'COMPLETE':
                source_stats[source]['completed'] += 1
                if (source, item_id) in processing_starts:
                    processing_time = (timestamp - processing_starts[(source, item_id)]).total_seconds()
                    source_stats[source]['processing_times'].append(processing_time)
                    del processing_starts[(source, item_id)]

            elif event_type == 'FAIL':
                source_stats[source]['failed'] += 1
                if (source, item_id) in processing_starts:
                    del processing_starts[(source, item_id)]

        # Calculate reliability metrics
        reliability = {}
        for source, stats in source_stats.items():
            total_attempts = stats['completed'] + stats['failed']
            success_rate = stats['completed'] / total_attempts if total_attempts > 0 else 0

            avg_processing_time = (
                sum(stats['processing_times']) / len(stats['processing_times'])
                if stats['processing_times'] else 0
            )

            reliability[source] = {
                'success_rate': round(success_rate, 3),
                'total_processed': stats['completed'],
                'total_failed': stats['failed'],
                'total_attempts': total_attempts,
                'average_processing_time': round(avg_processing_time, 2),
                'discovered': stats['discovered']
            }

        self.cache[cache_key] = reliability
        return reliability

    def system_health_view(self) -> Dict[str, Any]:
        """Overall system health metrics"""
        cache_key = 'system_health'
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Get recent activity (last hour)
        since = datetime.now() - timedelta(hours=1)
        recent_events = self._read_log_events(since=since)

        # Count events by type
        event_counts = Counter(event['event_type'] for event in recent_events)

        # Get status metrics
        podcast_status = self.podcast_status_view()
        error_analysis = self.error_analysis_view()

        health = {
            'recent_activity_1h': len(recent_events),
            'event_counts': dict(event_counts),
            'podcast_status': podcast_status,
            'error_rate_1h': error_analysis['total_failures'],
            'last_activity': recent_events[0]['timestamp'].isoformat() if recent_events else None,
            'system_uptime': self._get_uptime()
        }

        self.cache[cache_key] = health
        return health

    def _get_uptime(self) -> str:
        """Get system uptime based on log file creation"""
        try:
            if os.path.exists(self.log_file):
                creation_time = datetime.fromtimestamp(os.path.getctime(self.log_file))
                uptime = datetime.now() - creation_time
                days = uptime.days
                hours = uptime.seconds // 3600
                minutes = (uptime.seconds % 3600) // 60
                return f"{days}d {hours}h {minutes}m"
        except:
            pass
        return "Unknown"

    def clear_cache(self):
        """Clear the view cache"""
        self.cache.clear()

# Global views instance
_views = None

def get_views(log_file: str = "oos.log") -> LogViews:
    """Get or create the global views instance"""
    global _views
    if _views is None or _views.log_file != log_file:
        _views = LogViews(log_file)
    return _views

# Convenience functions for direct use
def podcast_status() -> Dict[str, int]:
    """Get current podcast processing status"""
    return get_views().podcast_status_view()

def throughput(timeframe: str = '1h') -> Dict[str, Any]:
    """Get processing throughput"""
    return get_views().throughput_view(timeframe)

def error_analysis() -> Dict[str, Any]:
    """Get error analysis"""
    return get_views().error_analysis_view()

def source_reliability() -> Dict[str, Any]:
    """Get source reliability metrics"""
    return get_views().source_reliability_view()

def system_health() -> Dict[str, Any]:
    """Get system health metrics"""
    return get_views().system_health_view()

if __name__ == "__main__":
    # Simple test
    views = get_views("test_oos.log")

    print("📊 Podcast Status:")
    print(json.dumps(views.podcast_status_view(), indent=2))

    print("\n📈 Throughput:")
    print(json.dumps(views.throughput_view(), indent=2))

    print("\n🔍 Error Analysis:")
    print(json.dumps(views.error_analysis_view(), indent=2))

    print("\n✅ Log Views test completed")