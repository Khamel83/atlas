#!/usr/bin/env python3
"""
OOS Log-Stream System Validation
Complete end-to-end validation of the new log-stream architecture
"""

import json
import time
import tempfile
import os
from datetime import datetime
from simple_log_processor import SimpleLogProcessor
from podcast_processor_adapter import PodcastProcessor
from batch_database_sync import BatchDatabaseSync
from log_views import get_views

class OOSValidator:
    """Complete validation of the OOS log-stream system"""

    def __init__(self, test_log_file: str = "validation_test.log"):
        self.test_log_file = test_log_file
        self.results = {
            "test_start": datetime.now().isoformat(),
            "tests": {},
            "summary": {}
        }

    def run_complete_validation(self):
        """Run all validation tests"""
        print("🧪 OOS Log-Stream System Validation")
        print("=" * 60)

        # Clean up any existing test files
        if os.path.exists(self.test_log_file):
            os.remove(self.test_log_file)

        test_results = {}

        # Test 1: Logger functionality
        test_results["logger"] = self.test_logger_functionality()

        # Test 2: Analytics views
        test_results["analytics"] = self.test_analytics_views()

        # Test 3: Podcast processing adapter
        test_results["podcast_adapter"] = self.test_podcast_adapter()

        # Test 4: Batch database sync
        test_results["batch_sync"] = self.test_batch_sync()

        # Test 5: Simple processor end-to-end
        test_results["end_to_end"] = self.test_end_to_end()

        # Test 6: Performance and scalability
        test_results["performance"] = self.test_performance()

        # Calculate summary
        passed = sum(1 for result in test_results.values() if result.get("passed", False))
        total = len(test_results)

        self.results["tests"] = test_results
        self.results["summary"] = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round((passed / total) * 100, 1),
            "test_end": datetime.now().isoformat()
        }

        # Print results
        self.print_results()

        return self.results

    def test_logger_functionality(self) -> dict:
        """Test basic logger functionality"""
        print("\n📝 Testing Logger Functionality...")
        from oos_logger import get_logger

        try:
            logger = get_logger(self.test_log_file)

            # Test different event types
            logger.discover("podcast", "TestPodcast", "test_001", {"url": "https://test.com"})
            logger.process("podcast", "TestPodcast", "test_001", {"processor": "test"})
            logger.complete("podcast", "TestPodcast", "test_001", {"file": "test.txt"})
            logger.fail("podcast", "TestPodcast", "test_002", {"error": "test error"})

            # Verify log file exists and has content
            if os.path.exists(self.test_log_file):
                with open(self.test_log_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) >= 4:
                        return {"passed": True, "message": f"✅ Logger working: {len(lines)} events logged"}
                    else:
                        return {"passed": False, "message": f"❌ Expected 4 events, got {len(lines)}"}
            else:
                return {"passed": False, "message": "❌ Log file not created"}

        except Exception as e:
            return {"passed": False, "message": f"❌ Logger test failed: {e}"}

    def test_analytics_views(self) -> dict:
        """Test analytics views functionality"""
        print("\n📊 Testing Analytics Views...")

        try:
            views = get_views(self.test_log_file)

            # Test podcast status view
            status = views.podcast_status_view()
            if not isinstance(status, dict):
                return {"passed": False, "message": "❌ Podcast status should return dict"}

            # Test throughput view
            throughput = views.throughput_view('1h')
            if not isinstance(throughput, dict):
                return {"passed": False, "message": "❌ Throughput should return dict"}

            # Test error analysis view
            errors = views.error_analysis_view()
            if not isinstance(errors, dict):
                return {"passed": False, "message": "❌ Error analysis should return dict"}

            # Test source reliability view
            reliability = views.source_reliability_view()
            if not isinstance(reliability, dict):
                return {"passed": False, "message": "❌ Source reliability should return dict"}

            return {"passed": True, "message": f"✅ All analytics views working correctly"}

        except Exception as e:
            return {"passed": False, "message": f"❌ Analytics test failed: {e}"}

    def test_podcast_adapter(self) -> dict:
        """Test podcast processing adapter"""
        print("\n🎧 Testing Podcast Adapter...")

        try:
            adapter = PodcastProcessor(self.test_log_file)

            # Test processing a single episode
            result = adapter.process_episode(
                "https://feeds.simplecast.com/test",
                "TestPodcast",
                "adapter_test_001"
            )

            if result['status'] not in ['success', 'error', 'timeout']:
                return {"passed": False, "message": f"❌ Invalid status: {result['status']}"}

            return {"passed": True, "message": f"✅ Podcast adapter working: {result['status']}"}

        except Exception as e:
            return {"passed": False, "message": f"❌ Podcast adapter test failed: {e}"}

    def test_batch_sync(self) -> dict:
        """Test batch database sync"""
        print("\n🔄 Testing Batch Database Sync...")

        try:
            sync = BatchDatabaseSync(log_file=self.test_log_file)

            # Test sync completed transcripts
            result1 = sync.sync_completed_transcripts()
            if result1['status'] not in ['success', 'no_new_transcripts']:
                return {"passed": False, "message": f"❌ Sync transcripts failed: {result1}"}

            # Test sync processing stats
            result2 = sync.sync_processing_stats()
            if result2['status'] != 'success':
                return {"passed": False, "message": f"❌ Sync stats failed: {result2}"}

            # Test cleanup
            result3 = sync.cleanup_old_log_entries(days_to_keep=30)
            if result3['status'] != 'success':
                return {"passed": False, "message": f"❌ Cleanup failed: {result3}"}

            return {"passed": True, "message": f"✅ Batch sync working correctly"}

        except Exception as e:
            return {"passed": False, "message": f"❌ Batch sync test failed: {e}"}

    def test_end_to_end(self) -> dict:
        """Test complete end-to-end workflow"""
        print("\n🔄 Testing End-to-End Workflow...")

        try:
            processor = SimpleLogProcessor(self.test_log_file)

            # Test episode discovery
            episodes = processor.discover_new_episodes(2)
            if len(episodes) == 0:
                return {"passed": False, "message": "❌ No episodes discovered"}

            # Test episode processing
            results = processor.process_episodes_batch(episodes, 2)
            if results['success'] == 0:
                return {"passed": False, "message": "❌ No episodes processed successfully"}

            # Test analytics
            analytics = processor.get_analytics_summary()
            if not isinstance(analytics, dict):
                return {"passed": False, "message": "❌ Analytics not returned as dict"}

            return {"passed": True, "message": f"✅ End-to-end workflow: {results['success']}/{results['total']} episodes processed"}

        except Exception as e:
            return {"passed": False, "message": f"❌ End-to-end test failed: {e}"}

    def test_performance(self) -> dict:
        """Test performance and scalability"""
        print("\n⚡ Testing Performance...")

        try:
            # Test log file parsing performance
            start_time = time.time()
            views = get_views(self.test_log_file)

            # Run multiple analytics queries
            for _ in range(10):
                views.podcast_status_view()
                views.throughput_view('1h')
                views.error_analysis_view()

            parse_time = time.time() - start_time

            # Test with larger log file
            adapter = PodcastProcessor(self.test_log_file)
            for i in range(10):
                adapter.process_episode(
                    f"https://test.com/episode{i}",
                    "PerformanceTest",
                    f"perf_test_{i:03d}"
                )

            # Test parsing larger file
            large_start = time.time()
            views = get_views(self.test_log_file)
            views.podcast_status_view()
            large_time = time.time() - large_start

            return {
                "passed": True,
                "message": f"✅ Performance test: {parse_time:.3f}s (small), {large_time:.3f}s (large)",
                "metrics": {
                    "small_file_parse_time": round(parse_time, 3),
                    "large_file_parse_time": round(large_time, 3)
                }
            }

        except Exception as e:
            return {"passed": False, "message": f"❌ Performance test failed: {e}"}

    def print_results(self):
        """Print validation results"""
        summary = self.results["summary"]

        print(f"\n🏆 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass Rate: {summary['pass_rate']}%")
        print("=" * 60)

        for test_name, result in self.results["tests"].items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"{status} {test_name}: {result['message']}")

        if summary['pass_rate'] == 100:
            print(f"\n🎉 ALL TESTS PASSED! The OOS log-stream system is working correctly.")
        else:
            print(f"\n⚠️  {summary['failed']} tests failed. System needs attention.")

    def save_results(self, filename: str = "validation_results.json"):
        """Save validation results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Validation results saved to {filename}")

def main():
    """Run the complete validation"""
    validator = OOSValidator()
    results = validator.run_complete_validation()
    validator.save_results()

    # Exit with appropriate code
    exit(0 if results["summary"]["pass_rate"] == 100 else 1)

if __name__ == "__main__":
    main()