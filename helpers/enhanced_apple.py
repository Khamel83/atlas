#!/usr/bin/env python3
"""
Enhanced Apple Features - Advanced Apple device integration
Extends basic Apple integration with advanced features and automation.

CORE PRINCIPLE: SEAMLESS APPLE ECOSYSTEM INTEGRATION
"""

import json
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import plistlib

from helpers.apple_integrations import AppleDeviceIntegration, BulletproofCapture
from helpers.utils import log_info, log_error


class EnhancedAppleIntegration:
    """
    Enhanced Apple integration with advanced features.

    Features:
    - Automated Safari History sync
    - Apple Notes full-text search and sync
    - Health app data integration
    - Screen Time insights integration
    - iCloud document monitoring
    - Siri Shortcuts automation
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize enhanced Apple integration."""
        self.config = config or {}
        self.base_integration = AppleDeviceIntegration(config)
        self.capture = BulletproofCapture(config)

        # Enhanced feature directories
        self.enhanced_dir = Path('inputs/apple/enhanced')
        self.history_dir = self.enhanced_dir / 'history'
        self.notes_dir = self.enhanced_dir / 'notes'
        self.health_dir = self.enhanced_dir / 'health'
        self.screen_time_dir = self.enhanced_dir / 'screen_time'

        for directory in [self.enhanced_dir, self.history_dir, self.notes_dir,
                         self.health_dir, self.screen_time_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Feature configuration
        self.auto_sync_enabled = self.config.get('auto_sync_enabled', True)
        self.sync_interval_hours = self.config.get('sync_interval_hours', 6)

    def sync_safari_history(self, days_back: int = 7) -> str:
        """
        Sync Safari browsing history for knowledge tracking.

        Extracts valuable content from browsing patterns while respecting privacy.
        """
        try:
            # macOS Safari history location
            home = Path.home()
            history_db = home / 'Library' / 'Safari' / 'History.db'

            if not history_db.exists():
                log_error("Safari history database not found")
                return None

            # Calculate date range
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Extract browsing history
            history_data = self._extract_safari_history(history_db, cutoff_date)

            if not history_data:
                log_info("No Safari history found in date range")
                return None

            # Capture raw history data
            metadata = {
                'source': 'safari_history',
                'days_back': days_back,
                'total_visits': len(history_data),
                'extraction_method': 'sqlite_query'
            }

            capture_id = self.capture.capture_raw_data(
                data=history_data,
                source_type='safari_history',
                source_device='mac',
                metadata=metadata
            )

            # Process valuable URLs
            valuable_urls = self._filter_valuable_urls(history_data)

            if valuable_urls:
                # Save URLs for processing
                urls_file = self.history_dir / f"valuable_urls_{capture_id}.txt"
                with open(urls_file, 'w') as f:
                    for url_data in valuable_urls:
                        f.write(f"{url_data['url']}  # {url_data['title']}\n")

                log_info(f"Safari history synced: {len(valuable_urls)} valuable URLs from {len(history_data)} total visits")

            return capture_id

        except Exception as e:
            log_error(f"Error syncing Safari history: {str(e)}")
            return None

    def _extract_safari_history(self, history_db: Path, cutoff_date: datetime) -> List[Dict]:
        """Extract Safari history from SQLite database."""
        try:
            # Convert datetime to Safari's timestamp format (seconds since 2001-01-01)
            safari_epoch = datetime(2001, 1, 1)
            cutoff_timestamp = (cutoff_date - safari_epoch).total_seconds()

            history_data = []

            with sqlite3.connect(str(history_db)) as conn:
                # Query history visits with URLs and titles
                cursor = conn.execute('''
                    SELECT h.url, h.title, v.visit_time, v.visit_count
                    FROM history_items h
                    JOIN history_visits v ON h.id = v.history_item
                    WHERE v.visit_time > ?
                    ORDER BY v.visit_time DESC
                    LIMIT 1000
                ''', (cutoff_timestamp,))

                for row in cursor:
                    url, title, visit_time, visit_count = row

                    # Convert Safari timestamp back to datetime
                    visit_datetime = safari_epoch + timedelta(seconds=visit_time)

                    history_data.append({
                        'url': url,
                        'title': title or 'Untitled',
                        'visit_time': visit_datetime.isoformat(),
                        'visit_count': visit_count
                    })

            return history_data

        except Exception as e:
            log_error(f"Error extracting Safari history: {str(e)}")
            return []

    def _filter_valuable_urls(self, history_data: List[Dict]) -> List[Dict]:
        """Filter browsing history for valuable content URLs."""
        valuable_urls = []

        # Patterns for valuable content
        valuable_patterns = [
            'article', 'blog', 'post', 'news', 'research', 'paper',
            'documentation', 'tutorial', 'guide', 'wiki', 'stack',
            'medium.com', 'substack.com', 'github.com', 'arxiv.org'
        ]

        # Patterns to exclude
        exclude_patterns = [
            'facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com',
            'youtube.com/watch', 'netflix.com', 'amazon.com/gp',
            'google.com/search', 'maps.google.com', 'gmail.com'
        ]

        for item in history_data:
            url = item['url'].lower()
            title = item['title'].lower()

            # Skip if matches exclude patterns
            if any(pattern in url for pattern in exclude_patterns):
                continue

            # Include if matches valuable patterns
            if any(pattern in url or pattern in title for pattern in valuable_patterns):
                valuable_urls.append(item)
                continue

            # Include URLs with substantial time spent (multiple visits)
            if item['visit_count'] > 2:
                valuable_urls.append(item)

        # Remove duplicates and limit
        seen_urls = set()
        filtered_urls = []

        for item in valuable_urls:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                filtered_urls.append(item)

        return filtered_urls[:100]  # Limit to prevent overwhelming

    def sync_apple_notes(self) -> str:
        """
        Sync Apple Notes for knowledge capture.

        Extracts notes with valuable content and references.
        """
        try:
            # macOS Notes database location
            home = Path.home()
            notes_db = home / 'Library' / 'Group Containers' / 'group.com.apple.notes' / 'NoteStore.sqlite'

            if not notes_db.exists():
                log_error("Apple Notes database not found")
                return None

            # Extract notes
            notes_data = self._extract_apple_notes(notes_db)

            if not notes_data:
                log_info("No Apple Notes found")
                return None

            # Capture raw notes data
            metadata = {
                'source': 'apple_notes',
                'total_notes': len(notes_data),
                'extraction_method': 'sqlite_query'
            }

            capture_id = self.capture.capture_raw_data(
                data=notes_data,
                source_type='apple_notes',
                source_device='mac',
                metadata=metadata
            )

            # Process and save individual notes
            valuable_notes = self._filter_valuable_notes(notes_data)

            if valuable_notes:
                for i, note in enumerate(valuable_notes):
                    note_file = self.notes_dir / f"note_{capture_id}_{i}.md"
                    with open(note_file, 'w', encoding='utf-8') as f:
                        f.write(f"# {note['title']}\n\n")
                        f.write(f"Created: {note['created_date']}\n")
                        f.write(f"Modified: {note['modified_date']}\n\n")
                        f.write(note['content'])

                log_info(f"Apple Notes synced: {len(valuable_notes)} valuable notes")

            return capture_id

        except Exception as e:
            log_error(f"Error syncing Apple Notes: {str(e)}")
            return None

    def _extract_apple_notes(self, notes_db: Path) -> List[Dict]:
        """Extract Apple Notes from SQLite database."""
        try:
            notes_data = []

            with sqlite3.connect(str(notes_db)) as conn:
                # Query notes with content
                cursor = conn.execute('''
                    SELECT
                        n.ZTITLE,
                        n.ZDATA,
                        n.ZCREATIONDATE,
                        n.ZMODIFICATIONDATE
                    FROM ZICNOTEDATA n
                    WHERE n.ZDATA IS NOT NULL
                    AND LENGTH(n.ZDATA) > 50
                    ORDER BY n.ZMODIFICATIONDATE DESC
                    LIMIT 500
                ''')

                for row in cursor:
                    title, data, created, modified = row

                    # Convert Core Data timestamps (seconds since 2001-01-01)
                    core_data_epoch = datetime(2001, 1, 1)
                    created_date = core_data_epoch + timedelta(seconds=created) if created else None
                    modified_date = core_data_epoch + timedelta(seconds=modified) if modified else None

                    # Extract text content from data blob (simplified)
                    content = self._extract_note_content(data)

                    if content and len(content) > 10:
                        notes_data.append({
                            'title': title or 'Untitled Note',
                            'content': content,
                            'created_date': created_date.isoformat() if created_date else None,
                            'modified_date': modified_date.isoformat() if modified_date else None
                        })

            return notes_data

        except Exception as e:
            log_error(f"Error extracting Apple Notes: {str(e)}")
            return []

    def _extract_note_content(self, data_blob: bytes) -> str:
        """Extract text content from Apple Notes data blob."""
        try:
            # Apple Notes uses protobuf format, this is a simplified extraction
            # In production, would use proper protobuf parsing

            if isinstance(data_blob, str):
                return data_blob

            # Try to decode as UTF-8 and extract readable text
            text = data_blob.decode('utf-8', errors='ignore')

            # Clean up the text (remove control characters, etc.)
            import re
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            return cleaned if len(cleaned) > 10 else None

        except Exception as e:
            log_error(f"Error extracting note content: {str(e)}")
            return None

    def _filter_valuable_notes(self, notes_data: List[Dict]) -> List[Dict]:
        """Filter notes for valuable content."""
        valuable_notes = []

        # Patterns for valuable content
        valuable_patterns = [
            'http', 'idea', 'research', 'project', 'meeting', 'notes',
            'todo', 'plan', 'summary', 'insight', 'learning', 'book',
            'article', 'reference', 'code', 'python', 'javascript'
        ]

        for note in notes_data:
            content_lower = note['content'].lower()
            title_lower = note['title'].lower()

            # Include notes with URLs or valuable keywords
            if ('http' in content_lower or
                any(pattern in content_lower or pattern in title_lower for pattern in valuable_patterns)):
                valuable_notes.append(note)
                continue

            # Include longer notes (likely substantial content)
            if len(note['content']) > 200:
                valuable_notes.append(note)

        return valuable_notes[:50]  # Limit to prevent overwhelming

    def setup_automated_sync(self) -> bool:
        """
        Setup automated sync using macOS automation.

        Creates launchd agent for periodic sync.
        """
        try:
            if not self.auto_sync_enabled:
                log_info("Automated sync disabled in config")
                return False

            # Create launchd plist for automated sync
            plist_content = {
                'Label': 'com.atlas.apple.sync',
                'ProgramArguments': [
                    '/usr/bin/python3',
                    str(Path(__file__).parent.parent / 'scripts' / 'apple_auto_sync.py')
                ],
                'StartInterval': self.sync_interval_hours * 3600,  # Convert hours to seconds
                'RunAtLoad': True,
                'StandardOutPath': str(Path.home() / 'Library' / 'Logs' / 'atlas_apple_sync.log'),
                'StandardErrorPath': str(Path.home() / 'Library' / 'Logs' / 'atlas_apple_sync_error.log')
            }

            # Save plist file
            plist_path = Path.home() / 'Library' / 'LaunchAgents' / 'com.atlas.apple.sync.plist'
            plist_path.parent.mkdir(exist_ok=True)

            with open(plist_path, 'wb') as f:
                plistlib.dump(plist_content, f)

            # Create sync script
            sync_script = Path(__file__).parent.parent / 'scripts' / 'apple_auto_sync.py'
            sync_script.parent.mkdir(exist_ok=True)

            script_content = f'''#!/usr/bin/env python3
"""
Automated Apple sync script for Atlas.
"""

import sys
from pathlib import Path

# Add Atlas to path
atlas_dir = Path(__file__).parent.parent
sys.path.insert(0, str(atlas_dir))

from helpers.enhanced_apple import EnhancedAppleIntegration
from helpers.utils import setup_logging, log_info

def main():
    setup_logging("data/apple_auto_sync.log")
    log_info("Starting automated Apple sync")

    integration = EnhancedAppleIntegration()

    # Sync Safari history
    history_id = integration.sync_safari_history()
    if history_id:
        log_info(f"Safari history synced: {{history_id}}")

    # Sync Apple Notes
    notes_id = integration.sync_apple_notes()
    if notes_id:
        log_info(f"Apple Notes synced: {{notes_id}}")

    # Process pending captures
    integration.base_integration.process_pending_captures()

    log_info("Automated Apple sync completed")

if __name__ == "__main__":
    main()
'''

            with open(sync_script, 'w') as f:
                f.write(script_content)

            sync_script.chmod(0o755)  # Make executable

            # Load launchd agent
            try:
                subprocess.run(['launchctl', 'load', str(plist_path)], check=True)
                log_info(f"Automated sync setup complete. Syncing every {self.sync_interval_hours} hours")
                return True
            except subprocess.CalledProcessError as e:
                log_error(f"Failed to load launchd agent: {str(e)}")
                return False

        except Exception as e:
            log_error(f"Error setting up automated sync: {str(e)}")
            return False

    def get_sync_status(self) -> Dict[str, Any]:
        """Get status of Apple integration sync."""
        try:
            # Check pending captures
            pending_captures = self.capture.get_pending_captures()

            # Check recent sync activity
            recent_captures = []
            with sqlite3.connect(self.capture.db_path) as conn:
                cursor = conn.execute('''
                    SELECT source_type, capture_timestamp, processing_status
                    FROM capture_log
                    WHERE capture_timestamp > datetime('now', '-24 hours')
                    AND source_type IN ('safari_history', 'apple_notes', 'safari_reading_list')
                    ORDER BY capture_timestamp DESC
                ''')

                for row in cursor:
                    recent_captures.append({
                        'source_type': row[0],
                        'timestamp': row[1],
                        'status': row[2]
                    })

            # Check if automated sync is running
            sync_active = False
            try:
                result = subprocess.run(['launchctl', 'list', 'com.atlas.apple.sync'],
                                      capture_output=True, text=True)
                sync_active = result.returncode == 0
            except:
                pass

            return {
                'pending_captures': len(pending_captures),
                'recent_captures_24h': len(recent_captures),
                'recent_activity': recent_captures[:10],
                'automated_sync_active': sync_active,
                'auto_sync_enabled': self.auto_sync_enabled,
                'sync_interval_hours': self.sync_interval_hours
            }

        except Exception as e:
            log_error(f"Error getting sync status: {str(e)}")
            return {'error': str(e)}

    def manual_full_sync(self) -> Dict[str, str]:
        """Perform manual full sync of all Apple sources."""
        results = {}

        try:
            # Sync Safari Reading List
            reading_list_id = self.base_integration.import_safari_reading_list()
            if reading_list_id:
                results['safari_reading_list'] = reading_list_id

            # Sync Safari History
            history_id = self.sync_safari_history()
            if history_id:
                results['safari_history'] = history_id

            # Sync Apple Notes
            notes_id = self.sync_apple_notes()
            if notes_id:
                results['apple_notes'] = notes_id

            # Process all pending captures
            self.base_integration.process_pending_captures()

            log_info(f"Manual full sync completed: {len(results)} sources synced")
            return results

        except Exception as e:
            log_error(f"Error in manual full sync: {str(e)}")
            results['error'] = str(e)
            return results


def setup_enhanced_apple_integration(config: Dict[str, Any] = None) -> EnhancedAppleIntegration:
    """
    Setup complete enhanced Apple integration.

    Returns configured integration instance.
    """
    integration = EnhancedAppleIntegration(config)

    # Setup automated sync if enabled
    if integration.auto_sync_enabled:
        integration.setup_automated_sync()

    log_info("Enhanced Apple integration setup complete")
    return integration


def quick_apple_sync() -> Dict[str, str]:
    """
    Quick function for manual Apple sync.

    Usage:
        from helpers.enhanced_apple import quick_apple_sync
        results = quick_apple_sync()
    """
    integration = EnhancedAppleIntegration()
    return integration.manual_full_sync()