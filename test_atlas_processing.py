#!/usr/bin/env python3
"""
Test Atlas v2 Processing - Simple verification
"""

import sqlite3
import json
import asyncio
import sys
import os
from pathlib import Path

# Add Atlas v2 modules path
sys.path.append('/home/ubuntu/dev/atlas/atlas_v2')

async def test_single_item():
    """Test processing a single queue item"""
    print("🧪 Testing Atlas v2 processing...")

    # Get a pending item directly from database
    conn = sqlite3.connect("/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db")
    cursor = conn.execute("""
        SELECT content_id, source_url, source_name, metadata_json
        FROM processing_queue
        WHERE status = 'pending'
        LIMIT 1
    """)

    item = cursor.fetchone()
    if not item:
        print("❌ No pending items found in database")
        conn.close()
        return

    content_id, source_url, source_name, metadata_json = item
    conn.close()

    print(f"🎯 Testing with: {content_id}")
    print(f"📄 URL: {source_url}")
    print(f"📊 Source: {source_name}")

    try:
        # Import Atlas v2 modules
        from modules.database import DatabaseManager
        from modules.processor import ContentProcessor
        from modules.config_manager import ConfigManager

        # Initialize
        config_manager = ConfigManager()
        db_manager = DatabaseManager()
        processor = ContentProcessor(db_manager, config_manager)

        await db_manager.initialize()

        # Update status to processing
        await db_manager.update_queue_status(content_id, 'processing')
        print("📝 Status updated to 'processing'")

        # Try to process the item
        print(f"🔄 Processing {content_id}...")
        result = await processor.process_content(content_id)

        # Update status based on result
        if result['status'] == 'success':
            print(f"✅ SUCCESS: {result['message']}")
            await db_manager.update_queue_status(content_id, 'completed')
        elif result['status'] == 'retry':
            print(f"🔄 RETRY: {result['message']}")
            await db_manager.update_queue_status(content_id, 'retry')
        else:
            print(f"❌ FAILED: {result['message']}")
            await db_manager.update_queue_status(content_id, 'failed')

        await db_manager.close()
        print(f"🏁 Test complete: {result['status']}")

    except Exception as e:
        print(f"❌ ERROR during processing: {e}")
        import traceback
        traceback.print_exc()

def create_simple_monitor():
    """Create a simple monitoring script"""
    script = """#!/bin/bash
# Simple Atlas v2 Monitor - Run this to check if processing is working

echo "🔍 Atlas v2 Status Check - $(date)"
echo "=================================="

# Check if container is running
if ! docker ps | grep atlas-v2 > /dev/null; then
    echo "❌ Atlas v2 container is NOT running"
    echo "🚀 Starting Atlas v2..."
    docker start atlas-v2
    sleep 10
fi

# Check health
echo "📊 Health Status:"
curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ Health check failed"

# Check queue size
echo ""
echo "📋 Queue Status:"
sqlite3 /home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db "
SELECT
    status,
    COUNT(*) as count
FROM processing_queue
GROUP BY status
ORDER BY count DESC;"

# Check recent activity
echo ""
echo "⏰ Recent Processing Activity:"
sqlite3 /home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db "
SELECT
    content_type,
    COUNT(*) as count
FROM processed_content
WHERE created_at > datetime('now', '-1 hour')
GROUP BY content_type;"

echo ""
echo "🎯 If no items are being processed, run: python3 test_atlas_processing.py"
"""

    with open("/home/ubuntu/dev/atlas/check_atlas.sh", "w") as f:
        f.write(script)

    os.chmod("/home/ubuntu/dev/atlas/check_atlas.sh", 0o755)
    print("✅ Created monitor script: /home/ubuntu/dev/atlas/check_atlas.sh")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Atlas v2 Processing Test')
    parser.add_argument('--test', action='store_true', help='Test processing single item')
    parser.add_argument('--monitor', action='store_true', help='Create monitor script')

    args = parser.parse_args()

    if args.test:
        asyncio.run(test_single_item())
    elif args.monitor:
        create_simple_monitor()
    else:
        print("Usage: python3 test_atlas_processing.py --test or --monitor")