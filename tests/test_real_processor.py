#!/usr/bin/env python3
"""
Test the REAL content processor to make sure it actually extracts content
"""

import asyncio
import sys
import os
sys.path.append('atlas_v2')

from atlas_v2.modules.database import DatabaseManager
from atlas_v2.modules.real_content_processor import RealContentProcessor

async def test_real_processor():
    """Test the real processor with actual pending items"""

    print("🧪 Testing REAL Content Processor")
    print("=" * 50)

    # Initialize database
    db = DatabaseManager("atlas_v2/data/atlas_v2.db")
    await db.initialize()

    # Get some pending items to test with
    print("📋 Getting sample pending items...")

    import aiosqlite
    async with aiosqlite.connect("atlas_v2/data/atlas_v2.db") as conn:
        cursor = await conn.execute("""
            SELECT content_id, source_url, content_type, source_name
            FROM processing_queue
            WHERE status = 'pending'
            LIMIT 3
        """)

        pending_items = await cursor.fetchall()

    if not pending_items:
        print("❌ No pending items found to test with")
        return

    print(f"✅ Found {len(pending_items)} pending items to test")

    # Test each item
    for i, (content_id, source_url, content_type, source_name) in enumerate(pending_items, 1):
        print(f"\n🧪 Test {i}: Processing {content_id}")
        print(f"   URL: {source_url}")
        print(f"   Type: {content_type}")
        print(f"   Source: {source_name}")

        try:
            # Get content details directly from processing queue
            import aiosqlite
            async with aiosqlite.connect("atlas_v2/data/atlas_v2.db") as conn:
                cursor = await conn.execute("""
                    SELECT content_id, source_url, source_name, content_type
                    FROM processing_queue
                    WHERE content_id = ?
                """, (content_id,))

                row = await cursor.fetchone()

            if not row:
                print(f"❌ Could not find content in queue: {content_id}")
                continue

            content_info = {
                'content_id': row[0],
                'source_url': row[1],
                'source_name': row[2],
                'content_type': row[3],
                'title': source_name,  # Use source_name as title for now
                'metadata': {}
            }

            # Test with real processor
            async with RealContentProcessor(db, None) as processor:
                result = await processor.process_content(content_id)

            print(f"📊 Result: {result['status']}")
            print(f"📝 Message: {result['message']}")

            if result['status'] == 'success':
                content = result.get('content', '')
                print(f"📄 Content length: {len(content)} characters")
                print(f"📝 Title: {result.get('title', 'No title')}")

                # Show first 200 characters of content
                preview = content[:200].replace('\n', ' ').strip()
                print(f"👀 Preview: {preview}...")

                if len(content) > 1000:
                    print("✅ SUCCESS - Found substantial content!")
                else:
                    print("⚠️ Found some content but might be limited")
            else:
                print(f"❌ Failed: {result['message']}")

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")

    print(f"\n🎯 Test completed!")
    print("🔥 If we see substantial content above, the processor is working!")

    await db.close()

if __name__ == "__main__":
    asyncio.run(test_real_processor())