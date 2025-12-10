import os
from unittest.mock import MagicMock, patch

import pytest

from helpers.metadata_manager import ContentType
from helpers.podcast_ingestor import PodcastIngestor


@pytest.fixture
def dummy_config(tmp_path):
    return {
        "data_directory": str(tmp_path),
        "podcast_output_path": os.path.join(str(tmp_path), "podcasts"),
        "run_transcription": False,
    }


@pytest.fixture
def ingestor(dummy_config):
    ingestor = PodcastIngestor(dummy_config)
    ingestor.path_manager.type_directories[ContentType.PODCAST] = dummy_config[
        "podcast_output_path"
    ]
    return ingestor


def test_initialization(ingestor):
    assert ingestor.config is not None
    assert hasattr(ingestor, "error_handler")


@patch("feedparser.parse")
def test_process_feed_success(mock_parse, ingestor):
    mock_feed = MagicMock()
    mock_feed.entries = [MagicMock()]
    mock_parse.return_value = mock_feed
    with patch.object(
        ingestor, "process_content", return_value=True
    ) as mock_process_content:
        ingestor.process_feed("http://example.com/feed")
        mock_process_content.assert_called_once()
