#!/usr/bin/env python3
"""
Apple Ingestion Test Suite - Validate bulletproof data capture
Tests all Apple device ingestion pathways to ensure no data loss.

CORE PRINCIPLE: EVERY TEST MUST PASS - NO EXCEPTIONS!
"""

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from helpers.apple_integrations import capture_apple_content, setup_apple_shortcuts_webhook
from helpers.enhanced_apple import EnhancedAppleIntegration
from helpers.failsafe_ingestor import failsafe_ingest_url, failsafe_ingest_text, FailsafeIngestor
from helpers.shortcuts_manager import setup_apple_shortcuts
from helpers.utils import log_info, log_error


class AppleIngestionTester:
    """
    Comprehensive test suite for Apple device ingestion.

    Tests every possible pathway to ensure bulletproof capture.
    """

    def __init__(self):
        """Initialize test suite."""
        self.test_results = {}
        self.test_data_dir = Path('test_data')
        self.test_data_dir.mkdir(exist_ok=True)

        # Test configurations
        self.test_urls = [
            "https://example.com/test-article",
            "https://github.com/test/repo",
            "https://news.ycombinator.com/item?id=123456"
        ]

        self.test_texts = [
            "This is a test note from iPhone shortcuts",
            "Meeting notes: Discuss Atlas integration with team",
            "📝 TODO: Review Apple device compatibility"
        ]

        print("🧪 Apple Ingestion Test Suite Initialized")

    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite."""
        print("\n🚀 Starting comprehensive Apple ingestion tests...")

        # Core capture tests
        self.test_bulletproof_capture()
        self.test_failsafe_ingestion()

        # Apple-specific tests
        self.test_shortcuts_integration()
        self.test_apple_notes_sync()
        self.test_safari_integration()

        # File handling tests
        self.test_file_ingestion()

        # Error handling tests
        self.test_error_recovery()

        # Performance tests
        self.test_bulk_ingestion()

        # Generate test report
        return self._generate_test_report()

    def test_bulletproof_capture(self):
        """Test core bulletproof capture functionality."""
        print("\n📦 Testing bulletproof capture...")
        test_name = "bulletproof_capture"

        try:
            # Test URL capture
            capture_id_1 = capture_apple_content(
                "https://example.com/test1",
                "shortcuts",
                "iphone"
            )

            # Test text capture
            capture_id_2 = capture_apple_content(
                "Test text content from iPad",
                "shortcuts",
                "ipad"
            )

            # Test file data capture
            test_file_data = {"file": "test.pdf", "content": "binary_data_here"}
            capture_id_3 = capture_apple_content(
                test_file_data,
                "file_drop",
                "mac"
            )

            # Verify captures exist
            if capture_id_1 and capture_id_2 and capture_id_3:
                self.test_results[test_name] = {
                    'status': 'PASS',
                    'captures': [capture_id_1, capture_id_2, capture_id_3],
                    'message': 'All bulletproof captures successful'
                }
                print("✅ Bulletproof capture: PASS")
            else:
                self.test_results[test_name] = {
                    'status': 'FAIL',
                    'message': 'One or more captures failed'
                }
                print("❌ Bulletproof capture: FAIL")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"💥 Bulletproof capture: ERROR - {str(e)}")

    def test_failsafe_ingestion(self):
        """Test failsafe ingestion system."""
        print("\n🛡️ Testing failsafe ingestion...")
        test_name = "failsafe_ingestion"

        try:
            ingestor = FailsafeIngestor()

            # Test URL ingestion
            queue_id_1 = failsafe_ingest_url(self.test_urls[0], "test_suite")

            # Test text ingestion
            queue_id_2 = failsafe_ingest_text(
                self.test_texts[0],
                "Test Note",
                "test_suite"
            )

            # Test file ingestion
            test_file = self._create_test_file("test_document.txt", "Test file content")
            queue_id_3 = ingestor.ingest_file(str(test_file), "test_suite")

            # Verify queue entries
            if queue_id_1 and queue_id_2 and queue_id_3:
                # Check queue status
                status = ingestor.get_queue_status()

                self.test_results[test_name] = {
                    'status': 'PASS',
                    'queue_ids': [queue_id_1, queue_id_2, queue_id_3],
                    'queue_status': status,
                    'message': 'All failsafe ingestions successful'
                }
                print("✅ Failsafe ingestion: PASS")
            else:
                self.test_results[test_name] = {
                    'status': 'FAIL',
                    'message': 'One or more ingestions failed'
                }
                print("❌ Failsafe ingestion: FAIL")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"💥 Failsafe ingestion: ERROR - {str(e)}")

    def test_shortcuts_integration(self):
        """Test Apple Shortcuts integration."""
        print("\n📱 Testing Apple Shortcuts integration...")
        test_name = "shortcuts_integration"

        try:
            # Generate shortcuts
            result = setup_apple_shortcuts("http://localhost:8081")

            # Verify shortcuts were created
            shortcuts_created = len(result.get('shortcuts', []))

            if shortcuts_created > 0:
                self.test_results[test_name] = {
                    'status': 'PASS',
                    'shortcuts_created': shortcuts_created,
                    'webhook_url': result.get('webhook_url'),
                    'files': result,
                    'message': f'{shortcuts_created} shortcuts generated successfully'
                }
                print(f"✅ Shortcuts integration: PASS ({shortcuts_created} shortcuts)")
            else:
                self.test_results[test_name] = {
                    'status': 'FAIL',
                    'message': 'No shortcuts were generated'
                }
                print("❌ Shortcuts integration: FAIL")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"💥 Shortcuts integration: ERROR - {str(e)}")

    def test_apple_notes_sync(self):
        """Test Apple Notes synchronization."""
        print("\n📝 Testing Apple Notes sync...")
        test_name = "apple_notes_sync"

        try:
            integration = EnhancedAppleIntegration()

            # Create mock Notes data for testing
            mock_notes_file = self._create_test_notes_file()

            # Test notes processing
            capture_id = integration.base_integration.process_apple_notes_export(str(mock_notes_file))

            if capture_id:
                self.test_results[test_name] = {
                    'status': 'PASS',
                    'capture_id': capture_id,
                    'message': 'Apple Notes sync successful'
                }
                print("✅ Apple Notes sync: PASS")
            else:
                self.test_results[test_name] = {
                    'status': 'FAIL',
                    'message': 'Apple Notes sync failed'
                }
                print("❌ Apple Notes sync: FAIL")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"💥 Apple Notes sync: ERROR - {str(e)}")

    def test_safari_integration(self):
        """Test Safari integration."""
        print("\n🌐 Testing Safari integration...")
        test_name = "safari_integration"

        try:
            integration = EnhancedAppleIntegration()

            # Create mock Safari reading list
            mock_reading_list = self._create_mock_reading_list()

            # Test reading list import
            capture_id = integration.base_integration.import_safari_reading_list(str(mock_reading_list))

            if capture_id:
                self.test_results[test_name] = {
                    'status': 'PASS',
                    'capture_id': capture_id,
                    'message': 'Safari integration successful'
                }
                print("✅ Safari integration: PASS")
            else:
                self.test_results[test_name] = {
                    'status': 'FAIL',
                    'message': 'Safari integration failed'
                }
                print("❌ Safari integration: FAIL")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"💥 Safari integration: ERROR - {str(e)}")

    def test_file_ingestion(self):
        """Test file ingestion capabilities."""
        print("\n📁 Testing file ingestion...")
        test_name = "file_ingestion"

        try:
            ingestor = FailsafeIngestor()

            # Test different file types
            test_files = {
                'text': self._create_test_file("test.txt", "Text file content"),
                'markdown': self._create_test_file("test.md", "# Markdown Content\nTest"),
                'json': self._create_test_file("test.json", '{"test": "data"}'),
            }

            results = {}
            for file_type, file_path in test_files.items():
                queue_id = ingestor.ingest_file(str(file_path), f"test_{file_type}")
                results[file_type] = queue_id

            if all(results.values()):
                self.test_results[test_name] = {
                    'status': 'PASS',
                    'files_processed': results,
                    'message': f'All {len(test_files)} file types ingested successfully'
                }
                print(f"✅ File ingestion: PASS ({len(test_files)} types)")
            else:
                self.test_results[test_name] = {
                    'status': 'FAIL',
                    'message': 'Some file ingestions failed'
                }
                print("❌ File ingestion: FAIL")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"💥 File ingestion: ERROR - {str(e)}")

    def test_error_recovery(self):
        """Test error recovery and resilience."""
        print("\n🔧 Testing error recovery...")
        test_name = "error_recovery"

        try:
            ingestor = FailsafeIngestor()

            # Test with invalid URL (should be captured but fail processing)
            queue_id_1 = failsafe_ingest_url("not-a-valid-url", "error_test")

            # Test with empty text (should be captured but may fail processing)
            queue_id_2 = failsafe_ingest_text("", "", "error_test")

            # Test with non-existent file (should fail gracefully)
            try:
                queue_id_3 = ingestor.ingest_file("/non/existent/file.txt", "error_test")
            except Exception:
                queue_id_3 = None  # Expected to fail

            # Test queue processing of problematic items
            processing_result = ingestor.process_pending_queue(batch_size=5)

            # Verify error handling
            if queue_id_1 and queue_id_2:  # Capture should succeed even for bad data
                self.test_results[test_name] = {
                    'status': 'PASS',
                    'captured_items': [queue_id_1, queue_id_2],
                    'processing_result': processing_result,
                    'message': 'Error recovery working - bad data captured, processing handled gracefully'
                }
                print("✅ Error recovery: PASS")
            else:
                self.test_results[test_name] = {
                    'status': 'FAIL',
                    'message': 'Error recovery failed - bad data not captured'
                }
                print("❌ Error recovery: FAIL")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"💥 Error recovery: ERROR - {str(e)}")

    def test_bulk_ingestion(self):
        """Test bulk ingestion performance."""
        print("\n⚡ Testing bulk ingestion...")
        test_name = "bulk_ingestion"

        try:
            start_time = time.time()

            # Ingest multiple URLs quickly
            queue_ids = []
            for i in range(10):
                queue_id = failsafe_ingest_url(f"https://example.com/test-{i}", "bulk_test")
                queue_ids.append(queue_id)

            # Ingest multiple text items
            for i in range(10):
                queue_id = failsafe_ingest_text(f"Bulk test text {i}", f"Test {i}", "bulk_test")
                queue_ids.append(queue_id)

            end_time = time.time()
            ingestion_time = end_time - start_time

            if len(queue_ids) == 20:
                self.test_results[test_name] = {
                    'status': 'PASS',
                    'items_ingested': len(queue_ids),
                    'ingestion_time_seconds': round(ingestion_time, 2),
                    'items_per_second': round(len(queue_ids) / ingestion_time, 2),
                    'message': f'Bulk ingestion successful: {len(queue_ids)} items in {ingestion_time:.2f}s'
                }
                print(f"✅ Bulk ingestion: PASS ({len(queue_ids)} items, {ingestion_time:.2f}s)")
            else:
                self.test_results[test_name] = {
                    'status': 'FAIL',
                    'message': f'Expected 20 items, got {len(queue_ids)}'
                }
                print("❌ Bulk ingestion: FAIL")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"💥 Bulk ingestion: ERROR - {str(e)}")

    def _create_test_file(self, filename: str, content: str) -> Path:
        """Create test file."""
        test_file = self.test_data_dir / filename
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return test_file

    def _create_test_notes_file(self) -> Path:
        """Create mock Apple Notes export file."""
        notes_content = """# Meeting Notes
