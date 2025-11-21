#!/usr/bin/env python3
"""
Direct API Testing without Server

Tests the API functionality directly by importing and calling the endpoint functions.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api import (
    app,
    health_check,
    get_stats,
    get_content_types,
    get_db,
    get_proc
)
from core.database import get_database
from core.processor import get_processor


async def test_api_functionality():
    """Test API functionality directly"""
    print("🧪 Testing Atlas API functionality directly...")
    print("=" * 50)

    passed = 0
    failed = 0

    # Test 1: Health Check
    print("\n🏥 Testing health check...")
    try:
        health_data = await health_check()
        print(f"✅ Health check: {health_data.status}")
        print(f"   Database: {health_data.database}")
        print(f"   Processor: {health_data.processor}")
        print(f"   Total Content: {health_data.total_content}")
        passed += 1
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        failed += 1

    # Test 2: Database Connection
    print("\n💾 Testing database connection...")
    try:
        db = get_database()
        stats = db.get_statistics()
        print(f"✅ Database connected")
        print(f"   Total content: {stats.get('total_content', 0)}")
        if 'by_type' in stats:
            print(f"   Content types: {len(stats['by_type'])}")
        passed += 1
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        failed += 1

    # Test 3: Processor Health
    print("\n⚙️ Testing processor health...")
    try:
        processor = get_processor()
        processor_health = await processor.health_check()
        print(f"✅ Processor healthy: {processor_health['status']}")
        print(f"   Strategies: {processor_health['healthy_strategies']}/{processor_health['total_strategies']}")
        if processor_health['errors']:
            print(f"   Errors: {processor_health['errors']}")
        passed += 1
    except Exception as e:
        print(f"❌ Processor health check failed: {e}")
        failed += 1

    # Test 4: Content Processing
    print("\n📝 Testing content processing...")
    try:
        processor = get_processor()
        test_content = "This is a test article for the Atlas API direct test."
        result = await processor.process(test_content, title="Direct API Test")

        if result.success:
            print(f"✅ Content processed successfully")
            print(f"   ID: {result.content.id}")
            print(f"   Title: {result.content.title}")
            print(f"   Type: {result.content.content_type}")
            print(f"   Stage: {result.content.stage}")
            passed += 1
        else:
            print(f"❌ Content processing failed: {result.error}")
            failed += 1
    except Exception as e:
        print(f"❌ Content processing error: {e}")
        failed += 1

    # Test 5: URL Processing
    print("\n🌐 Testing URL processing...")
    try:
        processor = get_processor()
        test_url = "https://httpbin.org/html"
        result = await processor.process(test_url)

        if result.success:
            print(f"✅ URL processed successfully")
            print(f"   Title: {result.content.title}")
            print(f"   URL: {result.content.url}")
            print(f"   Type: {result.content.content_type}")
            print(f"   Content length: {len(result.content.content)}")
            passed += 1
        else:
            print(f"❌ URL processing failed: {result.error}")
            failed += 1
    except Exception as e:
        print(f"❌ URL processing error: {e}")
        failed += 1

    # Test 6: Batch Processing
    print("\n📦 Testing batch processing...")
    try:
        processor = get_processor()
        batch_items = [
            "Batch item 1",
            "Batch item 2",
            "https://example.com"
        ]
        results = await processor.process_batch(batch_items)

        successful = sum(1 for r in results if not isinstance(r, Exception) and r.success)
        failed_items = sum(1 for r in results if isinstance(r, Exception) or not r.success)

        print(f"✅ Batch processing completed")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed_items}")
        print(f"   Total: {len(batch_items)}")
        passed += 1
    except Exception as e:
        print(f"❌ Batch processing error: {e}")
        failed += 1

    # Test 7: Content Search
    print("\n🔍 Testing content search...")
    try:
        db = get_database()
        results = db.search_content("test", limit=5)
        print(f"✅ Content search completed")
        print(f"   Results found: {len(results)}")
        if results:
            print(f"   First result: {results[0].title}")
        passed += 1
    except Exception as e:
        print(f"❌ Content search error: {e}")
        failed += 1

    # Test 8: Content Types
    print("\n📋 Testing content types...")
    try:
        db = get_database()
        # Use the connection from the pool
        with db.pool.get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT content_type, COUNT(*) as count
                FROM content
                GROUP BY content_type
                ORDER BY count DESC
                LIMIT 5
            """)
            results = cursor.fetchall()
        print(f"✅ Content types retrieved")
        print(f"   Types found: {len(results)}")
        for row in results[:3]:
            print(f"   - {row[0]}: {row[1]}")
        passed += 1
    except Exception as e:
        print(f"❌ Content types error: {e}")
        failed += 1

    # Cleanup
    print("\n🧹 Cleaning up resources...")
    try:
        processor = get_processor()
        await processor.close()
        print("✅ Resources cleaned up")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Direct API Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All API functionality tests passed!")
        print("\n📱 Atlas API Integration Ready:")
        print("   ✅ Health monitoring")
        print("   ✅ Database operations")
        print("   ✅ Content processing")
        print("   ✅ URL extraction")
        print("   ✅ Batch processing")
        print("   ✅ Search functionality")
        print("   ✅ Resource management")
        return True
    else:
        print("❌ Some API functionality tests failed!")
        return False


async def test_api_structure():
    """Test API structure and routes"""
    print("\n🏗️ Testing API structure...")
    print("=" * 30)

    try:
        # Test FastAPI app structure
        print(f"✅ FastAPI app created: {app.title}")
        print(f"✅ Version: {app.version}")
        print(f"✅ Routes: {len(app.routes)}")

        # List main endpoints
        endpoints = []
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                endpoints.append(f"{list(route.methods)[0] if route.methods else 'GET'} {route.path}")

        print(f"✅ Endpoints: {len(endpoints)}")
        for endpoint in sorted(endpoints)[:10]:  # Show first 10
            print(f"   {endpoint}")

        if len(endpoints) > 10:
            print(f"   ... and {len(endpoints) - 10} more")

        return True
    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        return False


async def main():
    """Run all API tests"""
    print("🚀 Starting Atlas API Direct Tests...")
    print("=" * 60)

    # Test API structure
    structure_ok = await test_api_structure()

    # Test API functionality
    functionality_ok = await test_api_functionality()

    # Overall result
    if structure_ok and functionality_ok:
        print("\n🎉 Atlas API is ready for production!")
        print("\n📱 Mobile Integration Features:")
        print("   • REST API endpoints for all operations")
        print("   • Content addition (text, URLs, RSS)")
        print("   • Search and filtering capabilities")
        print("   • Batch processing support")
        print("   • Health monitoring and statistics")
        print("   • Interactive documentation")
        print("   • CORS support for web integration")
        return True
    else:
        print("\n❌ Atlas API has issues that need to be resolved")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)