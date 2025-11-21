#!/usr/bin/env python3
"""
Always-On Atlas Queue Processor
Keeps processing the Atlas queue 24/7
"""

import sqlite3
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json

class AlwaysOnProcessor:
    """Keeps processing Atlas queue continuously"""

    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def get_next_item(self):
        """Get next unprocessed item from queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT id, source_url, title, content, source_type
            FROM atlas_queue
            WHERE processing_status = 'pending' OR processing_status IS NULL
            ORDER BY added_date ASC
            LIMIT 1
        """)

        item = cursor.fetchone()
        conn.close()
        return item

    def mark_processed(self, item_id, success=True, transcript_text=""):
        """Mark item as processed"""
        conn = sqlite3.connect(self.db_path)
        status = 'completed' if success else 'failed'

        conn.execute("""
            UPDATE atlas_queue
            SET processing_status = ?,
                processed_date = CURRENT_TIMESTAMP,
                transcript_text = ?
            WHERE id = ?
        """, (status, transcript_text, item_id))

        conn.commit()
        conn.close()

    def process_item(self, item):
        """Process a single queue item"""
        item_id, source_url, title, content, source_type = item

        print(f"🔄 Processing: {title[:60]}... ({source_type})")

        try:
            # If it's a URL, try to fetch better content
            if source_url and source_url.startswith('http'):
                print(f"   📥 Fetching: {source_url[:60]}...")

                try:
                    response = self.session.get(source_url, timeout=15)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Remove unwanted elements
                    for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                        element.decompose()

                    text = soup.get_text()
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    clean_content = '\n'.join(lines)

                    if len(clean_content) > len(content):
                        print(f"   ✅ Enhanced content: {len(clean_content)} chars")
                        self.mark_processed(item_id, True, clean_content)
                        return True

                except Exception as e:
                    print(f"   ⚠️  Fetch failed: {str(e)[:50]}")

            # Use existing content or URL info
            if content:
                print(f"   ✅ Using existing content: {len(content)} chars")
                self.mark_processed(item_id, True, content)
                return True
            else:
                print(f"   ❌ No content available")
                self.mark_processed(item_id, False)
                return False

        except Exception as e:
            print(f"   ❌ Processing error: {e}")
            self.mark_processed(item_id, False)
            return False

    def run_forever(self):
        """Run continuously processing items"""
        print("🚀 ALWAYS-ON ATLAS PROCESSOR")
        print("=" * 50)
        print("🎯 Will keep processing 24/7")
        print("🔄 Runs continuously when items are available")
        print("💤 Sleeps when queue is empty")

        while True:
            try:
                # Get next item to process
                item = self.get_next_item()

                if item:
                    # Process the item
                    self.process_item(item)
                    print("   ⏳ Waiting 2 seconds before next item...")
                    time.sleep(2)
                else:
                    # No items to process, check queue status
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.execute("SELECT COUNT(*) FROM atlas_queue WHERE processing_status = 'pending' OR processing_status IS NULL")
                    pending = cursor.fetchone()[0]
                    conn.close()

                    if pending == 0:
                        print("😴 Queue empty - sleeping 30 seconds...")
                        time.sleep(30)
                    else:
                        print("   ⏳ Brief pause...")
                        time.sleep(5)

            except KeyboardInterrupt:
                print("\n👋 Processor stopped by user")
                break
            except Exception as e:
                print(f"🚫 Error in main loop: {e}")
                time.sleep(10)

if __name__ == "__main__":
    processor = AlwaysOnProcessor()
    processor.run_forever()