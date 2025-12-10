#!/usr/bin/env python3
"""
Extensive Database Testing Suite

Comprehensive testing of the Universal Database Service with
edge cases, performance testing, and stress scenarios.
"""

import sys
import os
import asyncio
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database import get_database, Content


class ExtensiveDatabaseTests:
    """Comprehensive database testing suite"""

    def __init__(self):
        self.db = get_database()
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

    def test_basic_operations(self):
        """Test basic CRUD operations"""
        print("\n🧪 Testing Basic Database Operations...")

        # Test content creation
        content = Content(
            title="Test Article",
            content="This is test content for database validation",
            content_type="article",
            url="https://example.com/test"
        )
        content_id = self.db.store_content(content)
        assert content_id > 0, "Content ID should be positive"
        self.log_test("Content Creation", True, f"ID: {content_id}")

        # Test content retrieval
        retrieved = self.db.get_content(content_id)
        assert retrieved is not None, "Content should be retrievable"
        assert retrieved.title == "Test Article", "Title should match"
        assert retrieved.content == "This is test content for database validation", "Content should match"
        self.log_test("Content Retrieval", True, f"Retrieved: {retrieved.title}")

        # Test content update
        retrieved.content = "Updated test content"
        updated_id = self.db.update_content(retrieved)
        assert updated_id == content_id, "Update should return same ID"

        updated = self.db.get_content(content_id)
        assert updated.content == "Updated test content", "Content should be updated"
        self.log_test("Content Update", True, "Content updated successfully")

        # Test content deletion
        deleted = self.db.delete_content(content_id)
        assert deleted, "Deletion should succeed"

        retrieved_after_delete = self.db.get_content(content_id)
        assert retrieved_after_delete is None, "Content should be deleted"
        self.log_test("Content Deletion", True, "Content deleted successfully")

    def test_search_functionality(self):
        """Test search with various scenarios"""
        print("\n🔍 Testing Search Functionality...")

        # Create test data
        test_contents = [
            Content(title="Python Programming", content="Learn Python programming language", content_type="article"),
            Content(title="Web Development", content="Build modern web applications", content_type="article"),
            Content(title="Database Design", content="Design efficient database systems", content_type="article"),
            Content(title="Machine Learning", content="Introduction to machine learning algorithms", content_type="article"),
            Content(title="Data Science", content="Data analysis and visualization techniques", content_type="article")
        ]

        content_ids = []
        for content in test_contents:
            content_id = self.db.store_content(content)
            content_ids.append(content_id)

        # Test basic search
        results = self.db.search_content("python")
        assert len(results) > 0, "Should find Python-related content"
        self.log_test("Basic Search", True, f"Found {len(results)} results for 'python'")

        # Test case-insensitive search
        results = self.db.search_content("PYTHON")
        assert len(results) > 0, "Case-insensitive search should work"
        self.log_test("Case-Insensitive Search", True, f"Found {len(results)} results for 'PYTHON'")

        # Test multi-word search
        results = self.db.search_content("web applications")
        assert len(results) > 0, "Multi-word search should work"
        self.log_test("Multi-Word Search", True, f"Found {len(results)} results for 'web applications'")

        # Test search with limit
        results = self.db.search_content("data", limit=2)
        assert len(results) <= 2, "Should respect search limit"
        self.log_test("Search with Limit", True, f"Limited to {len(results)} results")

        # Test search with no results
        results = self.db.search_content("nonexistentterm123456")
        assert len(results) == 0, "Should return empty for no matches"
        self.log_test("No Results Search", True, "Correctly returned 0 results")

        # Cleanup
        for content_id in content_ids:
            self.db.delete_content(content_id)

    def test_statistics_functionality(self):
        """Test statistics generation"""
        print("\n📊 Testing Statistics Functionality...")

        # Get initial stats
        initial_stats = self.db.get_statistics()
        initial_total = initial_stats.get('total_content', 0)

        # Add test content
        test_contents = [
            Content(title="Stat Test 1", content="Test content for statistics", content_type="article"),
            Content(title="Stat Test 2", content="Another test content", content_type="note"),
            Content(title="Stat Test 3", content="Third test content", content_type="article"),
        ]

        content_ids = []
        for content in test_contents:
            content_id = self.db.store_content(content)
            content_ids.append(content_id)

        # Check updated stats
        updated_stats = self.db.get_statistics()
        updated_total = updated_stats.get('total_content', 0)

        assert updated_total == initial_total + 3, "Should have 3 more items"
        self.log_test("Statistics Total Count", True, f"Total: {updated_total} (was {initial_total})")

        # Check content type breakdown
        by_type = updated_stats.get('by_type', {})
        assert by_type.get('article', 0) >= 2, "Should have at least 2 articles"
        assert by_type.get('note', 0) >= 1, "Should have at least 1 note"
        self.log_test("Content Type Breakdown", True, f"Articles: {by_type.get('article', 0)}, Notes: {by_type.get('note', 0)}")

        # Test recent content
        recent = self.db.get_recent_content(limit=5)
        assert len(recent) >= 3, "Should have at least 3 recent items"
        self.log_test("Recent Content", True, f"Retrieved {len(recent)} recent items")

        # Cleanup
        for content_id in content_ids:
            self.db.delete_content(content_id)

    def test_duplicate_detection(self):
        """Test duplicate content detection"""
        print("\n🔄 Testing Duplicate Detection...")

        # Store original content
        original = Content(
            title="Original Content",
            content="This is unique content for duplicate testing",
            content_type="article",
            url="https://example.com/unique"
        )
        original_id = self.db.store_content(original)

        # Try to store duplicate with same URL
        duplicate = Content(
            title="Updated Title",
            content="Updated content but same URL",
            content_type="article",
            url="https://example.com/unique"
        )
        duplicate_id = self.db.store_content(duplicate)

        # Should return the same ID (update existing)
        assert duplicate_id == original_id, "Should update existing content instead of creating duplicate"
        self.log_test("URL Duplicate Detection", True, f"Returned same ID: {duplicate_id}")

        # Verify content was updated
        retrieved = self.db.get_content(original_id)
        assert retrieved.title == "Updated Title", "Title should be updated"
        assert retrieved.content == "Updated content but same URL", "Content should be updated"
        self.log_test("Duplicate Content Update", True, "Content properly updated")

        # Cleanup
        self.db.delete_content(original_id)

    def test_stage_management(self):
        """Test stage-based processing system"""
        print("\n📈 Testing Stage Management...")

        # Create content with initial stage
        content = Content(
            title="Stage Test",
            content="Content for stage testing",
            content_type="article",
            stage=0
        )
        content_id = self.db.store_content(content)

        # Test stage updates
        for stage in [100, 200, 300, 400, 500]:
            success = self.db.update_content_stage(content_id, stage)
            assert success, f"Stage update to {stage} should succeed"

            retrieved = self.db.get_content(content_id)
            assert retrieved.stage == stage, f"Stage should be {stage}"
            self.log_test(f"Stage Update to {stage}", True, f"Stage: {retrieved.stage}")

        # Test content retrieval by stage (should be at stage 500 now)
        stage_500_content = self.db.get_content_by_stage(500)
        assert len(stage_500_content) > 0, "Should find content at stage 500"
        self.log_test("Content by Stage", True, f"Found {len(stage_500_content)} items at stage 500")

        # Cleanup
        self.db.delete_content(content_id)

    def test_concurrent_access(self):
        """Test concurrent database access"""
        print("\n🔄 Testing Concurrent Access...")

        def worker(worker_id: int) -> list[int]:
            """Worker function for concurrent testing"""
            content_ids = []
            for i in range(10):
                content = Content(
                    title=f"Worker {worker_id} Content {i}",
                    content=f"Content from worker {worker_id}, item {i}",
                    content_type="test"
                )
                content_id = self.db.store_content(content)
                content_ids.append(content_id)

                # Small delay to simulate processing
                time.sleep(0.01)
            return content_ids

        # Run multiple workers concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            all_content_ids = []

            for future in as_completed(futures):
                try:
                    content_ids = future.result()
                    all_content_ids.extend(content_ids)
                except Exception as e:
                    self.log_test(f"Concurrent Worker", False, f"Error: {e}")
                    return

        # Verify all content was stored
        assert len(all_content_ids) == 50, f"Should have 50 items, got {len(all_content_ids)}"
        self.log_test("Concurrent Storage", True, f"Stored {len(all_content_ids)} items concurrently")

        # Verify all content is retrievable
        successful_retrievals = 0
        for content_id in all_content_ids:
            if self.db.get_content(content_id) is not None:
                successful_retrievals += 1

        assert successful_retrievals == 50, f"Should retrieve all 50 items, got {successful_retrievals}"
        self.log_test("Concurrent Retrieval", True, f"Retrieved {successful_retrievals}/50 items")

        # Cleanup
        for content_id in all_content_ids:
            self.db.delete_content(content_id)

    def test_performance_metrics(self):
        """Test database performance"""
        print("\n⚡ Testing Performance Metrics...")

        # Test bulk insertion performance
        items_to_insert = 100
        start_time = time.time()

        content_ids = []
        for i in range(items_to_insert):
            content = Content(
                title=f"Performance Test {i}",
                content=f"Performance test content item {i}",
                content_type="test"
            )
            content_id = self.db.store_content(content)
            content_ids.append(content_id)

        insertion_time = time.time() - start_time
        items_per_second = items_to_insert / insertion_time

        self.log_test("Bulk Insertion", True,
                    f"{items_to_insert} items in {insertion_time:.2f}s ({items_per_second:.1f} items/s)")

        # Test search performance
        search_terms = ["performance", "test", "content", "item"]
        start_time = time.time()

        for term in search_terms:
            results = self.db.search_content(term, limit=50)

        search_time = time.time() - start_time
        self.log_test("Search Performance", True,
                    f"4 searches in {search_time:.3f}s ({search_time/4:.3f}s per search)")

        # Test statistics generation performance
        start_time = time.time()
        stats = self.db.get_statistics()
        stats_time = time.time() - start_time

        self.log_test("Statistics Generation", True,
                    f"Generated in {stats_time:.3f}s")

        # Cleanup
        for content_id in content_ids:
            self.db.delete_content(content_id)

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n🛡️ Testing Edge Cases...")

        # Test empty content
        try:
            empty_content = Content(title="", content="", content_type="test")
            content_id = self.db.store_content(empty_content)
            # Should work (empty content is allowed)
            self.log_test("Empty Content", True, "Empty content accepted")
            self.db.delete_content(content_id)
        except Exception as e:
            self.log_test("Empty Content", False, f"Error: {e}")

        # Test very long content
        long_content = "Very long content. " * 1000  # ~25KB
        try:
            long_content_obj = Content(title="Long Content", content=long_content, content_type="test")
            content_id = self.db.store_content(long_content_obj)

            retrieved = self.db.get_content(content_id)
            assert len(retrieved.content) == len(long_content), "Long content should be preserved"
            self.log_test("Long Content", True, f"Stored {len(long_content)} characters")
            self.db.delete_content(content_id)
        except Exception as e:
            self.log_test("Long Content", False, f"Error: {e}")

        # Test special characters
        special_content = "Special characters: áéíóú 中文 عربى 😊 🎉"
        try:
            special_content_obj = Content(title="Special Chars", content=special_content, content_type="test")
            content_id = self.db.store_content(special_content_obj)

            retrieved = self.db.get_content(content_id)
            assert retrieved.content == special_content, "Special characters should be preserved"
            self.log_test("Special Characters", True, "Unicode content preserved")
            self.db.delete_content(content_id)
        except Exception as e:
            self.log_test("Special Characters", False, f"Error: {e}")

        # Test non-existent content retrieval
        non_existent = self.db.get_content(999999)
        assert non_existent is None, "Should return None for non-existent content"
        self.log_test("Non-existent Content", True, "Correctly returned None")

    def test_database_health(self):
        """Test database health monitoring"""
        print("\n🏥 Testing Database Health...")

        # Test basic health check
        health = self.db.health_check()
        assert health['status'] == 'healthy', "Database should be healthy"
        assert 'total_content' in health, "Health check should include total_content"
        self.log_test("Health Check", True, f"Status: {health['status']}, Items: {health.get('total_content', 0)}")

        # Test connection pool info
        pool_info = self.db.get_connection_pool_info()
        assert isinstance(pool_info, dict), "Should return pool info dict"
        self.log_test("Connection Pool Info", True, f"Pool info available")

        # Test cache info
        cache_info = self.db.get_cache_info()
        assert isinstance(cache_info, dict), "Should return cache info dict"
        self.log_test("Cache Info", True, f"Cache info available")

    def run_all_tests(self):
        """Run all database tests"""
        print("🚀 Starting Extensive Database Tests...")
        print("=" * 60)

        test_methods = [
            self.test_basic_operations,
            self.test_search_functionality,
            self.test_statistics_functionality,
            self.test_duplicate_detection,
            self.test_stage_management,
            self.test_concurrent_access,
            self.test_performance_metrics,
            self.test_edge_cases,
            self.test_database_health
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test(test_method.__name__, False, f"Exception: {e}")

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("📊 Extensive Database Test Summary")
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
            print("\n🎉 All Extensive Database Tests Passed!")
            print("✅ Universal Database Service is production-ready")
        else:
            print("\n⚠️  Some tests failed - review failed tests above")


def main():
    """Main test runner"""
    test_suite = ExtensiveDatabaseTests()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()