#!/usr/bin/env python3
"""
Test Enhanced Free Processor - Small batch to see validation in action
"""

import sqlite3
from enhanced_free_processor import EnhancedFreeProcessor

def test_enhanced_processor():
    """Test enhanced processor with 5 episodes"""

    print("🧪 Testing Enhanced Free Processor")
    print("=" * 50)

    processor = EnhancedFreeProcessor()

    # Get 5 pending episodes for testing
    conn = sqlite3.connect("podcast_processing.db")
    cursor = conn.execute("""
        SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.processing_status = 'pending'
        ORDER BY RANDOM()
        LIMIT 5
    """)

    episodes = cursor.fetchall()
    conn.close()

    if not episodes:
        print("❌ No pending episodes found")
        return

    print(f"📋 Testing {len(episodes)} episodes with enhanced validation...")
    print(f"🔧 Validation: 1,000+ words, strong indicators, dialogue structure")
    print()

    successful = 0
    failed = 0

    for episode in episodes:
        episode_id, title, link, podcast_id, podcast_name = episode

        print(f"\n🎙️  Podcast: {podcast_name}")
        print(f"📄 Episode: {title[:60]}...")

        try:
            if processor.process_episode(episode):
                successful += 1
                print("✅ SUCCESS - High-quality transcript found!")
            else:
                failed += 1
                print("❌ FAILED - No quality transcript found")
        except Exception as e:
            print(f"🚫 ERROR: {e}")
            failed += 1

        print("-" * 60)

    print(f"\n🏁 Test Complete!")
    print(f"📊 Results: {successful} successful, {failed} failed")
    print(f"📈 Success rate: {(successful/(successful+failed))*100:.1f}%" if (successful+failed) > 0 else "No episodes processed")

    processor.log_api_usage()

if __name__ == "__main__":
    test_enhanced_processor()