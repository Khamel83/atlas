#!/usr/bin/env python3
"""
Continuous Atlas Runner - Simple persistent processing
"""

import sqlite3
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import signal
import sys

class ContinuousRunner:
    """Simple continuous processor that restarts itself"""

    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.running = True

        # Handle shutdown gracefully
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        print(f"\n👋 Received shutdown signal, stopping gracefully...")
        self.running = False

    def get_queue_stats(self):
        """Get current queue statistics"""
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute("SELECT COUNT(*) FROM atlas_ingestion_queue WHERE processing_status = 'pending'")
        pending = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM atlas_ingestion_queue WHERE processing_status = 'completed'")
        completed = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM episodes WHERE processing_status = 'completed'")
        episodes_done = cursor.fetchone()[0]

        conn.close()
        return pending, completed, episodes_done

    def process_next_batch(self, batch_size=10):
        """Process next batch of items"""
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute("""
            SELECT id, source_url, title, raw_content
            FROM atlas_ingestion_queue
            WHERE processing_status = 'pending'
            ORDER BY ingestion_date ASC
            LIMIT ?
        """, (batch_size,))

        items = cursor.fetchall()

        if not items:
            conn.close()
            return 0

        processed = 0
        for item_id, source_url, title, raw_content in items:
            print(f"🔄 Processing: {title[:50]}...")

            try:
                # Try to enhance content if we have a URL
                enhanced_content = raw_content

                if source_url and source_url.startswith('http'):
                    try:
                        response = self.session.get(source_url, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                                element.decompose()

                            text = soup.get_text()
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            new_content = '\n'.join(lines)

                            if len(new_content) > len(enhanced_content):
                                enhanced_content = new_content
                                print(f"   ✅ Enhanced: {len(enhanced_content)} chars")
                    except:
                        pass

                # Mark as completed
                conn.execute("""
                    UPDATE atlas_ingestion_queue
                    SET processing_status = 'completed',
                        processed_date = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (item_id,))

                processed += 1
                print(f"   ✅ Completed")

            except Exception as e:
                print(f"   ❌ Error: {e}")
                # Mark as failed but don't stop processing
                conn.execute("""
                    UPDATE atlas_ingestion_queue
                    SET processing_status = 'failed'
                    WHERE id = ?
                """, (item_id,))

        conn.commit()
        conn.close()
        return processed

    def run_forever(self):
        """Run continuous processing loop"""
        print("🚀 CONTINUOUS ATLAS RUNNER")
        print("=" * 50)
        print("🔄 Will run continuously until stopped")
        print("💤 Smart sleeping when queue is empty")
        print("📊 Auto-reports progress every 30 seconds")
        print("\n💡 Use Ctrl+C to stop gracefully")

        cycle_count = 0
        last_report = time.time()

        while self.running:
            try:
                cycle_count += 1

                # Get stats
                pending, completed, episodes_done = self.get_queue_stats()

                # Report status every 30 seconds or every 10 cycles
                current_time = time.time()
                if current_time - last_report > 30 or cycle_count % 10 == 0:
                    print(f"\n📊 STATUS UPDATE (Cycle {cycle_count}):")
                    print(f"   📥 Atlas Queue: {pending:,} pending, {completed:,} completed")
                    print(f"   🎙️  Episodes: {episodes_done:,} with transcripts")
                    print(f"   ⏰ {datetime.now().strftime('%H:%M:%S')}")
                    last_report = current_time

                # Process items
                if pending > 0:
                    processed = self.process_next_batch(min(20, pending))  # Process up to 20 items
                    print(f"   🔄 Processed {processed} items this cycle")
                    time.sleep(3)  # Brief pause between batches
                else:
                    # No items to process - longer sleep
                    print(f"   😴 Queue empty - sleeping 60 seconds...")
                    time.sleep(60)

            except KeyboardInterrupt:
                print(f"\n👋 Stopping by user request...")
                break
            except Exception as e:
                print(f"🚫 Error in processing loop: {e}")
                time.sleep(10)  # Wait before retrying

        print(f"\n🏁 PROCESSING COMPLETE")
        print(f"📊 Final stats after {cycle_count} cycles:")
        pending, completed, episodes_done = self.get_queue_stats()
        print(f"   📥 Atlas Queue: {pending:,} pending, {completed:,} completed")
        print(f"   🎙️  Episodes: {episodes_done:,} with transcripts")

if __name__ == "__main__":
    runner = ContinuousRunner()
    runner.run_forever()