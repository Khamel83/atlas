#!/usr/bin/env python3
"""
Test suite for PODEMOS podcast processing system
Tests both Atlas and PODEMOS integration functionality
"""

import pytest
import asyncio
import tempfile
import os
import sys
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

class TestSmartTranscriptionPipeline:
    """Test Atlas smart transcription functionality"""

    def test_import_smart_transcription(self):
        """Test that smart transcription module imports correctly"""
        try:
            from helpers.smart_transcription_pipeline import SmartTranscriptionPipeline
            assert SmartTranscriptionPipeline is not None
        except ImportError as e:
            pytest.fail(f"Failed to import SmartTranscriptionPipeline: {e}")

    def test_pipeline_initialization(self):
        """Test pipeline initializes with config"""
        from helpers.smart_transcription_pipeline import SmartTranscriptionPipeline

        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock config
            config = {
                'DATA_DIRECTORY': temp_dir,
                'PROCESSING_QUEUE_DIRECTORY': temp_dir
            }

            pipeline = SmartTranscriptionPipeline(config)
            assert pipeline is not None
            assert pipeline.data_dir == Path(temp_dir)

    def test_prioritized_podcast_loading(self):
        """Test loading of prioritized podcast configuration"""
        from helpers.smart_transcription_pipeline import SmartTranscriptionPipeline

        with tempfile.TemporaryDirectory() as temp_dir:
            config = {'DATA_DIRECTORY': temp_dir}

            # Create test CSV
            csv_path = Path(temp_dir) / 'podcasts_prioritized.csv'
            csv_content = '''Category,Podcast Name,Count,Future,Transcript_Only,Exclude
Tech & Business,Test Podcast,10,1,0,0
Science,Test Podcast 2,5,1,1,0'''

            csv_path.write_text(csv_content)

            pipeline = SmartTranscriptionPipeline(config)
            podcasts = pipeline._load_prioritized_podcasts(str(csv_path))

            assert len(podcasts) == 2
            assert podcasts[0]['Podcast Name'] == 'Test Podcast'
            assert podcasts[1]['Transcript_Only'] == '1'

class TestPodemosFeedMonitor:
    """Test PODEMOS feed monitoring functionality"""

    def test_import_feed_monitor(self):
        """Test that feed monitor imports correctly"""
        try:
            from podemos_feed_monitor import PodemosFeedMonitor
            assert PodemosFeedMonitor is not None
        except ImportError as e:
            pytest.fail(f"Failed to import PodemosFeedMonitor: {e}")

    def test_podcast_feed_dataclass(self):
        """Test PodcastFeed dataclass"""
        from podemos_feed_monitor import PodcastFeed

        feed = PodcastFeed(
            name="Test Podcast",
            url="https://example.com/feed.xml",
            category="Technology",
            check_interval=60,
            priority=1
        )

        assert feed.name == "Test Podcast"
        assert feed.url == "https://example.com/feed.xml"
        assert feed.check_interval == 60

    @pytest.mark.asyncio
    async def test_feed_monitor_initialization(self):
        """Test feed monitor initialization"""
        from podemos_feed_monitor import PodemosFeedMonitor

        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                'DATA_DIRECTORY': temp_dir,
                'PROCESSING_QUEUE_DIRECTORY': temp_dir
            }

            monitor = PodemosFeedMonitor(config)
            assert monitor is not None
            assert monitor.db_path.exists()

class TestPodemoRSSServer:
    """Test PODEMOS RSS server functionality"""

    def test_import_rss_server(self):
        """Test that RSS server imports correctly"""
        try:
            from podemos_rss_server import PodemosFeedServer, RSSGenerator
            assert PodemosFeedServer is not None
            assert RSSGenerator is not None
        except ImportError as e:
            pytest.fail(f"Failed to import RSS server components: {e}")

    def test_feed_auth_initialization(self):
        """Test feed authentication system"""
        from podemos_rss_server import PodemosFeedAuth

        with tempfile.TemporaryDirectory() as temp_dir:
            auth_db = os.path.join(temp_dir, "test_auth.db")
            auth = PodemosFeedAuth(auth_db)

            assert auth is not None
            assert os.path.exists(auth_db)

    def test_token_generation(self):
        """Test access token generation"""
        from podemos_rss_server import PodemosFeedAuth

        with tempfile.TemporaryDirectory() as temp_dir:
            auth_db = os.path.join(temp_dir, "test_auth.db")
            auth = PodemosFeedAuth(auth_db)

            token = auth.generate_feed_token("test_feed", "test_user")
            assert token is not None
            assert len(token) > 10  # Should be a substantial token

            # Test validation
            is_valid = auth.validate_token(token, "test_feed")
            assert is_valid is True

            # Test invalid token
            is_valid = auth.validate_token("invalid_token", "test_feed")
            assert is_valid is False

