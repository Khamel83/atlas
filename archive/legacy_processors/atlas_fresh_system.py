#!/usr/bin/env python3
"""
Fresh Atlas System - Complete reset with new database
"""

import sqlite3
import os
from atlas_universal_bookmarker import AtlasUniversalBookmarker
from pathlib import Path

def create_fresh_atlas():
    """Create a completely fresh Atlas system"""
    print("🚀 CREATING FRESH ATLAS SYSTEM")
    print("=" * 50)

    # Create fresh database name
    fresh_db = "atlas_bookmarks_fresh.db"

    # Remove old database if exists
    if os.path.exists(fresh_db):
        os.remove(fresh_db)
        print("🗑️  Removed old fresh database")

    # Create new bookmarker with fresh database
    os.environ['ATLAS_DB_PATH'] = fresh_db

    class FreshAtlasBookmarker(AtlasUniversalBookmarker):
        def __init__(self):
            self.db_path = os.getenv('ATLAS_DB_PATH', 'atlas_bookmarks_fresh.db')
            self.setup_database()

    bookmarker = FreshAtlasBookmarker()

    # Test basic functionality
    print("🧪 Testing fresh system...")

    # Test URL bookmarking
    result = bookmarker.bookmark_url(
        "https://example.com/test",
        "Test URL for Fresh Atlas",
        "test,demo,fresh_system"
    )

    if result:
        print(f"✅ Successfully bookmarked test URL! ID: {result}")
    else:
        print("❌ Failed to bookmark test URL")

    # Test text bookmarking
    text_result = bookmarker.bookmark_text(
        "This is a test transcript for Atlas bookmarking system. It contains multiple sentences and should be properly indexed and searchable.",
        "Test Transcript",
        "test,transcript,demo"
    )

    if text_result:
        print(f"✅ Successfully bookmarked test text! ID: {text_result}")

    # Show stats
    stats = bookmarker.get_stats()
    print(f"\n📊 Fresh Atlas Status:")
    print(f"   Total Bookmarks: {stats['total_bookmarks']}")
    print(f"   Database: {fresh_db}")

    # Test search
    print(f"\n🔍 Testing search...")
    results = bookmarker.search_bookmarks("test")
    print(f"   Found {len(results)} results for 'test'")

    for result in results:
        print(f"   - {result['title']} ({result['content_type']})")

    print(f"\n🎉 FRESH ATLAS SYSTEM READY!")
    print(f"📚 Use database: {fresh_db}")
    print(f"🚀 Ready for your data sources!")

    return fresh_db

if __name__ == "__main__":
    fresh_db = create_fresh_atlas()

    print(f"\n📋 NEXT STEPS:")
    print(f"1. ATLAS_DB_PATH={fresh_db} python3 atlas_interface.py")
    print(f"2. Use the interface to import all your data")
    print(f"3. Enjoy your fresh Atlas system!")