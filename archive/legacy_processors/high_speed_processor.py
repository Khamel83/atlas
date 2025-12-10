#!/usr/bin/env python3
"""
High-Speed Atlas v2 Processor
Processes items rapidly instead of 5 items every 5 minutes
"""

import sqlite3
import subprocess
import time
import json
import os
from datetime import datetime

def process_batch_items(batch_size=50):
    """Process a large batch of items quickly"""
    print(f"🚀 Processing {batch_size} items at {datetime.now()}")

    # Run processing inside the container
    result = subprocess.run([
        'docker', 'exec', 'atlas-v2', 'python3', '-c', f'''
import asyncio
from modules.database import DatabaseManager
from modules.processor import ContentProcessor
from modules.config_manager import ConfigManager

async def process_batch():
    db = DatabaseManager()
    await db.initialize()

    # Get pending items
    items = await db.get_pending_items(limit={batch_size})
    print(f"Processing {{len(items)}} items...")

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
                print(f"✅ Completed: {{content_id}}")
            else:
                await db.update_queue_status(content_id, "failed")
                print(f"❌ Failed: {{content_id}}")

        except Exception as e:
            print(f"❌ Error processing {{content_id}}: {{e}}")
            await db.update_queue_status(content_id, "failed")

    await db.close()
    print(f"Batch complete: {{processed}} processed")

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

def high_speed_processor():
    """Run high-speed processing continuously"""
    print("🚀 Starting Atlas v2 High-Speed Processor")
    print("Will process 50 items every 30 seconds")
    print("Press Ctrl+C to stop")

    while True:
        try:
            queue_status, pending_count = check_queue_status()
            print(f"\n📊 Status: {queue_status} | Pending: {pending_count}")

            if pending_count > 0:
                process_batch_items(50)  # Process 50 items at once
            else:
                print("✅ No pending items - queue is empty!")
                break

        except Exception as e:
            print(f"❌ Error in processing loop: {e}")

        # Wait only 30 seconds between batches
        print("⏰ Waiting 30 seconds...")
        time.sleep(30)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Atlas v2 High-Speed Processor')
    parser.add_argument('--run', action='store_true', help='Run continuous high-speed processor')
    parser.add_argument('--once', action='store_true', help='Process one batch only')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size per run')

    args = parser.parse_args()

    if args.run:
        high_speed_processor()
    elif args.once:
        process_batch_items(args.batch_size)
    else:
        print("Usage: python3 high_speed_processor.py --run or --once [--batch-size N]")