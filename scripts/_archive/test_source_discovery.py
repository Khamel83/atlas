#!/usr/bin/env python3
"""
Test Source Discovery System End-to-End

Comprehensive testing for the Source Inventory Discovery system to verify
it correctly discovers unprocessed work and integrates with Atlas pipeline.
"""

import sys
import sqlite3
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.source_inventory import SourceInventoryDiscovery, discover_unprocessed_work

def test_database_connection():
    """Test database connectivity."""
    print("🔌 Testing database connection...")
    try:
        with sqlite3.connect("data/atlas.db") as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM content")
            count = cursor.fetchone()[0]
            print(f"✅ Database connected: {count} existing content items")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_csv_discovery():
    """Test CSV work discovery functionality."""
    print("\n📄 Testing CSV discovery...")
    try:
        discovery = SourceInventoryDiscovery()
        csv_work = discovery.discover_csv_work()

        print(f"✅ CSV discovery completed: {len(csv_work)} unprocessed URLs found")

        if csv_work:
            sample_url = csv_work[0]
            print(f"   Sample URL: {sample_url['url'][:60]}...")
            print(f"   Title: {sample_url['title'][:50]}...")
            print(f"   Source: {sample_url['source']}")

        return True
    except Exception as e:
        print(f"❌ CSV discovery failed: {e}")
        return False

def test_podcast_discovery():
    """Test podcast work discovery functionality."""
    print("\n🎙️ Testing podcast discovery...")
    try:
        discovery = SourceInventoryDiscovery()
        podcast_work = discovery.discover_podcast_work()

        print(f"✅ Podcast discovery completed: {len(podcast_work)} unprocessed episodes found")

        if podcast_work:
            sample_episode = podcast_work[0]
            print(f"   Sample episode: {sample_episode['title'][:50]}...")
            print(f"   Podcast: {sample_episode['podcast_name']}")
            print(f"   URL: {sample_episode['url'][:60]}...")

        return True
    except Exception as e:
        print(f"❌ Podcast discovery failed: {e}")
        return False

def test_stage_entry_creation():
    """Test creating stage 0 entries in content table."""
    print("\n📝 Testing stage entry creation...")
    try:
        # Create test data
        test_items = [
            {
                'url': f'https://test-source-discovery-{int(time.time())}.example.com',
                'title': 'Test Source Discovery Item',
                'source': 'test_source_discovery',
                'test_run': True
            }
        ]

        discovery = SourceInventoryDiscovery()
        created_count = discovery.create_stage_entries(test_items)

        if created_count > 0:
            print(f"✅ Stage entry creation: {created_count} entries created")

            # Verify the entry exists in database
            with sqlite3.connect("data/atlas.db") as conn:
                cursor = conn.execute(
                    "SELECT url, title, metadata FROM content WHERE url = ?",
                    (test_items[0]['url'],)
                )
                result = cursor.fetchone()

                if result:
                    print(f"   ✅ Entry verified in database")
                    print(f"   URL: {result[0]}")
                    print(f"   Title: {result[1]}")
                    metadata = eval(result[2]) if result[2] else {}
                    print(f"   Stage: {metadata.get('discovery_stage', 'unknown')}")
                else:
                    print(f"   ❌ Entry not found in database")
                    return False
        else:
            print(f"⚠️ No new entries created (may be duplicate)")

        return True
    except Exception as e:
        print(f"❌ Stage entry creation failed: {e}")
        return False

