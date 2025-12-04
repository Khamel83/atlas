#!/usr/bin/env python3
"""
Test script for Generic Content Processor

Verifies that the unified processor can handle different content types
and properly extract, store, and process content.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.processor import GenericContentProcessor, get_processor
from core.database import UniversalDatabase, get_database


async def test_processor_basic_operations():
    """Test basic processor operations"""
    print("🧪 Testing Generic Content Processor...")

    processor = GenericContentProcessor()

    # Test processor capabilities
    print("\n📋 Testing processor capabilities...")
    capabilities = processor.get_capabilities()
    print(f"✅ Available strategies: {capabilities['strategies']}")
    print(f"✅ Supported types: {capabilities['supported_types']}")

    # Test strategy selection
    print("\n🎯 Testing strategy selection...")
    test_cases = [
        ("https://example.com", "URLStrategy"),
        ("https://example.com/feed.xml", "RSSStrategy"),
        ("This is plain text content", "TextStrategy"),
    ]

    for input_data, expected_strategy in test_cases:
        strategy = processor.select_strategy(input_data)
        if strategy:
            print(f"✅ {input_data} -> {strategy.name}")
        else:
            print(f"❌ No strategy found for: {input_data}")

    # Test text processing
    print("\n📝 Testing text content processing...")
    test_text = """
    # Test Document

    This is a test document with multiple paragraphs.

    ## Section 1

    Lorem ipsum dolor sit amet, consectetur adipiscing elit.
    Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

    ## Section 2

    Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
    """

    result = await processor.process(test_text, title="Test Document")
    if result.success:
        print(f"✅ Text processing successful")
        print(f"   Title: {result.content.title}")
        print(f"   Type: {result.content.content_type}")
        print(f"   Content length: {len(result.content.content)}")
        print(f"   Processing time: {result.processing_time:.2f}s")
        print(f"   Stages completed: {result.stages_completed}")
    else:
        print(f"❌ Text processing failed: {result.error}")

    # Test URL processing (requires network)
    print("\n🌐 Testing URL content processing...")
    test_url = "https://httpbin.org/html"
    result = await processor.process(test_url)
    if result.success:
        print(f"✅ URL processing successful")
        print(f"   Title: {result.content.title}")
        print(f"   URL: {result.content.url}")
        print(f"   Content length: {len(result.content.content)}")
        print(f"   Processing time: {result.processing_time:.2f}s")
    else:
        print(f"⚠️  URL processing failed (expected if network unavailable): {result.error}")

    # Test health check
    print("\n🏥 Testing processor health check...")
    health = await processor.health_check()
    print(f"Health status: {health['status']}")
    print(f"Healthy strategies: {health['healthy_strategies']}/{health['total_strategies']}")
    if health['errors']:
        print(f"Errors: {health['errors']}")

    # Cleanup
    await processor.close()
    print("\n🎉 Basic processor tests completed!")
    return True


async def test_processor_database_integration():
    """Test processor integration with database"""
    print("\n🧪 Testing processor-database integration...")

    processor = GenericContentProcessor()
    db = get_database()

    # Process and store content
    test_content = "This is a test for database integration with the generic processor."
    result = await processor.process(test_content, title="Database Integration Test")

    if result.success and result.content.id:
        print(f"✅ Content stored with ID: {result.content.id}")

        # Retrieve from database
        retrieved = db.get_content(result.content.id)
        if retrieved:
            print(f"✅ Content retrieved from database")
            print(f"   Title: {retrieved.title}")
            print(f"   Stage: {retrieved.stage}")
            print(f"   AI summary: {retrieved.ai_summary}")
        else:
            print("❌ Failed to retrieve content from database")
            return False

        # Test search functionality
        search_results = db.search_content("database integration")
        if search_results:
            print(f"✅ Found {len(search_results)} search results")
        else:
            print("❌ No search results found")
            return False

        # Test statistics
        stats = db.get_statistics()
        print(f"✅ Database statistics: {stats['total_content']} total items")
    else:
        print("❌ Failed to store content in database")
        return False

    # Cleanup
    await processor.close()
    print("✅ Processor-database integration tests passed!")
    return True


async def test_processor_error_handling():
    """Test processor error handling"""
    print("\n🧪 Testing processor error handling...")

    processor = GenericContentProcessor()

    # Test invalid URL
    print("\n🔗 Testing invalid URL handling...")
    result = await processor.process("https://invalid-domain-that-does-not-exist-12345.com")
    if not result.success:
        print(f"✅ Invalid URL properly rejected: {result.error}")
    else:
        print("⚠️  Invalid URL was accepted (may be acceptable if DNS resolution worked)")
        return False

    # Test empty content
    print("\n📄 Testing empty content handling...")
    result = await processor.process("", title="Empty Test")
    if not result.success:
        print(f"✅ Empty content properly handled: {result.error}")
    else:
        print("⚠️  Empty content was accepted (may be acceptable)")

    # Test malformed RSS
    print("\n📡 Testing malformed RSS handling...")
    result = await processor.process("https://example.com/not-a-feed.xml")
    if not result.success:
        print(f"✅ Malformed RSS properly handled: {result.error}")
    else:
        print("⚠️  Malformed RSS was accepted (may be acceptable)")

    # Cleanup
    await processor.close()
    print("✅ Error handling tests completed!")
    return True


async def test_batch_processing():
    """Test batch processing functionality"""
    print("\n🧪 Testing batch processing...")

    processor = GenericContentProcessor()

    # Prepare batch items
    batch_items = [
        "First test item",
        "Second test item",
        "Third test item",
        "https://example.com",
        "Final test item"
    ]

    print(f"📦 Processing {len(batch_items)} items in batch...")
    start_time = asyncio.get_event_loop().time()

    results = await processor.process_batch(batch_items)

    processing_time = asyncio.get_event_loop().time() - start_time

    # Analyze results
    successful = 0
    failed = 0
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ Item {i+1} failed with exception: {result}")
            failed += 1
        elif result.success:
            print(f"✅ Item {i+1}: {result.content.title}")
            successful += 1
        else:
            print(f"❌ Item {i+1} failed: {result.error}")
            failed += 1

    print(f"\n📊 Batch processing results:")
    print(f"   Total items: {len(batch_items)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Processing time: {processing_time:.2f}s")
    print(f"   Average per item: {processing_time/len(batch_items):.2f}s")

    # Cleanup
    await processor.close()
    return True


async def main():
    """Run all processor tests"""
    print("🚀 Starting Generic Content Processor tests...")
    print("=" * 50)

    # Ensure config directory exists
    Path("config").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)

    # Create test config if it doesn't exist
    if not Path("config/test_database.yaml").exists():
        test_config = """
database:
  path: "data/test_atlas.db"
  max_connections: 5

connection_pool:
  max_connections: 5
  min_connections: 1

cache:
  enabled: true
  max_size: 100

performance:
  wal_mode: true
  foreign_keys: true
"""
        with open("config/test_database.yaml", "w") as f:
            f.write(test_config)

    # Run tests
    tests = [
        test_processor_basic_operations,
        test_processor_database_integration,
        test_processor_error_handling,
        test_batch_processing
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if await test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All Generic Content Processor tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)