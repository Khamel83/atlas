#!/usr/bin/env python3
"""
Morning Status Dashboard
Instantly answers "how are we doing?" with complete status
Combines all tracking systems into one comprehensive report
"""

import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MorningStatusDashboard:
    """Comprehensive morning status dashboard"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")

        # All the tracking files
        self.transcripts_dir = self.root_dir / "transcripts"
        self.url_tracking_db = self.root_dir / "url_ingestion.db"
        self.podcast_db = self.root_dir / "podcast_processing.db"
        self.master_csv = self.root_dir / "master_url_ingestion_log.csv"
        self.summary_json = self.root_dir / "url_ingestion_summary.json"
        self.progress_files = list(self.root_dir.glob("overnight_progress_*.json"))

        # Output formatting
        self.console_width = 80

    def get_system_status(self):
        """Get overall system status"""
        try:
            # Check if overnight processor is running
            import subprocess
            result = subprocess.run(['pgrep', '-f', 'simple_overnight_processor.py'],
                                   capture_output=True, text=True)
            processor_running = bool(result.returncode == 0)

            return {
                'status': '🟢 RUNNING' if processor_running else '🔴 STOPPED',
                'processor_running': processor_running,
                'last_check': datetime.now().isoformat()
            }
        except:
            return {'status': '❓ UNKNOWN', 'processor_running': False, 'last_check': datetime.now().isoformat()}

    def get_transcript_counts(self):
        """Get comprehensive transcript statistics"""
        if not self.transcripts_dir.exists():
            return {'total': 0, 'by_method': {}, 'by_podcast': {}, 'size_mb': 0}

        total_files = len(list(self.transcripts_dir.glob("*.md")))

        # By extraction method
        by_method = defaultdict(int)
        by_podcast = defaultdict(int)
        total_size = 0

        for transcript_file in self.transcripts_dir.glob("*.md"):
            try:
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_size += len(content.encode('utf-8'))

                    # Extract method from filename
                    filename = transcript_file.name
                    if 'WAYBACK' in filename:
                        by_method['Wayback'] += 1
                    elif 'Simple' in filename:
                        by_method['Simple'] += 1
                    else:
                        by_method['Other'] += 1

                    # Extract podcast from content
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith('**Podcast:'):
                            podcast = line.split(':', 1)[1].strip()
                            by_podcast[podcast] += 1
                            break

            except Exception as e:
                logger.error(f"Error reading {transcript_file}: {e}")

        return {
            'total': total_files,
            'by_method': dict(by_method),
            'by_podcast': dict(by_podcast),
            'size_mb': round(total_size / (1024 * 1024), 2)
        }

    def get_url_tracking_stats(self):
        """Get URL tracking statistics"""
        if not self.url_tracking_db.exists():
            return {'error': 'No URL tracking database found'}

        conn = sqlite3.connect(str(self.url_tracking_db))
        try:
            # Overall stats
            cursor = conn.execute('''
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN success = 1 THEN 1 END) as successful,
                    COUNT(CASE WHEN success = 0 THEN 1 END) as failed,
                    COUNT(DISTINCT podcast_name) as unique_podcasts,
                    COUNT(DISTINCT source_type) as unique_sources,
                    COUNT(DISTINCT source_url) as unique_urls,
                    SUM(content_length) as total_chars,
                    AVG(processing_time_seconds) as avg_time
                FROM url_ingestions
            ''')
            overall = cursor.fetchone()

            # By source type
            cursor = conn.execute('''
                SELECT source_type, COUNT(*) as total, COUNT(CASE WHEN success = 1 THEN 1 END) as successful
                FROM url_ingestions
                GROUP BY source_type
                ORDER BY total DESC
            ''')
            by_source = cursor.fetchall()

            # Recent activity (last hour)
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor = conn.execute('''
                SELECT COUNT(*) as recent_count
                FROM url_ingestions
                WHERE timestamp > ?
            ''', (one_hour_ago,))
            recent = cursor.fetchone()

            return {
                'total_attempts': overall[0],
                'successful': overall[1],
                'failed': overall[2],
                'success_rate': (overall[1] / overall[0] * 100) if overall[0] > 0 else 0,
                'unique_podcasts': overall[3],
                'unique_sources': overall[4],
                'unique_urls': overall[5],
                'total_characters': overall[6],
                'avg_processing_time': overall[7],
                'last_hour_count': recent[0] if recent else 0,
                'by_source_type': [
                    {'type': row[0], 'total': row[1], 'success': row[2], 'rate': (row[2]/row[1]*100) if row[1] > 0 else 0}
                    for row in by_source
                ]
            }

        except Exception as e:
            logger.error(f"Error reading URL tracking: {e}")
            return {'error': str(e)}
        finally:
            conn.close()

    def get_podcast_database_stats(self):
        """Get podcast database statistics"""
        if not self.podcast_db.exists():
            return {'error': 'No podcast database found'}

        conn = sqlite3.connect(str(self.podcast_db))
        try:
            # Episode statistics
            cursor = conn.execute('''
                SELECT
                    COUNT(*) as total_episodes,
                    COUNT(CASE WHEN transcript_found = 1 THEN 1 END) as with_transcript,
                    COUNT(CASE WHEN transcript_found = 0 THEN 1 END) as without_transcript
                FROM episodes
            ''')
            episode_stats = cursor.fetchone()

            # Podcast count
            cursor = conn.execute('SELECT COUNT(*) FROM podcasts')
            total_podcasts = cursor.fetchone()[0]

            completion_rate = (episode_stats[1] / episode_stats[0] * 100) if episode_stats[0] > 0 else 0

            return {
                'total_podcasts': total_podcasts,
                'total_episodes': episode_stats[0],
                'episodes_with_transcripts': episode_stats[1],
                'episodes_without_transcripts': episode_stats[2],
                'completion_rate': completion_rate
            }

        except Exception as e:
            logger.error(f"Error reading podcast database: {e}")
            return {'error': str(e)}
        finally:
            conn.close()

    def get_progress_files_status(self):
        """Analyze progress files"""
        if not self.progress_files:
            return {'total': 0, 'latest': None, 'trend': 'no_data'}

        # Sort by timestamp
        progress_files = sorted(self.progress_files, key=lambda x: x.stat().st_mtime, reverse=True)

        latest_file = progress_files[0] if progress_files else None

        # Read latest progress
        latest_data = None
        if latest_file:
            try:
                with open(latest_file, 'r') as f:
                    latest_data = json.load(f)
            except:
                pass

        # Calculate trend
        if len(progress_files) >= 3:
            oldest_file = progress_files[-1]
            try:
                with open(oldest_file, 'r') as f:
                    oldest_data = json.load(f)
                    old_processed = oldest_data.get('stats', {}).get('processed', 0)
                new_processed = latest_data.get('stats', {}).get('processed', 0) if latest_data else 0
                if new_processed > old_processed:
                    trend = 'increasing'
                elif new_processed < old_processed:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            except:
                trend = 'unknown'
        else:
            trend = 'insufficient_data'

        return {
            'total_files': len(progress_files),
            'latest_file': latest_file.name if latest_file else None,
            'latest_timestamp': latest_data.get('timestamp') if latest_data else None,
            'latest_processed': latest_data.get('stats', {}).get('processed', 0) if latest_data else 0,
            'trend': trend
        }

    def calculate_completion_projection(self):
        """Calculate when all transcripts will be completed"""
        url_stats = self.get_url_tracking_stats()
        podcast_stats = self.get_podcast_database_stats()

        if 'error' in url_stats or 'error' in podcast_stats:
            return {'error': 'Cannot calculate projection'}

        current_success_rate = url_stats['success_rate'] / 100
        episodes_remaining = podcast_stats['episodes_without_transcripts']

        if current_success_rate == 0:
            return {'error': 'No success to base projection on'}

        current_rate_per_hour = url_stats.get('last_hour_count', 0)

        if current_rate_per_hour > 0:
            hours_needed = episodes_remaining / current_rate_per_hour
        else:
            # Use overall rate
            if 'total_attempts' in url_stats and url_stats['total_attempts'] > 0:
                avg_rate = url_stats['total_attempts'] / 6  # Last ~6 hours of data
                if avg_rate > 0:
                    hours_needed = episodes_remaining / avg_rate
                else:
                    hours_needed = float('inf')
            else:
                hours_needed = float('inf')

        if hours_needed == float('inf'):
            return {'error': 'Cannot determine processing rate'}

        completion_time = datetime.now() + timedelta(hours=hours_needed)
        return {
            'episodes_remaining': episodes_remaining,
            'current_rate_per_hour': current_rate_per_hour,
            'success_rate': current_success_rate * 100,
            'estimated_completion_hours': round(hours_needed, 1),
            'estimated_completion_time': completion_time.isoformat(),
            'days_remaining': round(hours_needed / 24, 1)
        }

    def generate_morning_report(self):
        """Generate comprehensive morning status report"""
        print("\n" + "="*80)
        print("🌅 ATLAS TRANSCRIPT PROCESSING - MORNING STATUS DASHBOARD")
        print("="*80)
        print(f"📅 Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌍 Current Time: {datetime.now().strftime('%I:%M %p')}")

        # System Status
        system_status = self.get_system_status()
        print(f"\n🖥️  SYSTEM STATUS: {system_status['status']}")
        print(f"   Overnight Processor: {'🟢 RUNNING' if system_status['processor_running'] else '🔴 STOPPED'}")

        # Transcript Overview
        transcript_stats = self.get_transcript_counts()
        print(f"\n📝 TRANSCRIPT OVERVIEW:")
        print(f"   Total Transcripts: {transcript_stats['total']}")
        print(f"   Total Size: {transcript_stats['size_mb']} MB")

        if transcript_stats['by_method']:
            print(f"   By Method: {dict(transcript_stats['by_method'])}")

        if transcript_stats['by_podcast']:
            top_podcasts = sorted(transcript_stats['by_podcast'].items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"   Top Podcasts: {dict(top_podcasts)}")

        # URL Tracking Stats
        url_stats = self.get_url_tracking_stats()
        if 'error' not in url_stats:
            print(f"\n🔗 URL TRACKING:")
            print(f"   Total Attempts: {url_stats['total_attempts']}")
            print(f"   Successful: {url_stats['successful']}")
            print(f"   Failed: {url_stats['failed']}")
            print(f"   Success Rate: {url_stats['success_rate']:.1f}%")
            print(f"   Unique Podcasts: {url_stats['unique_podcasts']}")
            print(f"   Unique Sources: {url_stats['unique_sources']}")
            print(f"   Last Hour Activity: {url_stats['last_hour_count']} attempts")
            print(f"   Total Content: {url_stats['total_characters']:,} characters")

            if url_stats['by_source_type']:
                print(f"   Source Types: {len(url_stats['by_source_type'])} active")
                for source in url_stats['by_source_type'][:5]:
                    print(f"      • {source['type']}: {source['total']} attempts, {source['rate']:.1f}% success")

        # Podcast Database Stats
        podcast_stats = self.get_podcast_database_stats()
        if 'error' not in podcast_stats:
            print(f"\n📚 PODCAST DATABASE:")
            print(f"   Total Podcasts: {podcast_stats['total_podcasts']}")
            print(f"   Total Episodes: {podcast_stats['total_episodes']}")
            print(f"   Episodes with Transcripts: {podcast_stats['episodes_with_transcripts']}")
            print(f"   Episodes Without: {podcast_stats['episodes_without_transcripts']}")
            print(f"   Completion Rate: {podcast_stats['completion_rate']:.1f}%")

        # Progress Analysis
        progress_status = self.get_progress_files_status()
        if progress_status['total_files'] > 0:
            print(f"\n📊 PROGRESS ANALYSIS:")
            print(f"   Progress Files: {progress_status['total_files']}")
            print(f"   Latest File: {progress_status['latest_file']}")
            print(f"   Processed: {progress_status['latest_processed']} transcripts")
            print(f"   Trend: {progress_status['trend'].upper()}")

        # Completion Projection
        projection = self.calculate_completion_projection()
        if 'error' not in projection:
            print(f"\n🎯 COMPLETION PROJECTION:")
            print(f"   Episodes Remaining: {projection['episodes_remaining']}")
            print(f"   Current Rate: {projection['current_rate_per_hour']}/hour")
            print(f"   Success Rate: {projection['success_rate']:.1f}%")
            print(f"   Estimated: {projection['estimated_completion_hours']} hours")
            print(f"   Complete By: {datetime.fromisoformat(projection['estimated_completion_time']).strftime('%B %d, %I:%M %p')}")
            print(f"   Days Remaining: {projection['days_remaining']}")

        # Recent Activity
        print(f"\n🕐 RECENT ACTIVITY (Last Hour)")
        if url_stats['last_hour_count'] > 0:
            print(f"   URL Attempts: {url_stats['last_hour_count']}")
            if system_status['processor_running']:
                print(f"   Processor Status: 🟢 Active")
            else:
                print(f"   Processor Status: 🔴 Stopped")
        else:
            print("   No recent activity")

        # Quick Actions
        print(f"\n🚀 QUICK ACTIONS:")
        print(f"   • Check live logs: tail -f overnight_processing.log")
        print(f"   • View transcripts: ls transcripts/ | wc -l")
        print(f"   • Check database: sqlite3 podcast_processing.db 'SELECT COUNT(*) FROM episodes;'")
        print(f"   • Monitor processor: ps aux | grep simple_overnight_processor")

        print("\n" + "="*80)

        # Save detailed report
        detailed_report = {
            'timestamp': datetime.now().isoformat(),
            'system_status': system_status,
            'transcript_stats': transcript_stats,
            'url_tracking_stats': url_stats,
            'podcast_database_stats': podcast_stats,
            'progress_status': progress_status,
            'completion_projection': projection
        }

        report_file = self.root_dir / f"morning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(detailed_report, f, indent=2, default=str)

        print(f"\n💾 Detailed report saved: {report_file}")
        return detailed_report

    def print_quick_status(self):
        """Print a very quick status overview"""
        system_status = self.get_system_status()
        transcript_stats = self.get_transcript_counts()
        url_stats = self.get_url_tracking_stats()

        print(f"\n🚀 ATLAS STATUS - {datetime.now().strftime('%I:%M %p')}")
        print(f"System: {system_status['status']} | Transcripts: {transcript_stats['total']} | Success Rate: {url_stats.get('success_rate', 0):.1f}% | Processor: {'🟢' if system_status['processor_running'] else '🔴'}")

def main():
    """Main morning status function"""
    dashboard = MorningStatusDashboard()
    dashboard.generate_morning_report()

if __name__ == "__main__":
    main()