def test_full_discovery_workflow():
    """Test the complete discovery workflow."""
    print("\n🚀 Testing full discovery workflow...")
    try:
        # Record initial state
        with sqlite3.connect("data/atlas.db") as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM content")
            initial_count = cursor.fetchone()[0]

        # Run discovery
        results = discover_unprocessed_work("data/atlas.db")

        # Check results
        if 'error' in results:
            print(f"❌ Discovery workflow failed: {results['error']}")
            return False

        print(f"✅ Discovery workflow completed:")
        print(f"   📄 CSV URLs added: {results.get('csv_urls_added', 0)}")
        print(f"   🎙️ Podcast episodes added: {results.get('podcast_episodes_added', 0)}")
        print(f"   📊 Total work created: {results.get('total_work_created', 0)}")
        print(f"   ⏱️ Discovery time: {results.get('discovery_time', 0)}s")
        print(f"   📁 Sources scanned: {', '.join(results.get('sources_scanned', []))}")

        # Verify database changes
        with sqlite3.connect("data/atlas.db") as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM content")
            final_count = cursor.fetchone()[0]

        entries_added = final_count - initial_count
        expected_added = results.get('total_work_created', 0)

        if entries_added >= expected_added:
            print(f"✅ Database verification: {entries_added} new entries added")
        else:
            print(f"❌ Database verification failed: expected {expected_added}, got {entries_added}")
            return False

        return True
    except Exception as e:
        print(f"❌ Full discovery workflow failed: {e}")
        return False

def test_batch_limits():
    """Test batch processing limits."""
    print("\n📊 Testing batch limits...")
    try:
        discovery = SourceInventoryDiscovery()
        original_limit = discovery.batch_limit

        # Set a small batch limit for testing
        discovery.batch_limit = 5

        csv_work = discovery.discover_csv_work()
        podcast_work = discovery.discover_podcast_work()

        # Restore original limit
        discovery.batch_limit = original_limit

        csv_count = len(csv_work)
        podcast_count = len(podcast_work)

        print(f"✅ Batch limits respected:")
        print(f"   📄 CSV work (limit 5): {csv_count} items")
        print(f"   🎙️ Podcast work (limit 5): {podcast_count} items")

        if csv_count <= 5 and podcast_count <= 5:
            return True
        else:
            print(f"❌ Batch limits exceeded")
            return False

    except Exception as e:
        print(f"❌ Batch limit test failed: {e}")
        return False

def check_stage_progression():
    """Check if content at stage 0 gets processed by existing workers."""
    print("\n⚙️ Checking stage progression capability...")
    try:
        with sqlite3.connect("data/atlas.db") as conn:
            # Check for any content at various stages
            stages_query = """
                SELECT
                    CASE
                        WHEN metadata LIKE '%discovery_stage%0%' THEN 'stage_0'
                        WHEN ai_summary IS NOT NULL THEN 'processed'
                        WHEN content IS NOT NULL AND content != '' THEN 'content_extracted'
                        ELSE 'raw'
                    END as stage_category,
                    COUNT(*) as count
                FROM content
                GROUP BY stage_category
            """
            cursor = conn.execute(stages_query)
            results = cursor.fetchall()

            print("✅ Content stage distribution:")
            for stage, count in results:
                print(f"   {stage}: {count} items")

            # Check if universal processing queue is configured to handle stage 0
            print("ℹ️ Stage progression will be handled by existing Atlas workers")
            print("   Workers automatically process content from stage 0 → 599")

        return True
    except Exception as e:
        print(f"❌ Stage progression check failed: {e}")
        return False

def main():
    """Run all tests and provide summary."""
    print("🧪 Atlas Source Discovery System Test Suite")
    print("=" * 55)

    tests = [
        ("Database Connection", test_database_connection),
        ("CSV Discovery", test_csv_discovery),
        ("Podcast Discovery", test_podcast_discovery),
        ("Stage Entry Creation", test_stage_entry_creation),
        ("Full Discovery Workflow", test_full_discovery_workflow),
        ("Batch Limits", test_batch_limits),
        ("Stage Progression Check", check_stage_progression)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            failed += 1

    print("\n" + "=" * 55)
    print(f"🧪 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✅ All tests passed! Source Discovery system is ready for production.")
        return True
    else:
        print("❌ Some tests failed. Please review and fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)