#!/usr/bin/env python3
"""
Create a frequent processor for Atlas v2
"""

import sqlite3
import subprocess
import time
import json
import os
from datetime import datetime

def process_batch_items():
    """Process a batch of items from the queue"""
    print(f"🔄 Processing batch at {datetime.now()}")

    # Run processing inside the container
    result = subprocess.run([
        'docker', 'exec', 'atlas-v2', 'python3', '-c', '''
import asyncio
from modules.database import DatabaseManager
from modules.processor import ContentProcessor
from modules.config_manager import ConfigManager

async def process_batch():
    db = DatabaseManager()
    await db.initialize()

    # Get pending items
    items = await db.get_pending_items(limit=5)
    print(f"Processing {len(items)} items...")

    processed = 0
    for item in items:
        content_id = item["content_id"]
        try:
            await db.update_queue_status(content_id, "processing")

            processor = ContentProcessor(db, ConfigManager())
            result = await processor.process_content(content_id)

            if result["status"] == "success":
                await db.update_queue_status(content_id, "completed")
                processed += 1
                print(f"✅ Completed: {content_id}")
            else:
                await db.update_queue_status(content_id, "failed")
                print(f"❌ Failed: {content_id}")

        except Exception as e:
            print(f"❌ Error processing {content_id}: {e}")
            await db.update_queue_status(content_id, "failed")

    await db.close()
    print(f"Batch complete: {processed} processed")

asyncio.run(process_batch())
'''
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"❌ Error: {result.stderr}")

def check_queue_status():
    """Check current queue status"""
    conn = sqlite3.connect("/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db")

    cursor = conn.execute("SELECT status, COUNT(*) FROM processing_queue GROUP BY status")
    queue_status = dict(cursor.fetchall())

    cursor = conn.execute("SELECT COUNT(*) FROM processing_queue WHERE status = 'pending'")
    pending_count = cursor.fetchone()[0]

    conn.close()

    return queue_status, pending_count

def continuous_processor():
    """Run continuous processing every 5 minutes"""
    print("🚀 Starting Atlas v2 Continuous Processor")
    print("Will process 5 items every 5 minutes")
    print("Press Ctrl+C to stop")

    while True:
        try:
            queue_status, pending_count = check_queue_status()
            print(f"\n📊 Status: {queue_status} | Pending: {pending_count}")

            if pending_count > 0:
                process_batch_items()
            else:
                print("✅ No pending items - queue is empty!")

        except Exception as e:
            print(f"❌ Error in processing loop: {e}")

        # Wait 5 minutes
        print("⏰ Waiting 5 minutes...")
        time.sleep(300)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Atlas v2 Continuous Processor')
    parser.add_argument('--run', action='store_true', help='Run continuous processor')
    parser.add_argument('--once', action='store_true', help='Process one batch only')

    args = parser.parse_args()

    if args.run:
        continuous_processor()
    elif args.once:
        process_batch_items()
    else:
        print("Usage: python3 create_frequent_scheduler.py --run or --once")