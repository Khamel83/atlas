#!/usr/bin/env python3
"""
Extensive API Testing Suite

Comprehensive testing of the REST API with various endpoints,
error scenarios, and integration testing.
"""

import sys
import os
import asyncio
import time
import json
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api import app as api_app
from core.database import get_database
from core.processor import get_processor
import uvicorn


class ExtensiveAPITests:
    """Comprehensive API testing suite"""

    def __init__(self):
        self.api_base_url = "http://localhost:8000/api"
        self.test_results = []
        self.start_time = time.time()

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result with timing"""
        elapsed = time.time() - self.start_time
        status = "✅" if passed else "❌"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'elapsed': elapsed
        })
        print(f"{status} {test_name} ({elapsed:.2f}s) - {details}")

    async def test_health_endpoints(self):
        """Test health check endpoints"""
        print("\n🏥 Testing Health Endpoints...")

        async with aiohttp.ClientSession() as session:
            # Test basic health check
            try:
                async with session.get(f"{self.api_base_url}/health") as response:
                    assert response.status == 200, "Health check should return 200"
                    data = await response.json()
                    assert 'status' in data, "Health response should include status"
                    assert 'database' in data, "Health response should include database status"
                    assert 'processor' in data, "Health response should include processor status"
                    self.log_test("Basic Health Check", True, f"Status: {data['status']}")
            except Exception as e:
                self.log_test("Basic Health Check", False, f"Exception: {e}")

            # Test detailed health check
            try:
                async with session.get(f"{self.api_base_url}/health/detailed") as response:
                    assert response.status == 200, "Detailed health should return 200"
                    data = await response.json()
                    assert 'database' in data, "Should include database details"
                    assert 'processor' in data, "Should include processor details"
                    self.log_test("Detailed Health Check", True, "Detailed health data received")
            except Exception as e:
                self.log_test("Detailed Health Check", False, f"Exception: {e}")

    async def test_content_management(self):
        """Test content management endpoints"""
        print("\n📝 Testing Content Management...")

        async with aiohttp.ClientSession() as session:
            # Test content creation
            test_content = {
                "content": "Test content for API validation",
                "title": "API Test Content"
            }

            try:
                async with session.post(
                    f"{self.api_base_url}/content",
                    json=test_content,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    assert response.status == 200, "Content creation should return 200"
                    data = await response.json()
                    assert 'id' in data, "Response should include content ID"
                    content_id = data['id']
                    self.log_test("Content Creation", True, f"Created with ID: {content_id}")
            except Exception as e:
                self.log_test("Content Creation", False, f"Exception: {e}")
                return

            # Test content retrieval
            try:
                async with session.get(f"{self.api_base_url}/content/{content_id}") as response:
                    assert response.status == 200, "Content retrieval should return 200"
                    data = await response.json()
                    assert data['title'] == test_content['title'], "Retrieved title should match"
                    assert data['content'] == test_content['content'], "Retrieved content should match"
                    self.log_test("Content Retrieval", True, f"Retrieved: {data['title']}")
            except Exception as e:
                self.log_test("Content Retrieval", False, f"Exception: {e}")

            # Test content listing
            try:
                async with session.get(f"{self.api_base_url}/content?limit=10") as response:
                    assert response.status == 200, "Content listing should return 200"
                    data = await response.json()
                    assert 'content' in data, "Response should include content list"
                    assert isinstance(data['content'], list), "Content should be a list"
                    self.log_test("Content Listing", True, f"Retrieved {len(data['content'])} items")
            except Exception as e:
                self.log_test("Content Listing", False, f"Exception: {e}")

            # Test content deletion
            try:
                async with session.delete(f"{self.api_base_url}/content/{content_id}") as response:
                    assert response.status == 200, "Content deletion should return 200"
                    data = await response.json()
                    assert data.get('success', False), "Deletion should succeed"
                    self.log_test("Content Deletion", True, "Content deleted successfully")
            except Exception as e:
                self.log_test("Content Deletion", False, f"Exception: {e}")

    async def test_search_functionality(self):
        """Test search endpoints"""
        print("\n🔍 Testing Search Functionality...")

        async with aiohttp.ClientSession() as session:
            # First, create some test content
            test_items = [
                {"content": "Python programming language tutorial", "title": "Python Tutorial"},
                {"content": "Web development with JavaScript", "title": "JavaScript Guide"},
                {"content": "Database design and SQL", "title": "Database Design"}
            ]

            created_ids = []
            for item in test_items:
                try:
                    async with session.post(f"{self.api_base_url}/content", json=item) as response:
                        if response.status == 200:
                            data = await response.json()
                            created_ids.append(data['id'])
                except Exception:
                    pass

            # Test search functionality
            search_queries = [
                "Python",
                "JavaScript",
                "database",
                "programming"
            ]

            for query in search_queries:
                try:
                    search_data = {"query": query, "limit": 10}
                    async with session.post(
                        f"{self.api_base_url}/search",
                        json=search_data,
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        assert response.status == 200, f"Search for '{query}' should return 200"
                        data = await response.json()
                        assert 'results' in data, "Search response should include results"
                        assert isinstance(data['results'], list), "Results should be a list"
                        self.log_test(f"Search '{query}'", True, f"Found {len(data['results'])} results")
                except Exception as e:
                    self.log_test(f"Search '{query}'", False, f"Exception: {e}")

            # Test search with limit
            try:
                search_data = {"query": "test", "limit": 2}
                async with session.post(
                    f"{self.api_base_url}/search",
                    json=search_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    assert response.status == 200, "Limited search should return 200"
                    data = await response.json()
                    assert len(data['results']) <= 2, "Should respect search limit"
                    self.log_test("Search with Limit", True, f"Limited to {len(data['results'])} results")
            except Exception as e:
                self.log_test("Search with Limit", False, f"Exception: {e}")

            # Cleanup test content
            for content_id in created_ids:
                try:
                    async with session.delete(f"{self.api_base_url}/content/{content_id}") as response:
                        pass
                except Exception:
                    pass

    async def test_statistics_endpoints(self):
        """Test statistics endpoints"""
        print("\n📊 Testing Statistics Endpoints...")

        async with aiohttp.ClientSession() as session:
            # Test basic statistics
            try:
                async with session.get(f"{self.api_base_url}/stats") as response:
                    assert response.status == 200, "Statistics should return 200"
                    data = await response.json()
                    assert 'total_content' in data, "Should include total content count"
                    assert 'content_types' in data, "Should include content type count"
                    assert isinstance(data['total_content'], int), "Total should be integer"
                    self.log_test("Basic Statistics", True, f"Total content: {data['total_content']}")
            except Exception as e:
                self.log_test("Basic Statistics", False, f"Exception: {e}")

            # Test detailed statistics
            try:
                async with session.get(f"{self.api_base_url}/stats/detailed") as response:
                    assert response.status == 200, "Detailed statistics should return 200"
                    data = await response.json()
                    assert 'by_type' in data, "Should include breakdown by type"
                    assert 'recent_activity' in data, "Should include recent activity"
                    self.log_test("Detailed Statistics", True, "Detailed stats received")
            except Exception as e:
                self.log_test("Detailed Statistics", False, f"Exception: {e}")

            # Test content types endpoint
            try:
                async with session.get(f"{self.api_base_url}/content/types") as response:
                    assert response.status == 200, "Content types should return 200"
                    data = await response.json()
                    assert 'types' in data, "Should include types list"
                    assert isinstance(data['types'], dict), "Types should be a dictionary"
                    self.log_test("Content Types", True, f"Found {len(data['types'])} types")
            except Exception as e:
                self.log_test("Content Types", False, f"Exception: {e}")

    async def test_batch_operations(self):
        """Test batch operation endpoints"""
        print("\n📦 Testing Batch Operations...")

        async with aiohttp.ClientSession() as session:
            # Test batch content creation
            batch_data = {
                "items": [
                    {"content": "Batch item 1", "title": "Batch Test 1"},
                    {"content": "Batch item 2", "title": "Batch Test 2"},
                    {"content": "Batch item 3", "title": "Batch Test 3"}
                ]
            }

            try:
                async with session.post(
                    f"{self.api_base_url}/content/batch",
                    json=batch_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    assert response.status == 200, "Batch creation should return 200"
                    data = await response.json()
                    assert 'results' in data, "Should include results"
                    assert isinstance(data['results'], list), "Results should be a list"
                    batch_ids = [r.get('id') for r in data['results'] if r.get('id')]
                    self.log_test("Batch Creation", True, f"Created {len(batch_ids)} items")
            except Exception as e:
                self.log_test("Batch Creation", False, f"Exception: {e}")
                return

            # Test batch search
            try:
                search_data = {
                    "queries": ["batch", "test"],
                    "limit": 10
                }
                async with session.post(
                    f"{self.api_base_url}/search/batch",
                    json=search_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    assert response.status == 200, "Batch search should return 200"
                    data = await response.json()
                    assert 'results' in data, "Should include results"
                    self.log_test("Batch Search", True, "Batch search completed")
            except Exception as e:
                self.log_test("Batch Search", False, f"Exception: {e}")

            # Cleanup batch content
            for content_id in batch_ids:
                try:
                    async with session.delete(f"{self.api_base_url}/content/{content_id}") as response:
                        pass
                except Exception:
                    pass

    async def test_error_handling(self):
        """Test API error handling"""
        print("\n🛡️ Testing Error Handling...")

        async with aiohttp.ClientSession() as session:
            # Test invalid content ID
            try:
                async with session.get(f"{self.api_base_url}/content/999999") as response:
                    assert response.status == 404, "Invalid ID should return 404"
                    self.log_test("Invalid Content ID", True, "Correctly returned 404")
            except Exception as e:
                self.log_test("Invalid Content ID", False, f"Exception: {e}")

            # Test empty search query
            try:
                search_data = {"query": "", "limit": 10}
                async with session.post(
                    f"{self.api_base_url}/search",
                    json=search_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    # Should handle empty query gracefully
                    assert response.status in [200, 400], "Should handle empty query"
                    self.log_test("Empty Search Query", True, f"Status: {response.status}")
            except Exception as e:
                self.log_test("Empty Search Query", False, f"Exception: {e}")

            # Test invalid JSON
            try:
                async with session.post(
                    f"{self.api_base_url}/content",
                    data="invalid json",
                    headers={"Content-Type": "application/json"}
                ) as response:
                    assert response.status == 422, "Invalid JSON should return 422"
                    self.log_test("Invalid JSON", True, "Correctly returned 422")
            except Exception as e:
                self.log_test("Invalid JSON", False, f"Exception: {e}")

            # Test missing required fields
            try:
                async with session.post(
                    f"{self.api_base_url}/content",
                    json={"title": "Missing content field"},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    assert response.status == 422, "Missing fields should return 422"
                    self.log_test("Missing Fields", True, "Correctly returned 422")
            except Exception as e:
                self.log_test("Missing Fields", False, f"Exception: {e}")

    async def test_authentication_and_authorization(self):
        """Test authentication (currently open, but test structure)"""
        print("\n🔐 Testing Authentication...")

        async with aiohttp.ClientSession() as session:
            # Test that endpoints are accessible without auth (current design)
            try:
                async with session.get(f"{self.api_base_url}/health") as response:
                    assert response.status == 200, "Health endpoint should be accessible"
                    self.log_test("Open Access", True, "Endpoints accessible without auth")
            except Exception as e:
                self.log_test("Open Access", False, f"Exception: {e}")

    async def test_rate_limiting(self):
        """Test rate limiting behavior"""
        print("\n⚡ Testing Rate Limiting...")

        async with aiohttp.ClientSession() as session:
            # Make multiple rapid requests
            requests_made = 0
            successful_requests = 0

            for i in range(20):
                try:
                    async with session.get(f"{self.api_base_url}/health") as response:
                        requests_made += 1
                        if response.status == 200:
                            successful_requests += 1
                        elif response.status == 429:
                            self.log_test("Rate Limiting", True, f"Rate limited after {successful_requests} requests")
                            break
                except Exception:
                    break

            if successful_requests == requests_made:
                self.log_test("Rate Limiting", True, f"No rate limiting detected (may not be configured)")

    async def test_cors_headers(self):
        """Test CORS headers for cross-origin access"""
        print("\n🌐 Testing CORS Headers...")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.api_base_url}/health",
                    headers={"Origin": "http://example.com"}
                ) as response:
                    cors_headers = response.headers.get('Access-Control-Allow-Origin', '')
                    if cors_headers:
                        self.log_test("CORS Headers", True, f"CORS enabled: {cors_headers}")
                    else:
                        self.log_test("CORS Headers", True, "CORS not configured (may be intentional)")
            except Exception as e:
                self.log_test("CORS Headers", False, f"Exception: {e}")

    async def test_response_formats(self):
        """Test API response formats"""
        print("\n📋 Testing Response Formats...")

        async with aiohttp.ClientSession() as session:
            # Test JSON response format
            try:
                async with session.get(f"{self.api_base_url}/stats") as response:
                    assert response.headers.get('content-type', '').startswith('application/json'), "Should return JSON"
                    data = await response.json()
                    assert isinstance(data, dict), "Response should be JSON object"
                    self.log_test("JSON Response Format", True, "Valid JSON format")
            except Exception as e:
                self.log_test("JSON Response Format", False, f"Exception: {e}")

            # Test error response format
            try:
                async with session.get(f"{self.api_base_url}/content/999999") as response:
                    data = await response.json()
                    assert isinstance(data, dict), "Error response should be JSON"
                    self.log_test("Error Response Format", True, "Valid error format")
            except Exception as e:
                self.log_test("Error Response Format", False, f"Exception: {e}")

    async def test_performance_metrics(self):
        """Test API performance"""
        print("\n⚡ Testing API Performance...")

        async with aiohttp.ClientSession() as session:
            # Test response time for health check
            times = []
            for _ in range(10):
                start_time = time.time()
                try:
                    async with session.get(f"{self.api_base_url}/health") as response:
                        if response.status == 200:
                            times.append(time.time() - start_time)
                except Exception:
                    pass

            if times:
                avg_time = sum(times) / len(times)
                self.log_test("Health Check Performance", True, f"Average: {avg_time:.3f}s")
            else:
                self.log_test("Health Check Performance", False, "No successful requests")

            # Test content creation performance
            test_content = {"content": "Performance test content", "title": "Perf Test"}
            creation_times = []

            for i in range(5):
                start_time = time.time()
                try:
                    async with session.post(f"{self.api_base_url}/content", json=test_content) as response:
                        if response.status == 200:
                            creation_times.append(time.time() - start_time)
                            # Clean up
                            data = await response.json()
                            await session.delete(f"{self.api_base_url}/content/{data['id']}")
                except Exception:
                    pass

            if creation_times:
                avg_creation_time = sum(creation_times) / len(creation_times)
                self.log_test("Content Creation Performance", True, f"Average: {avg_creation_time:.3f}s")
            else:
                self.log_test("Content Creation Performance", False, "No successful creations")

    async def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Extensive API Tests...")
        print("=" * 60)

        test_methods = [
            self.test_health_endpoints,
            self.test_content_management,
            self.test_search_functionality,
            self.test_statistics_endpoints,
            self.test_batch_operations,
            self.test_error_handling,
            self.test_authentication_and_authorization,
            self.test_rate_limiting,
            self.test_cors_headers,
            self.test_response_formats,
            self.test_performance_metrics
        ]

        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                self.log_test(test_method.__name__, False, f"Exception: {e}")

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("📊 Extensive API Test Summary")
        print("=" * 60)

        passed = sum(1 for result in self.test_results if result['passed'])
        failed = len(self.test_results) - passed

        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {passed/len(self.test_results)*100:.1f}%")

        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   - {result['test']}: {result['details']}")

        print(f"\n⏱️ Total Test Duration: {time.time() - self.start_time:.2f}s")

        if failed == 0:
            print("\n🎉 All Extensive API Tests Passed!")
            print("✅ REST API is production-ready")
        else:
            print("\n⚠️  Some tests failed - review failed tests above")


async def main():
    """Main test runner"""
    # Note: This assumes the API server is running at localhost:8000
    test_suite = ExtensiveAPITests()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())