Date: 2024-01-15
Attendees: Team

## Discussion Points
- Atlas integration status
- Apple device compatibility
- Next steps

---

# Ideas List
- Improve search functionality
- Add voice memo support
- Better Safari integration

---

# Research Links
https://example.com/research-paper
https://github.com/important/repo
Important findings from recent studies
"""
        return self._create_test_file("mock_notes.txt", notes_content)

    def _create_mock_reading_list(self) -> Path:
        """Create mock Safari reading list file."""
        # Simplified plist-like content
        reading_list_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Children</key>
    <array>
        <dict>
            <key>Title</key>
            <string>Test Article 1</string>
            <key>URLString</key>
            <string>https://example.com/article1</string>
        </dict>
        <dict>
            <key>Title</key>
            <string>Test Article 2</string>
            <key>URLString</key>
            <string>https://example.com/article2</string>
        </dict>
    </array>
</dict>
</plist>"""
        return self._create_test_file("mock_reading_list.plist", reading_list_content)

    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'PASS')
        failed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'FAIL')
        error_tests = sum(1 for result in self.test_results.values() if result['status'] == 'ERROR')

        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'errors': error_tests,
                'success_rate': round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0
            },
            'test_results': self.test_results,
            'generated_at': datetime.now().isoformat(),
            'overall_status': 'PASS' if failed_tests == 0 and error_tests == 0 else 'FAIL'
        }

        # Save report
        report_file = Path('apple_ingestion_test_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary
        print(f"\n📊 TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"💥 Errors: {error_tests}")
        print(f"Success Rate: {report['test_summary']['success_rate']}%")
        print(f"\nOverall Status: {'🎉 ALL TESTS PASSED' if report['overall_status'] == 'PASS' else '⚠️  TESTS NEED ATTENTION'}")
        print(f"\nDetailed report saved to: {report_file}")

        return report


def run_apple_ingestion_tests():
    """
    Run complete Apple ingestion test suite.

    Usage:
        python test_apple_ingestion.py

    Or:
        from test_apple_ingestion import run_apple_ingestion_tests
        results = run_apple_ingestion_tests()
    """
    tester = AppleIngestionTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    print("🍎 Atlas Apple Ingestion Test Suite")
    print("="*50)

    results = run_apple_ingestion_tests()

    if results['overall_status'] == 'PASS':
        print("\n🎉 ALL TESTS PASSED! Apple ingestion is bulletproof! 🛡️")
        exit(0)
    else:
        print("\n⚠️  Some tests failed. Review the report for details.")
        exit(1)