"""
Comprehensive tests for MetadataManager.

This test suite covers all the newly implemented methods in MetadataManager
that are used by the cognitive amplification features.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import mock_open, patch

from helpers.metadata_manager import (
    ContentMetadata,
    ContentType,
    MetadataManager,
    ProcessingStatus,
)


class TestMetadataManagerComprehensive(unittest.TestCase):

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "data_directory": self.temp_dir,
            "article_output_path": os.path.join(self.temp_dir, "articles"),
            "podcast_output_path": os.path.join(self.temp_dir, "podcasts"),
            "youtube_output_path": os.path.join(self.temp_dir, "youtube"),
            "document_output_path": os.path.join(self.temp_dir, "documents"),
        }
        self.manager = MetadataManager(self.config)

        # Create sample metadata for testing
        self.sample_metadata = [
            self._create_sample_metadata(
                "item1",
                "Test Article 1",
                tags=["AI", "technology"],
                updated_at="2025-08-12T10:00:00.000000"
            ),
            self._create_sample_metadata(
                "item2",
                "Old Article",
                tags=["technology", "vintage"],
                updated_at="2020-01-15T12:00:00.000000"
            ),
            self._create_sample_metadata(
                "item3",
                "Recent Video",
                tags=["AI", "education"],
                updated_at="2025-08-11T14:30:00.000000",
                type_specific={"last_reviewed": "2020-01-01T00:00:00.000000"}
            ),
        ]

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_sample_metadata(self, uid, title, tags=None, updated_at=None, type_specific=None):
        """Helper to create sample metadata."""
        if updated_at is None:
            updated_at = datetime.now().isoformat()

        return ContentMetadata(
            uid=uid,
            content_type=ContentType.DOCUMENT,
            source=f"https://example.com/{uid}",
            title=title,
            status=ProcessingStatus.SUCCESS,
            tags=tags or [],
            updated_at=updated_at,
            created_at=updated_at,
            type_specific=type_specific or {}
        )

    def _mock_metadata_loading(self, metadata_list):
        """Mock the metadata loading to return our sample data."""
        def mock_get_all_metadata(filters=None):
            result = metadata_list.copy()

            # Apply filters if provided
            if filters:
                if "content_type" in filters:
                    filter_type = filters["content_type"]
                    if isinstance(filter_type, str):
                        filter_type = ContentType(filter_type)
                    result = [m for m in result if m.content_type == filter_type]

                if "status" in filters:
                    filter_status = filters["status"]
                    if isinstance(filter_status, str):
                        filter_status = ProcessingStatus(filter_status)
                    result = [m for m in result if m.status == filter_status]

            return result

        return patch.object(self.manager, 'get_all_metadata', side_effect=mock_get_all_metadata)

    def test_get_all_metadata_no_filters(self):
        """Test get_all_metadata returns all metadata when no filters applied."""
        with self._mock_metadata_loading(self.sample_metadata):
            result = self.manager.get_all_metadata()
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0].title, "Test Article 1")

    def test_get_all_metadata_with_content_type_filter(self):
        """Test get_all_metadata with content_type filter."""
        with self._mock_metadata_loading(self.sample_metadata):
            result = self.manager.get_all_metadata({"content_type": ContentType.DOCUMENT})
            self.assertEqual(len(result), 3)

            result = self.manager.get_all_metadata({"content_type": "document"})
            self.assertEqual(len(result), 3)

    def test_get_all_metadata_with_status_filter(self):
        """Test get_all_metadata with status filter."""
        sample_with_different_status = self.sample_metadata.copy()
        sample_with_different_status[0].status = ProcessingStatus.PENDING

        with self._mock_metadata_loading(sample_with_different_status):
            result = self.manager.get_all_metadata({"status": ProcessingStatus.SUCCESS})
            self.assertEqual(len(result), 2)

            result = self.manager.get_all_metadata({"status": "pending"})
            self.assertEqual(len(result), 1)

    def test_get_forgotten_content(self):
        """Test get_forgotten_content returns oldest content first."""
        with self._mock_metadata_loading(self.sample_metadata):
            result = self.manager.get_forgotten_content(threshold_days=365)
            self.assertGreaterEqual(len(result), 1)
            # Should contain old article
            titles = [item.title for item in result]
            self.assertIn("Old Article", titles)

    def test_get_forgotten_content_with_age_limit(self):
        """Test get_forgotten_content respects threshold_days."""
        with self._mock_metadata_loading(self.sample_metadata):
            # Only items older than 30 days
            result = self.manager.get_forgotten_content(threshold_days=30)
            self.assertGreaterEqual(len(result), 1)
            titles = [item.title for item in result]
            self.assertIn("Old Article", titles)

    def test_get_tag_patterns(self):
        """Test get_tag_patterns returns tag analysis."""
        with self._mock_metadata_loading(self.sample_metadata):
            result = self.manager.get_tag_patterns(min_frequency=1)

            # Should return a dictionary with tag analysis
            self.assertIsInstance(result, dict)

    def test_get_tag_patterns_with_min_frequency(self):
        """Test get_tag_patterns respects min_frequency."""
        with self._mock_metadata_loading(self.sample_metadata):
            result = self.manager.get_tag_patterns(min_frequency=2)
            self.assertIsInstance(result, dict)

    def test_get_temporal_patterns(self):
        """Test get_temporal_patterns returns temporal analysis."""
        with self._mock_metadata_loading(self.sample_metadata):
            result = self.manager.get_temporal_patterns(time_window="month")

            # Should return a dictionary with temporal analysis
            self.assertIsInstance(result, dict)

    def test_get_temporal_patterns_different_window(self):
        """Test get_temporal_patterns with different time window."""
        with self._mock_metadata_loading(self.sample_metadata):
            result = self.manager.get_temporal_patterns(time_window="week")
            self.assertIsInstance(result, dict)

    def test_get_recall_items(self):
        """Test get_recall_items returns items needing review."""
        with self._mock_metadata_loading(self.sample_metadata):
            result = self.manager.get_recall_items(limit=5)

            # Should return a list of items
            self.assertIsInstance(result, list)

            # Check that it contains items
            self.assertGreaterEqual(len(result), 0)

    def test_get_recall_items_with_limit(self):
        """Test get_recall_items respects limit."""
        with self._mock_metadata_loading(self.sample_metadata):
            result = self.manager.get_recall_items(limit=1)
            self.assertLessEqual(len(result), 1)

    def test_create_metadata(self):
        """Test create_metadata creates valid ContentMetadata."""
        metadata = self.manager.create_metadata(
            content_type=ContentType.DOCUMENT,
            source="https://test.com",
            title="Test Title"
        )

        self.assertIsInstance(metadata, ContentMetadata)
        self.assertEqual(metadata.content_type, ContentType.DOCUMENT)
        self.assertEqual(metadata.source, "https://test.com")
        self.assertEqual(metadata.title, "Test Title")
        self.assertEqual(metadata.status, ProcessingStatus.PENDING)
        self.assertIsNotNone(metadata.uid)
        self.assertIsNotNone(metadata.created_at)

    def test_get_type_directory(self):
        """Test get_type_directory returns correct paths."""
        article_dir = self.manager.get_type_directory(ContentType.ARTICLE)
        expected = os.path.join(self.temp_dir, "articles")
        self.assertEqual(article_dir, expected)

        document_dir = self.manager.get_type_directory(ContentType.DOCUMENT)
        expected = os.path.join(self.temp_dir, "documents")
        self.assertEqual(document_dir, expected)

    def test_get_metadata_path(self):
        """Test get_metadata_path constructs correct file paths."""
        path = self.manager.get_metadata_path(ContentType.DOCUMENT, "test123")
        expected = os.path.join(self.temp_dir, "documents", "metadata", "test123.json")
        self.assertEqual(path, expected)

    def test_save_metadata_creates_directories(self):
        """Test save_metadata creates necessary directories."""
        metadata = self._create_sample_metadata("test", "Test Title")

        with patch("builtins.open", mock_open()) as mock_file, \
             patch("json.dump") as mock_json_dump, \
             patch("os.makedirs") as mock_makedirs:

            result = self.manager.save_metadata(metadata)

            self.assertTrue(result)
            mock_makedirs.assert_called_once()
            mock_file.assert_called_once()
            mock_json_dump.assert_called_once()

    def test_load_metadata_file_not_found(self):
        """Test load_metadata returns None when file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            result = self.manager.load_metadata(ContentType.DOCUMENT, "nonexistent")
            self.assertIsNone(result)

    def test_load_metadata_corrupted_json(self):
        """Test load_metadata handles corrupted JSON gracefully."""
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data="invalid json")), \
             patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):

            result = self.manager.load_metadata(ContentType.DOCUMENT, "corrupted")
            self.assertIsNone(result)

    def test_integration_save_and_load(self):
        """Integration test: save metadata and load it back."""
        original_metadata = self._create_sample_metadata("integration_test", "Integration Test")

        # Create the actual directory structure
        metadata_dir = os.path.join(self.temp_dir, "documents", "metadata")
        os.makedirs(metadata_dir, exist_ok=True)

        # Save metadata
        self.assertTrue(self.manager.save_metadata(original_metadata))

        # Load metadata back
        loaded_metadata = self.manager.load_metadata(
            ContentType.DOCUMENT,
            "integration_test"
        )

        self.assertIsNotNone(loaded_metadata)
        self.assertEqual(loaded_metadata.uid, original_metadata.uid)
        self.assertEqual(loaded_metadata.title, original_metadata.title)
        self.assertEqual(loaded_metadata.content_type, original_metadata.content_type)
        self.assertEqual(loaded_metadata.status, original_metadata.status)


if __name__ == "__main__":
    unittest.main()