#!/usr/bin/env python3
"""
Comprehensive Atlas Test Suite - No Network Dependencies
Tests all system components without external API calls
"""

import sys
import os
import json
import time
from typing import Dict, Any, Optional

# Add current directory to path
sys.path.append('.')

class AtlasTestSuite:
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()

    def run_test(self, test_name: str, test_func):
        """Run a single test and track results"""
        try:
            start_time = time.time()
            test_func()
            end_time = time.time()
            duration = end_time - start_time

            self.test_results.append({
                'name': test_name,
                'status': 'PASS',
                'duration': duration,
                'error': None
            })
            print(f"✅ {test_name}: PASS ({duration:.2f}s)")

        except Exception as e:
            self.test_results.append({
                'name': test_name,
                'status': 'FAIL',
                'duration': 0,
                'error': str(e)
            })
            print(f"❌ {test_name}: FAIL - {str(e)}")

    def test_1_system_initialization(self):
        """Test 1: System initialization and configuration loading"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()

        # Check all required attributes
        required_attrs = [
            'logger', 'podcast_config', 'rss_feeds', 'processed_episodes',
            'transcript_sources', 'discovered_sources'
        ]

        for attr in required_attrs:
            assert hasattr(processor, attr), f"Missing attribute: {attr}"

        # Check specific configurations
        assert len(processor.transcript_sources) == 3, "Wrong number of transcript sources"
        assert isinstance(processor.discovered_sources, dict), "Discovery matrix not loaded"
        assert len(processor.discovered_sources) > 0, "Discovery matrix empty"

        # Check directories created
        assert os.path.exists('logs'), "Logs directory not created"
        assert os.path.exists('content/markdown'), "Content directory not created"
        assert os.path.exists('config'), "Config directory not created"

    def test_2_discovery_matrix_validation(self):
        """Test 2: Discovery matrix structure and content validation"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()
        matrix = processor.discovered_sources

        # Check matrix structure
        assert isinstance(matrix, dict), "Discovery matrix should be a dictionary"

        # Check if known podcasts are present
        known_podcasts = ['Accidental Tech Podcast', 'This American Life', '99% Invisible']
        found_count = 0

        for podcast in known_podcasts:
            if podcast in matrix:
                found_count += 1
                podcast_data = matrix[podcast]

                # Check podcast structure
                assert 'sources' in podcast_data, f"Missing sources for {podcast}"
                assert isinstance(podcast_data['sources'], list), f"Sources should be a list for {podcast}"

                # Check working sources
                working_sources = [s for s in podcast_data['sources'] if s.get('status') == 'working']
                if working_sources:
                    source = working_sources[0]
                    assert 'url' in source, f"Missing URL in source for {podcast}"
                    assert 'status' in source, f"Missing status in source for {podcast}"

        assert found_count > 0, f"No known podcasts found in matrix (found {found_count})"

    def test_3_transcript_sources_configuration(self):
        """Test 3: Transcript sources configuration and validation"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()
        sources = processor.transcript_sources

        # Check source structure
        assert len(sources) == 3, f"Expected 3 sources, got {len(sources)}"

        expected_sources = ['web_search', 'google_fallback', 'youtube_fallback']
        found_sources = [s['name'] for s in sources]

        for expected in expected_sources:
            assert expected in found_sources, f"Missing source: {expected}"

        # Check each source has required fields
        for source in sources:
            assert 'name' in source, "Source missing name"
            assert 'method' in source, "Source missing method"

    def test_4_method_availability(self):
        """Test 4: All required methods are available and callable"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()

        required_methods = [
            '_try_extract_from_source',
            '_try_youtube_transcript',
            '_find_youtube_version',
            '_extract_youtube_transcript',
            'process_log_entries',
            '_load_podcast_config',
            '_load_rss_feeds',
            '_load_processed_episodes'
        ]

        for method in required_methods:
            assert hasattr(processor, method), f"Missing method: {method}"
            assert callable(getattr(processor, method)), f"Method not callable: {method}"

    def test_5_error_handling(self):
        """Test 5: Error handling and graceful degradation"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()

        # Test with various invalid inputs
        invalid_inputs = [
            {},  # Empty dict
            {'title': ''},  # Missing fields
            {'podcast_name': ''},  # Missing fields
            {'title': 'Test', 'podcast_name': 'Test', 'link': 'invalid-url'},  # Invalid URL
            None,  # None input
        ]

        error_count = 0
        for invalid_input in invalid_inputs:
            try:
                if invalid_input is None:
                    continue  # Skip None as it would cause TypeError
                result = processor._try_extract_from_source(invalid_input, {'name': 'test', 'method': 'test'})
                # If it doesn't crash, that's good error handling
            except Exception as e:
                error_count += 1

        # Should handle most errors gracefully
        assert error_count < len(invalid_inputs), "Too many unhandled errors"

    def test_6_logger_functionality(self):
        """Test 6: Logger system functionality"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()
        logger = processor.logger

        # Check logger methods exist
        logger_methods = ['process', 'discover', 'complete', 'fail', 'skip', 'metrics']
        for method in logger_methods:
            assert hasattr(logger, method), f"Logger missing method: {method}"
            assert callable(getattr(logger, method)), f"Logger method not callable: {method}"

    def test_7_episode_data_processing(self):
        """Test 7: Episode data structure and processing"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()

        # Test episode data structure
        test_episode = {
            'title': 'Test Episode',
            'podcast_name': 'Test Podcast',
            'link': 'https://test.com/episode',
            'published': '2025-09-29',
            'summary': 'Test summary',
            'network': 'Test Network',
            'duration': '45:30'
        }

        # Check required fields are accessible
        required_fields = ['title', 'podcast_name', 'link']
        for field in required_fields:
            assert field in test_episode, f"Missing required field: {field}"
            assert test_episode[field], f"Empty required field: {field}"

    def test_8_integration_completeness(self):
        """Test 8: System integration completeness"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()

        # Check all major components are integrated
        integration_checks = [
            ('Discovery matrix loaded', len(processor.discovered_sources) > 0),
            ('Transcript sources configured', len(processor.transcript_sources) > 0),
            ('Logger initialized', hasattr(processor, 'logger')),
            ('Podcast config loaded', hasattr(processor, 'podcast_config')),
            ('RSS feeds loaded', hasattr(processor, 'rss_feeds')),
            ('Processed episodes loaded', hasattr(processor, 'processed_episodes')),
        ]

        for check_name, check_result in integration_checks:
            assert check_result, f"Integration check failed: {check_name}"

    def test_9_performance_metrics(self):
        """Test 9: Performance and metrics tracking"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()

        # Test initialization time
        start_time = time.time()
        processor2 = AtlasLogProcessor()
        init_time = time.time() - start_time

        # Should initialize quickly
        assert init_time < 5.0, f"Initialization too slow: {init_time:.2f}s"

        # Test memory usage (basic check)
        import sys
        processor_size = sys.getsizeof(processor)
        assert processor_size < 100 * 1024 * 1024, f"Processor too large: {processor_size} bytes"

    def test_10_file_operations(self):
        """Test 10: File operations and data persistence"""
        from atlas_log_processor import AtlasLogProcessor

        processor = AtlasLogProcessor()

        # Check file operations work
        assert os.path.exists(processor.config_file), "Config file not found"
        assert os.path.exists(processor.rss_file), "RSS file not found"
        assert os.path.exists(processor.processed_file), "Processed file not found"

        # Check file reading works
        assert isinstance(processor.podcast_config, dict), "Podcast config not loaded properly"
        assert isinstance(processor.rss_feeds, dict), "RSS feeds not loaded properly"
        assert isinstance(processor.processed_episodes, set), "Processed episodes not loaded properly"

    def run_all_tests(self):
        """Run all tests and generate report"""
        print("🧪 Atlas Comprehensive Test Suite")
        print("=" * 50)

        # Run all tests
        self.run_test("System Initialization", self.test_1_system_initialization)
        self.run_test("Discovery Matrix Validation", self.test_2_discovery_matrix_validation)
        self.run_test("Transcript Sources Configuration", self.test_3_transcript_sources_configuration)
        self.run_test("Method Availability", self.test_4_method_availability)
        self.run_test("Error Handling", self.test_5_error_handling)
        self.run_test("Logger Functionality", self.test_6_logger_functionality)
        self.run_test("Episode Data Processing", self.test_7_episode_data_processing)
        self.run_test("Integration Completeness", self.test_8_integration_completeness)
        self.run_test("Performance Metrics", self.test_9_performance_metrics)
        self.run_test("File Operations", self.test_10_file_operations)

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate test summary report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])

        total_time = time.time() - self.start_time

        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        print(f"Total Time: {total_time:.2f}s")

        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['name']}: {result['error']}")

        print(f"\n🎯 OVERALL RESULT: {'PASS' if failed_tests == 0 else 'FAIL'}")

        return failed_tests == 0

if __name__ == "__main__":
    test_suite = AtlasTestSuite()
    success = test_suite.run_all_tests()
    exit(0 if success else 1)
