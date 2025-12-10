import unittest
from unittest.mock import patch

from helpers.metadata_manager import (ContentMetadata, ContentType,
                                      MetadataManager)


class TestMetadataManager(unittest.TestCase):

    def setUp(self):
        self.config = {
            "data_directory": "output",
            "article_output_path": "output/articles",
            "podcast_output_path": "output/podcasts",
            "youtube_output_path": "output/youtube",
        }
        self.manager = MetadataManager(self.config)

    def test_create_metadata(self):
        metadata = self.manager.create_metadata(
            content_type=ContentType.ARTICLE,
            source="https://example.com",
            title="Test Article",
        )
        self.assertIsInstance(metadata, ContentMetadata)
        self.assertEqual(metadata.title, "Test Article")

    def test_save_and_load_metadata(self):
        metadata = self.manager.create_metadata(
            content_type=ContentType.ARTICLE,
            source="https://example.com",
            title="Test Article",
        )
        with patch("builtins.open", unittest.mock.mock_open()), patch(
            "json.dump"
        ), patch("os.path.exists", return_value=True), patch(
            "json.load", return_value=metadata.__dict__
        ):
            self.manager.save_metadata(metadata)
            loaded_metadata = self.manager.load_metadata(
                metadata.content_type, metadata.uid
            )
            # This is a simplified check. A real test would verify the content of the file.
            self.assertIsNotNone(loaded_metadata)


if __name__ == "__main__":
    unittest.main()
