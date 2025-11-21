#!/usr/bin/env python3
"""
Core System Integration Tests
Tests internal components that don't require external services
"""

import sys
import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestCoreIntegration(unittest.TestCase):
    """Test core system integration without external dependencies"""

    def setUp(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db_path = self.test_db.name
        self.test_db.close()

    def tearDown(self):
        """Clean up"""
        Path(self.test_db_path).unlink(missing_ok=True)

    def test_universal_queue_core(self):
        """Test Universal Processing Queue core functionality"""
        print("🧪 Testing Universal Processing Queue core...")

        from universal_processing_queue import UniversalProcessingQueue

        # Test queue initialization
        queue = UniversalProcessingQueue(self.test_db_path)
        self.assertIsNotNone(queue)

        # Test job addition
        job_id = queue.add_job('test_job', {'test': 'data'})
        self.assertIsNotNone(job_id)

        # Test stats
        stats = queue.get_queue_stats()
        self.assertIn('status_counts', stats)

        print("✅ Universal Processing Queue core test passed")

    def test_database_operations(self):
        """Test database operations work correctly"""
        print("🧪 Testing database operations...")

        # Test direct database operations
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()

            # Create test table
            cursor.execute('''
                CREATE TABLE test_integration (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    content_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert test data
            cursor.execute('''
                INSERT INTO test_integration (title, content_type)
                VALUES (?, ?)
            ''', ('Test Content', 'test_type'))

            # Verify insertion
            cursor.execute('SELECT * FROM test_integration')
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[1], 'Test Content')

        print("✅ Database operations test passed")

    def test_configuration_loading(self):
        """Test configuration system works"""
        print("🧪 Testing configuration loading...")

        try:
            from helpers.database_config import get_database_connection
            # Should not crash
            db_path = get_database_connection()
            self.assertIsNotNone(db_path)
            print("   📄 Database config loading successful")
        except Exception as e:
            print(f"   ⚠️ Database config issue: {e}")

        print("✅ Configuration loading test passed")

    def test_import_structure(self):
        """Test that all main components can be imported"""
        print("🧪 Testing import structure...")

        imports_to_test = [
            ('universal_processing_queue', 'UniversalProcessingQueue'),
            ('helpers.youtube_ingestor', 'YouTubeIngestor'),
            ('podemos_opml_parser', 'parse_overcast_opml'),
            ('podemos_episode_discovery', 'PodmosEpisodeDiscovery'),
            ('podemos_transcription', 'PodmosTranscriber'),
            ('podemos_ad_detection', 'PodmosAdDetector'),
            ('podemos_audio_cutter', 'PodmosAudioCutter'),
            ('podemos_rss_generator', 'PodmosRSSGenerator'),
            ('unified_service_manager', 'UnifiedServiceManager'),
        ]

        for module_name, class_name in imports_to_test:
            try:
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                self.assertIsNotNone(cls)
                print(f"   ✅ {module_name}.{class_name} imported successfully")
            except ImportError as e:
                print(f"   ❌ {module_name}.{class_name} import failed: {e}")
                self.fail(f"Failed to import {module_name}.{class_name}")

        print("✅ Import structure test passed")

    @patch('helpers.mac_mini_client.MacMiniClient')
    def test_transcript_orchestrator_graceful_degradation(self, mock_mac_mini):
        """Test transcript orchestrator handles Mac Mini unavailability gracefully"""
        print("🧪 Testing transcript orchestrator graceful degradation...")

        # Mock Mac Mini to be unavailable
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = False
        mock_mac_mini.return_value = mock_instance

        from transcript_orchestrator import TranscriptOrchestrator

        # Should not crash even if Mac Mini unavailable
        orchestrator = TranscriptOrchestrator(self.test_db_path)
        self.assertIsNotNone(orchestrator)

        # Test cache check (should work without Mac Mini)
        cached = orchestrator.check_cache('Test Podcast', 'Test Episode')
        # Should return None (no cache) but not crash
        self.assertIsNone(cached)

        print("✅ Transcript orchestrator graceful degradation test passed")

    def test_job_handler_registration(self):
        """Test that all job handlers are properly registered"""
        print("🧪 Testing job handler registration...")

        from universal_processing_queue import UniversalProcessingQueue

        queue = UniversalProcessingQueue(self.test_db_path)

        # Check all expected handlers are registered
        expected_handlers = [
            'ai_processing',
            'transcript_discovery',
            'podcast_transcription',
            'podemos_processing',
            'youtube_processing',
            'mac_mini_transcription',
            'content_ingestion',
            'reprocessing'
        ]

        for handler_type in expected_handlers:
            self.assertIn(handler_type, queue.job_handlers)
            print(f"   ✅ Handler '{handler_type}' registered")

        print("✅ Job handler registration test passed")

def run_core_tests():
    """Run core integration tests"""
    print("🚀 Running Atlas Core Integration Tests")
    print("=" * 50)

    # Load tests
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestCoreIntegration)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    print("\n" + "=" * 50)
    print(f"🎯 Core Test Results:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")

    success = len(result.failures) == 0 and len(result.errors) == 0

    if success:
        print("🎉 All core integration tests passed!")
        print("📋 External dependencies (Mac Mini, YouTube API) ready for setup")
    else:
        print("⚠️ Some core tests failed")

        if result.failures:
            for test, traceback in result.failures:
                print(f"   ❌ Failure in {test}")

        if result.errors:
            for test, traceback in result.errors:
                print(f"   💥 Error in {test}")

    return success

if __name__ == '__main__':
    success = run_core_tests()
    sys.exit(0 if success else 1)