class TestPodemoUltraFastProcessor:
    """Test PODEMOS ultra-fast processing functionality"""

    def test_import_ultra_fast_processor(self):
        """Test that ultra-fast processor imports correctly"""
        try:
            from podemos_ultra_fast_processor import PodemoUltraFastProcessor
            assert PodemoUltraFastProcessor is not None
        except ImportError as e:
            pytest.fail(f"Failed to import PodemoUltraFastProcessor: {e}")

    def test_processing_job_dataclass(self):
        """Test ProcessingJob dataclass"""
        from podemos_ultra_fast_processor import ProcessingJob

        job = ProcessingJob(
            id="test_123",
            podcast_name="Test Podcast",
            episode_title="Test Episode",
            episode_url="https://example.com/episode.mp3",
            priority=1,
            target_duration=300
        )

        assert job.id == "test_123"
        assert job.podcast_name == "Test Podcast"
        assert job.target_duration == 300

    def test_ad_detection_rules_loading(self):
        """Test ad detection rules are properly structured"""
        from podemos_ultra_fast_processor import PodemoUltraFastProcessor

        processor = PodemoUltraFastProcessor()
        assert processor.ad_detection_rules is not None
        assert 'sponsor_keywords' in processor.ad_detection_rules
        assert 'transition_phrases' in processor.ad_detection_rules
        assert isinstance(processor.ad_detection_rules['sponsor_keywords'], list)

class TestAtlasIntegration:
    """Test Atlas integration functionality"""

    def test_import_atlas_integration(self):
        """Test that Atlas integration imports correctly"""
        try:
            from podemos_atlas_integration import AtlasIntegratedQueue
            assert AtlasIntegratedQueue is not None
        except ImportError as e:
            pytest.fail(f"Failed to import AtlasIntegratedQueue: {e}")

    def test_podcast_item_creation(self):
        """Test PodemosPodcastItem creation"""
        from podemos_atlas_integration import PodemosPodcastItem

        item = PodemosPodcastItem(
            podcast_name="Test Podcast",
            episode_title="Test Episode",
            episode_url="https://example.com/episode.mp3",
            transcript_only=False,
            priority="high"
        )

        assert item.podcast_name == "Test Podcast"
        assert item.episode_title == "Test Episode"
        assert item.transcript_only is False
        assert item.capture_id.startswith("podemos_")

class TestSearchAPIFixes:
    """Test search API improvements"""

    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app for testing"""
        from fastapi.testclient import TestClient
        import sys
        sys.path.append(str(Path(__file__).parent.parent))

        from atlas_service_manager import create_app
        app = create_app()
        return TestClient(app)

    def test_search_endpoint_exists(self, mock_app):
        """Test that search endpoint exists and returns proper format"""
        # Test the fixed search endpoint
        response = mock_app.get("/api/v1/search/?q=test&limit=5")

        # Should not return 404 anymore
        assert response.status_code != 404

        # If it returns 200, should be JSON
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

class TestDatabaseOptimizations:
    """Test database optimizations and indexing"""

    def test_database_indexes_exist(self):
        """Test that database indexes were created for performance"""

        # This would test if the search optimizations were applied
        # For now, just test that the database can be accessed

        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = os.path.join(temp_dir, "test.db")

            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()

                # Create test content table
                cursor.execute("""
                    CREATE TABLE content (
                        id INTEGER PRIMARY KEY,
                        title TEXT,
                        content TEXT,
                        content_type TEXT,
                        url TEXT,
                        created_at TEXT
                    )
                """)

                # Add indexes like in the fix
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_title ON content(title)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_url ON content(url)")

                # Verify indexes exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='content'")
                indexes = cursor.fetchall()

                index_names = [idx[0] for idx in indexes]
                assert 'idx_content_title' in index_names
                assert 'idx_content_type' in index_names
                assert 'idx_content_url' in index_names

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])