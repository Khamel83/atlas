#!/usr/bin/env python3
"""
Test script for Atlas REST API

Verifies that the API endpoints work correctly for mobile integration.
"""

import sys
import os
import asyncio
import requests
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test configuration
API_BASE_URL = "http://localhost:8000"


def test_api_health():
    """Test API health endpoint"""
    print("🧪 Testing API health endpoint...")

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Health: {data['status']}")
            print(f"   Database: {data['database']}")
            print(f"   Processor: {data['processor']}")
            print(f"   Total Content: {data['total_content']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
        print("   Make sure the API is running with: python3 api.py")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_api_root():
    """Test API root endpoint"""
    print("\n🧪 Testing API root endpoint...")

    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Root: {data['name']} v{data['version']}")
            print(f"   Description: {data['description']}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False


def test_add_text_content():
    """Test adding text content"""
    print("\n🧪 Testing text content addition...")

    try:
        content_data = {
            "content": "This is a test article for the Atlas API. It contains multiple sentences to test the content processing functionality.",
            "title": "API Test Article",
            "source": "test_script"
        }

        response = requests.post(
            f"{API_BASE_URL}/content",
            json=content_data,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Content added successfully")
            print(f"   ID: {data['id']}")
            print(f"   Title: {data['title']}")
            print(f"   Type: {data['content_type']}")
            print(f"   Stage: {data['stage']}")
            return data['id']
        else:
            print(f"❌ Failed to add content: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Content addition error: {e}")
        return None


def test_add_url_content():
    """Test adding URL content"""
    print("\n🧪 Testing URL content addition...")

    try:
        content_data = {
            "content": "https://httpbin.org/html",
            "title": "Test URL Content"
        }

        response = requests.post(
            f"{API_BASE_URL}/content",
            json=content_data,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ URL content added successfully")
            print(f"   ID: {data['id']}")
            print(f"   Title: {data['title']}")
            print(f"   URL: {data['url']}")
            print(f"   Type: {data['content_type']}")
            return data['id']
        else:
            print(f"❌ Failed to add URL content: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ URL content addition error: {e}")
        return None


def test_get_content(content_id):
    """Test retrieving content by ID"""
    if not content_id:
        print("⚠️  Skipping content retrieval test (no content ID)")
        return False

    print(f"\n🧪 Testing content retrieval (ID: {content_id})...")

    try:
        response = requests.get(f"{API_BASE_URL}/content/{content_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Content retrieved successfully")
            print(f"   Title: {data['title']}")
            print(f"   Type: {data['content_type']}")
            print(f"   Created: {data['created_at']}")
            return True
        else:
            print(f"❌ Failed to retrieve content: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Content retrieval error: {e}")
        return False


def test_search_content():
    """Test content search"""
    print("\n🧪 Testing content search...")

    try:
        search_data = {
            "query": "test article",
            "limit": 10
        }

        response = requests.post(
            f"{API_BASE_URL}/search",
            json=search_data,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search completed successfully")
            print(f"   Query: {data['query']}")
            print(f"   Results: {data['total_results']}")

            if data['results']:
                print(f"   First result: {data['results'][0]['title']}")

            return True
        else:
            print(f"❌ Search failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Search error: {e}")
        return False


def test_list_content():
    """Test content listing"""
    print("\n🧪 Testing content listing...")

    try:
        response = requests.get(f"{API_BASE_URL}/content?limit=5", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Content listed successfully")
            print(f"   Total results: {data['total_results']}")
            print(f"   Limit: {data['limit']}")

            if data['results']:
                print(f"   Latest: {data['results'][0]['title']}")

            return True
        else:
            print(f"❌ Content listing failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Content listing error: {e}")
        return False


def test_get_stats():
    """Test statistics endpoint"""
    print("\n🧪 Testing statistics endpoint...")

    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Statistics retrieved successfully")
            print(f"   Total content: {data.get('total_content', 0)}")
            if 'by_type' in data:
                print(f"   Content types: {len(data['by_type'])}")
            return True
        else:
            print(f"❌ Statistics failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Statistics error: {e}")
        return False


def test_batch_content():
    """Test batch content processing"""
    print("\n🧪 Testing batch content processing...")

    try:
        batch_data = {
            "items": [
                {
                    "content": "First batch item for testing",
                    "title": "Batch Item 1"
                },
                {
                    "content": "Second batch item for testing",
                    "title": "Batch Item 2"
                },
                {
                    "content": "https://example.com",
                    "title": "Batch URL Item"
                }
            ]
        }

        response = requests.post(
            f"{API_BASE_URL}/content/batch",
            json=batch_data,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Batch processing completed")
            print(f"   Total items: {data['total_items']}")
            print(f"   Successful: {data['successful']}")
            print(f"   Failed: {data['failed']}")
            return True
        else:
            print(f"❌ Batch processing failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Batch processing error: {e}")
        return False


def test_content_types():
    """Test content types endpoint"""
    print("\n🧪 Testing content types endpoint...")

    try:
        response = requests.get(f"{API_BASE_URL}/content/types", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Content types retrieved")
            print(f"   Types found: {len(data['content_types'])}")

            for ct in data['content_types'][:3]:  # Show first 3
                print(f"   - {ct['type']}: {ct['count']}")

            return True
        else:
            print(f"❌ Content types failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Content types error: {e}")
        return False


def test_api_docs():
    """Test API documentation endpoints"""
    print("\n🧪 Testing API documentation...")

    try:
        # Test Swagger UI
        response = requests.get(f"{API_BASE_URL}/docs", timeout=10)
        if response.status_code == 200:
            print("✅ Swagger UI documentation available")
        else:
            print(f"⚠️  Swagger UI returned: {response.status_code}")

        # Test ReDoc
        response = requests.get(f"{API_BASE_URL}/redoc", timeout=10)
        if response.status_code == 200:
            print("✅ ReDoc documentation available")
        else:
            print(f"⚠️  ReDoc returned: {response.status_code}")

        return True
    except Exception as e:
        print(f"❌ Documentation test error: {e}")
        return False


async def test_all_api_endpoints():
    """Test all API endpoints"""
    print("🚀 Starting Atlas API Tests...")
    print("=" * 50)

    # Track test results
    passed = 0
    failed = 0
    content_ids = []

    # Run all tests
    tests = [
        ("Health Check", test_api_health),
        ("Root Endpoint", test_api_root),
        ("Text Content", test_add_text_content),
        ("URL Content", test_add_url_content),
        ("Content Types", test_content_types),
        ("Content Listing", test_list_content),
        ("Search", test_search_content),
        ("Statistics", test_get_stats),
        ("Batch Processing", test_batch_content),
        ("API Documentation", test_api_docs),
    ]

    for test_name, test_func in tests:
        try:
            if test_name == "Text Content":
                result = test_func()
                if result:
                    content_ids.append(result)
                    passed += 1
                else:
                    failed += 1
            elif test_name == "URL Content":
                result = test_func()
                if result:
                    content_ids.append(result)
                    passed += 1
                else:
                    failed += 1
            elif test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            failed += 1

    # Test content retrieval with the IDs we got
    if content_ids:
        print(f"\n🧪 Testing content retrieval with {len(content_ids)} IDs...")
        for content_id in content_ids:
            if test_get_content(content_id):
                passed += 1
            else:
                failed += 1

    # Print summary
    print("\n" + "=" * 50)
    print(f"📊 API Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All Atlas API tests passed!")
        print("\n📱 Mobile Integration Ready:")
        print("   ✅ REST API endpoints working")
        print("   ✅ Content addition and retrieval")
        print("   ✅ Search functionality")
        print("   ✅ Batch processing")
        print("   ✅ Statistics and monitoring")
        print("   ✅ Interactive documentation")
        return True
    else:
        print("❌ Some API tests failed!")
        return False


if __name__ == "__main__":
    print("🚀 Starting Atlas API Tests...")
    print("=" * 50)
    print("Note: Make sure the API server is running:")
    print("     python3 api.py")
    print("=" * 50)

    success = asyncio.run(test_all_api_endpoints())

    if not success:
        print("\n💡 Troubleshooting:")
        print("1. Make sure the API server is running: python3 api.py")
        print("2. Check that port 8000 is available")
        print("3. Verify all dependencies are installed")
        print("4. Check the API server logs for errors")

    sys.exit(0 if success else 1)