#!/usr/bin/env python3
"""
Retrofit Failed Content Through Google Search

This script finds previously failed Atlas ingestions and attempts to
recover them using Google Search fallback.
"""

import os
import sys
import sqlite3
import asyncio
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from urllib.parse import urlparse, unquote
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.google_search_queue import GoogleSearchQueue, QueuePriority
from helpers.google_search_fallback import search_with_google_fallback
from helpers.config import load_config
from helpers.database_config import get_database_path_str
from ingest.link_dispatcher import process_url_file
import uuid
import tempfile

class ContentRetrofitter:
    """Retrofits failed Atlas content using Google Search"""

    def __init__(self):
        self.config = load_config()
        self.queue = GoogleSearchQueue()
        self.db_path = get_database_path_str()
        self.stats = {
            "total_failed": 0,
            "searches_queued": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "already_exists": 0
        }

    def get_failed_content(self) -> List[Dict]:
        """Query database for failed/incomplete content entries"""
        failed_content = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Look for content with processing failures
                cursor = conn.execute("""
                    SELECT url, title, content, created_at, updated_at
                    FROM content
                    WHERE (content LIKE '%failed%' OR
                           content LIKE '%error%' OR
                           content LIKE '%could not%' OR
                           content LIKE '%timeout%' OR
                           content IS NULL OR
                           content = '' OR
                           LENGTH(content) < 100)
                    AND url IS NOT NULL
                    AND url != ''
                    ORDER BY created_at DESC
                    LIMIT 1000
                """)

                for row in cursor.fetchall():
                    failed_content.append(dict(row))

        except Exception as e:
            print(f"Error querying database: {e}")

        return failed_content

    def extract_search_query_from_url(self, url: str, title: str = None) -> str:
        """Extract meaningful search terms from URL and title"""
        # Start with title if available
        if title and title.strip() and not any(word in title.lower() for word in ['processing', 'failed', 'error']):
            # Clean up the title
            query = re.sub(r'[^\w\s-]', ' ', title)
            query = re.sub(r'\s+', ' ', query).strip()
            if len(query) > 10:  # Good title
                return query[:100]  # Limit length

        # Extract from URL
        parsed = urlparse(url)

        # Try path segments
        path_parts = [part for part in parsed.path.split('/') if part and not part.isdigit()]
        if path_parts:
            # Use the most specific part (usually the last meaningful segment)
            search_part = unquote(path_parts[-1])
            # Convert URL-style to readable
            search_part = search_part.replace('-', ' ').replace('_', ' ')
            search_part = re.sub(r'[^\w\s]', ' ', search_part)
            search_part = re.sub(r'\s+', ' ', search_part).strip()

            if len(search_part) > 5:  # Meaningful content
                return search_part[:100]

        # Fallback: use domain + generic article term
        domain = parsed.netloc.replace('www.', '').replace('.com', '').replace('.org', '').replace('.net', '')
        return f"article {domain}"

    async def process_failed_content(self, failed_items: List[Dict]) -> Dict:
        """Process failed content items through Google Search"""
        print(f"🔍 Processing {len(failed_items)} failed content items...")

        for i, item in enumerate(failed_items):
            try:
                url = item['url']
                title = item.get('title', '')

                print(f"[{i+1}/{len(failed_items)}] Processing: {url}")

                # Extract search query
                search_query = self.extract_search_query_from_url(url, title)
                print(f"  🔎 Search query: '{search_query}'")

                # Try Google Search to find alternative URL
                alternative_url = await search_with_google_fallback(search_query, priority=2)

                if alternative_url and alternative_url != url:
                    print(f"  ✅ Found alternative: {alternative_url}")

                    # Try to process the alternative URL
                    success = await self.process_alternative_url(url, alternative_url)

                    if success:
                        self.stats["successful_recoveries"] += 1
                        print(f"  🎉 Successfully recovered content!")
                    else:
                        self.stats["failed_recoveries"] += 1
                        print(f"  ❌ Failed to process alternative URL")
                else:
                    print(f"  ❌ No alternative URL found")
                    self.stats["failed_recoveries"] += 1

                # Small delay to be respectful
                if i % 10 == 9:  # Every 10 items
                    print(f"  💤 Brief pause... ({i+1}/{len(failed_items)} completed)")
                    await asyncio.sleep(2)

            except Exception as e:
                print(f"  ❌ Error processing {item.get('url', 'unknown')}: {e}")
                self.stats["failed_recoveries"] += 1

        return self.stats

    async def process_alternative_url(self, original_url: str, alternative_url: str) -> bool:
        """Process the alternative URL through Atlas ingestion"""
        try:
            # Create temporary file with the alternative URL
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(alternative_url)
                temp_file = f.name

            # Process through Atlas
            from ingest.link_dispatcher import process_url_file
            results = process_url_file(temp_file, self.config)

            # Clean up
            os.unlink(temp_file)

            # Check if processing was successful
            if results.get("successful") and len(results["successful"]) > 0:
                # Update original record to mark as recovered
                self.mark_content_recovered(original_url, alternative_url)
                return True
            elif results.get("duplicate") and len(results["duplicate"]) > 0:
                # Content already exists, still a successful recovery
                self.stats["already_exists"] += 1
                self.mark_content_recovered(original_url, alternative_url)
                return True
            else:
                return False

        except Exception as e:
            print(f"    Error processing alternative URL: {e}")
            return False

    def mark_content_recovered(self, original_url: str, alternative_url: str):
        """Mark content as recovered in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE content
                    SET content = content || '\n\n[RECOVERED via Google Search: ' || ? || ']',
                        updated_at = datetime('now')
                    WHERE url = ?
                """, (alternative_url, original_url))

        except Exception as e:
            print(f"    Error marking content as recovered: {e}")

    def generate_recovery_report(self) -> str:
        """Generate a recovery statistics report"""
        report = f"""
🔄 CONTENT RECOVERY REPORT
========================

📊 Statistics:
- Total failed content processed: {self.stats['total_failed']}
- Successful recoveries: {self.stats['successful_recoveries']}
- Failed recovery attempts: {self.stats['failed_recoveries']}
- Content already existed: {self.stats['already_exists']}
- Google searches queued: {self.stats['searches_queued']}

📈 Recovery Rate: {(self.stats['successful_recoveries'] / max(1, self.stats['total_failed']) * 100):.1f}%

🎯 Impact:
- {self.stats['successful_recoveries']} previously lost articles recovered
- {self.stats['already_exists']} duplicates detected and handled
- Total content availability improved by {self.stats['successful_recoveries'] + self.stats['already_exists']} items

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return report

async def main():
    """Main retrofit process"""
    print("🚀 Starting Atlas Content Retrofit Process")
    print("=" * 50)

    retrofitter = ContentRetrofitter()

    # Get failed content
    print("📋 Querying database for failed content...")
    failed_content = retrofitter.get_failed_content()
    retrofitter.stats["total_failed"] = len(failed_content)

    if not failed_content:
        print("✅ No failed content found to retrofit!")
        return

    print(f"📋 Found {len(failed_content)} failed content items")

    # Process failed content
    stats = await retrofitter.process_failed_content(failed_content)

    # Generate report
    report = retrofitter.generate_recovery_report()
    print(report)

    # Save report to file
    report_file = f"logs/content_recovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    os.makedirs('logs', exist_ok=True)
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"📝 Report saved to: {report_file}")
    print("🎉 Content retrofit process completed!")

if __name__ == "__main__":
    asyncio.run(main())