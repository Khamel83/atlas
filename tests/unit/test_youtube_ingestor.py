import os
import unittest.mock
from unittest.mock import MagicMock, patch

import pytest

from helpers.metadata_manager import ContentType
from helpers.youtube_ingestor import YouTubeIngestor


@pytest.fixture
def dummy_config(tmp_path):
    return {
        "data_directory": str(tmp_path),
        "youtube_output_path": os.path.join(str(tmp_path), "youtube"),
    }


@pytest.fixture
def ingestor(dummy_config):
    ingestor = YouTubeIngestor(dummy_config)
    ingestor.path_manager.type_directories[ContentType.YOUTUBE] = dummy_config[
        "youtube_output_path"
    ]
    return ingestor


def test_initialization(ingestor):
    assert ingestor.config is not None
    assert hasattr(ingestor, "error_handler")


@patch("helpers.youtube_ingestor.YouTube")
@patch("helpers.youtube_ingestor.YouTubeTranscriptApi")
def test_ingest_single_video_success(mock_transcript, mock_youtube, ingestor):
    mock_yt_instance = MagicMock()
    mock_yt_instance.title = "Test Video"
    mock_yt_instance.streams.filter.return_value.order_by.return_value.desc.return_value.first.return_value.download.return_value = (
        None
    )
    mock_youtube.return_value = mock_yt_instance
    mock_transcript.get_transcript.return_value = [{"text": "test"}]

    with patch("builtins.open", unittest.mock.mock_open()):
        result = ingestor.ingest_single_video("https://www.youtube.com/watch?v=test")
        assert result
