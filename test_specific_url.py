#!/usr/bin/env python3
"""
Test the real processor with a specific URL that should have content
"""

import asyncio
import sys
import os
sys.path.append('atlas_v2')

from atlas_v2.modules.database import DatabaseManager
from atlas_v2.modules.real_content_processor import RealContentProcessor

async def test_specific_url():
    """Test the real processor with a specific URL"""

    print("🧪 Testing REAL Content Processor with Specific URL")
    print("=" * 60)

    # Initialize database
    db = DatabaseManager("atlas_v2/data/atlas_v2.db")
    await db.initialize()

    # Test with a URL that should have substantial content
    test_urls = [
        ("https://www.nytimes.com/2025/09/30/podcasts/the-daily.html", "NYT Daily Podcast"),
        ("https://99percentinvisible.org/episode/a-beetle-by-any-other-name/transcript/", "99% Invisible (with transcript)"),
        ("https://www.thisamericanlife.org/800/transcript", "This American Life"),
        ("https://freakonomics.com/podcast/how-to-predict-the-future/", "Freakonomics Podcast"),
    ]

    for url, description in test_urls:
        print(f"\n🧪 Testing: {description}")
        print(f"   URL: {url}")

        try:
            # Create a fake content_id for testing
            content_id = f"test-{hash(url) % 10000}"

            # Create fake content info
            content_info = {
                'content_id': content_id,
                'source_url': url,
                'source_name': description,
                'content_type': 'podcast',
                'title': description,
                'metadata': {}
            }

            # Add to processing queue temporarily
            import aiosqlite
            async with aiosqlite.connect("atlas_v2/data/atlas_v2.db") as conn:
                await conn.execute("""
                    INSERT OR REPLACE INTO processing_queue
                    (content_id, source_url, source_name, content_type, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """, (content_id, url, description, 'podcast',
                      "2025-09-30T17:00:00", "2025-09-30T17:00:00"))
                await conn.commit()

            # Test with real processor
            async with RealContentProcessor(db, None) as processor:
                result = await processor.process_content(content_id)

            print(f"📊 Result: {result['status']}")
            print(f"📝 Message: {result['message']}")

            if result['status'] == 'success':
                content = result.get('content', '')
                print(f"📄 Content length: {len(content)} characters")
                print(f"📝 Title: {result.get('title', 'No title')}")

                # Show first 300 characters of content
                preview = content[:300].replace('\n', ' ').strip()
                print(f"👀 Preview: {preview}...")

                if len(content) > 2000:
                    print("✅ SUCCESS - Found substantial content!")
                    print(f"🎯 This URL would be processed successfully!")
                    break
                else:
                    print("⚠️ Found some content but might be limited")
            else:
                print(f"❌ Failed: {result['message']}")

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")

        finally:
            # Clean up test entry
            try:
                async with aiosqlite.connect("atlas_v2/data/atlas_v2.db") as conn:
                    await conn.execute("DELETE FROM processing_queue WHERE content_id = ?", (content_id,))
                    await conn.commit()
            except:
                pass

    print(f"\n🎯 URL testing completed!")
    print("🔥 If we found substantial content above, the processor is working!")

    await db.close()

if __name__ == "__main__":
    asyncio.run(test_specific_url())