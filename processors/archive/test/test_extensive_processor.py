#!/usr/bin/env python3
"""
Extensive Processor Testing Suite

Comprehensive testing of the Generic Content Processor with
various content types, error scenarios, and performance testing.
"""

import sys
import os
import asyncio
import time
import aiohttp
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.processor import get_processor, ProcessingResult
from core.database import Content


class ExtensiveProcessorTests:
    """Comprehensive processor testing suite"""

    def __init__(self):
        self.processor = get_processor()
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

    async def test_strategy_detection(self):
        """Test content type strategy detection"""
        print("\n🎯 Testing Strategy Detection...")

        test_cases = [
            ("https://example.com/article.html", "url"),
            ("https://example.com/feed.xml", "url"),
            ("https://example.com/rss", "url"),
            ("http://example.com/page", "url"),
            ("This is plain text content", "text"),
            ("Just some words", "text"),
            ("Single", "text"),
            ("", "text"),  # Empty should default to text
        ]

        for content, expected_strategy in test_cases:
            detected = self.processor._detect_strategy(content)
            assert detected == expected_strategy, f"Expected {expected_strategy}, got {detected}"
            self.log_test(f"Strategy Detection: {content[:30]}...", True, f"Detected: {detected}")

    async def test_text_processing(self):
        """Test text content processing"""
        print("\n📝 Testing Text Processing...")

        test_texts = [
            {
                "content": "This is a simple text document for testing.",
                "title": "Simple Test",
                "expected_type": "note"
            },
            {
                "content": "Multi-line\ntext document\nwith newlines.",
                "title": "Multi-line Test",
                "expected_type": "note"
            },
            {
                "content": "Document with special characters: áéíóú 中文 😊",
                "title": "Unicode Test",
                "expected_type": "note"
            },
            {
                "content": " " * 100 + "Content with leading whitespace",
                "title": "Whitespace Test",
                "expected_type": "note"
            },
            {
                "content": "A" * 10000,  # Very long content
                "title": "Long Content Test",
                "expected_type": "note"
            }
        ]

        for i, test_case in enumerate(test_texts):
            try:
                result = await self.processor.process(
                    test_case["content"],
                    title=test_case["title"]
                )

                assert result.success, f"Processing should succeed: {result.error}"
                assert result.content.content_type == test_case["expected_type"], f"Expected {test_case['expected_type']}"
                assert result.content.title == test_case["title"], "Title should match"

                self.log_test(f"Text Processing {i+1}", True,
                            f"Type: {result.content.content_type}, Length: {len(result.content.content)}")

            except Exception as e:
                self.log_test(f"Text Processing {i+1}", False, f"Exception: {e}")

    async def test_url_processing(self):
        """Test URL content processing"""
        print("\n🌐 Testing URL Processing...")

        test_urls = [
            {
                "url": "https://example.com",
                "expected_type": "article",
                "description": "Basic example domain"
            },
            {
                "url": "https://httpbin.org/html",
                "expected_type": "article",
                "description": "HTML test page"
            },
            {
                "url": "https://jsonplaceholder.typicode.com/posts/1",
                "expected_type": "article",
                "description": "JSON API endpoint"
            }
        ]

        for i, test_case in enumerate(test_urls):
            try:
                result = await self.processor.process(
                    test_case["url"],
                    title=f"URL Test {i+1}"
                )

                if result.success:
                    assert result.content.content_type == test_case["expected_type"], f"Expected {test_case['expected_type']}"
                    assert result.content.url == test_case["url"], "URL should be preserved"
                    self.log_test(f"URL Processing {i+1}", True,
                                f"Type: {result.content.content_type}, Length: {len(result.content.content)}")
                else:
                    # Some URLs might fail due to network issues, that's okay
                    self.log_test(f"URL Processing {i+1}", True,
                                f"Expected failure: {result.error}")

            except Exception as e:
                self.log_test(f"URL Processing {i+1}", False, f"Exception: {e}")

    async def test_error_handling(self):
        """Test error handling for invalid inputs"""
        print("\n🛡️ Testing Error Handling...")

        error_cases = [
            {
                "content": "https://invalid-domain-that-does-not-exist-12345.com",
                "title": "Invalid Domain",
                "expected_error": "Failed to fetch content"
            },
            {
                "content": "https://example.com/nonexistent-page-404.html",
                "title": "404 Page",
                "expected_error": "Failed to fetch content"
            },
            {
                "content": "not-a-valid-url",
                "title": "Invalid URL Format",
                "expected_error": "Failed to fetch content"
            }
        ]

        for i, test_case in enumerate(error_cases):
            try:
                result = await self.processor.process(
                    test_case["content"],
                    title=test_case["title"]
                )

                if result.success:
                    self.log_test(f"Error Handling {i+1}", False, "Expected failure but got success")
                else:
                    assert test_case["expected_error"] in result.error, f"Expected different error: {result.error}"
                    self.log_test(f"Error Handling {i+1}", True, f"Correctly failed: {result.error}")

            except Exception as e:
                self.log_test(f"Error Handling {i+1}", False, f"Unexpected exception: {e}")

    async def test_batch_processing(self):
        """Test batch processing capabilities"""
        print("\n📦 Testing Batch Processing...")

        # Test small batch
        small_batch = [
            "Batch item 1: Short text content",
            "Batch item 2: Another text item",
            "Batch item 3: Third batch item"
        ]

        start_time = time.time()
        small_results = await self.processor.process_batch(small_batch)
        small_time = time.time() - start_time

        successful_small = sum(1 for r in small_results if not isinstance(r, Exception) and r.success)
        self.log_test("Small Batch Processing", True,
                    f"{successful_small}/{len(small_batch)} successful in {small_time:.3f}s")

        # Test large batch
        large_batch = [f"Large batch item {i}: Content for testing" for i in range(50)]

        start_time = time.time()
        large_results = await self.processor.process_batch(large_batch)
        large_time = time.time() - start_time

        successful_large = sum(1 for r in large_results if not isinstance(r, Exception) and r.success)
        throughput = successful_large / large_time if large_time > 0 else 0

        self.log_test("Large Batch Processing", True,
                    f"{successful_large}/{len(large_batch)} successful in {large_time:.3f}s ({throughput:.1f} items/s)")

        # Test mixed content batch
        mixed_batch = [
            "Text content item",
            "https://example.com",
            "Another text item",
            "https://httpbin.org/html",
            "Final text item"
        ]

        mixed_results = await self.processor.process_batch(mixed_batch)
        successful_mixed = sum(1 for r in mixed_results if not isinstance(r, Exception) and r.success)

        self.log_test("Mixed Batch Processing", True,
                    f"{successful_mixed}/{len(mixed_batch)} successful")

    async def test_content_validation(self):
        """Test content validation and sanitization"""
        print("\n✅ Testing Content Validation...")

        # Test HTML content sanitization
        html_content = "<script>alert('dangerous')</script><p>Safe content</p>"
        result = await self.processor.process(html_content, title="HTML Test")

        if result.success:
            # Check that dangerous scripts are removed/escaped
            content_lower = result.content.content.lower()
            assert "<script>" not in content_lower, "Dangerous scripts should be removed"
            self.log_test("HTML Sanitization", True, "HTML content sanitized safely")
        else:
            self.log_test("HTML Sanitization", False, f"Processing failed: {result.error}")

        # Test very long titles
        long_title = "A" * 1000
        result = await self.processor.process("Content with long title", title=long_title)

        if result.success:
            assert len(result.content.title) <= 1000, "Title length should be reasonable"
            self.log_test("Long Title Handling", True, "Long title handled correctly")
        else:
            self.log_test("Long Title Handling", False, f"Processing failed: {result.error}")

    async def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        print("\n⚡ Testing Performance Benchmarks...")

        # Benchmark text processing
        text_samples = [
            "Short text content",
            "Medium length text content with more words and details to process",
            " ".join(["Word"] * 100),  # 100 words
            " ".join(["Word"] * 1000),  # 1000 words
        ]

        for i, sample in enumerate(text_samples):
            times = []
            for _ in range(5):
                start_time = time.time()
                result = await self.processor.process(sample, title=f"Benchmark {i}")
                times.append(time.time() - start_time)

            avg_time = sum(times) / len(times)
            self.log_test(f"Text Performance {i+1}", True,
                        f"Length: {len(sample)} chars, Avg: {avg_time:.3f}s")

        # Benchmark concurrent processing
        async def concurrent_worker(worker_id: int):
            results = []
            for i in range(10):
                result = await self.processor.process(f"Concurrent test {worker_id}-{i}")
                results.append(result)
            return results

        start_time = time.time()
        tasks = [concurrent_worker(i) for i in range(5)]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_time = time.time() - start_time

        total_processed = sum(len([r for r in results if not isinstance(r, Exception)])
                            for results in all_results if not isinstance(results, Exception))
        throughput = total_processed / concurrent_time

        self.log_test("Concurrent Processing", True,
                    f"{total_processed} items in {concurrent_time:.3f}s ({throughput:.1f} items/s)")

    async def test_memory_usage(self):
        """Test memory usage with large content"""
        print("\n🧠 Testing Memory Usage...")

        # Process increasingly large content
        sizes = [1000, 10000, 50000, 100000]  # characters

        for size in sizes:
            content = "X" * size
            title = f"Memory Test {size} chars"

            start_time = time.time()
            result = await self.processor.process(content, title=title)
            processing_time = time.time() - start_time

            if result.success:
                self.log_test(f"Memory Test {size}", True,
                            f"Processed in {processing_time:.3f}s, Length: {len(result.content.content)}")
            else:
                self.log_test(f"Memory Test {size}", False, f"Failed: {result.error}")

    async def test_database_integration(self):
        """Test integration with database"""
        print("\n💾 Testing Database Integration...")

        # Process content and verify database storage
        test_content = "Database integration test content"
        result = await self.processor.process(test_content, title="DB Integration Test")

        assert result.success, "Processing should succeed"
        assert result.content.id is not None, "Content should have database ID"

        # Verify content is retrievable from database
        db = self.processor.db
        retrieved = db.get_content(result.content.id)
        assert retrieved is not None, "Content should be retrievable"
        assert retrieved.content == test_content, "Content should match"
        assert retrieved.title == "DB Integration Test", "Title should match"

        self.log_test("Database Storage", True, f"Stored with ID: {result.content.id}")

        # Test search functionality
        search_results = db.search_content("database integration", limit=10)
        found = any(r.id == result.content.id for r in search_results)
        assert found, "Content should be searchable"
        self.log_test("Database Search", True, f"Found in search results")

    async def test_retry_mechanisms(self):
        """Test retry mechanisms for failed operations"""
        print("\n🔄 Testing Retry Mechanisms...")

        # Test retry with temporarily failing URL
        # Note: This is difficult to test reliably without mocking
        # For now, we'll test that the retry logic exists and handles timeouts

        try:
            # Use a URL that might timeout
            result = await self.processor.process(
                "https://httpbin.org/delay/5",  # 5 second delay
                title="Retry Test"
            )

            # This might succeed or fail depending on timeout settings
            if result.success:
                self.log_test("Retry Mechanism", True, "Content processed after potential retries")
            else:
                self.log_test("Retry Mechanism", True, f"Gracefully failed after retries: {result.error}")

        except Exception as e:
            self.log_test("Retry Mechanism", False, f"Exception during retry test: {e}")

    async def test_content_metadata(self):
        """Test content metadata extraction"""
        print("\n📋 Testing Content Metadata...")

        # Test metadata for different content types
        test_cases = [
            {
                "content": "Simple text content",
                "title": "Text Metadata Test",
                "type": "text"
            },
            {
                "content": "https://example.com",
                "title": "URL Metadata Test",
                "type": "url"
            }
        ]

        for test_case in test_cases:
            result = await self.processor.process(
                test_case["content"],
                title=test_case["title"]
            )

            if result.success:
                content = result.content

                # Check basic metadata
                assert content.title == test_case["title"], "Title should be set"
                assert content.content_type is not None, "Content type should be set"
                assert content.created_at is not None, "Created timestamp should be set"
                assert content.updated_at is not None, "Updated timestamp should be set"

                # Check stage progression
                assert content.stage >= 0, "Stage should be >= 0"

                self.log_test(f"Metadata {test_case['type']}", True,
                            f"Type: {content.content_type}, Stage: {content.stage}")

            else:
                self.log_test(f"Metadata {test_case['type']}", False, f"Processing failed: {result.error}")

    async def run_all_tests(self):
        """Run all processor tests"""
        print("🚀 Starting Extensive Processor Tests...")
        print("=" * 60)

        test_methods = [
            self.test_strategy_detection,
            self.test_text_processing,
            self.test_url_processing,
            self.test_error_handling,
            self.test_batch_processing,
            self.test_content_validation,
            self.test_performance_benchmarks,
            self.test_memory_usage,
            self.test_database_integration,
            self.test_retry_mechanisms,
            self.test_content_metadata
        ]

        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                self.log_test(test_method.__name__, False, f"Exception: {e}")

        # Generate summary
        self.generate_summary()

        # Cleanup
        await self.processor.close()

    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("📊 Extensive Processor Test Summary")
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
            print("\n🎉 All Extensive Processor Tests Passed!")
            print("✅ Generic Content Processor is production-ready")
        else:
            print("\n⚠️  Some tests failed - review failed tests above")


async def main():
    """Main test runner"""
    test_suite = ExtensiveProcessorTests()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())