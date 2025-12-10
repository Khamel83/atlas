from unittest.mock import patch

import pytest

from helpers.base_ingestor import BaseIngestor
from helpers.metadata_manager import ContentType


class TestIngestor(BaseIngestor):
    def get_content_type(self) -> ContentType:
        return ContentType.ARTICLE

    def get_module_name(self) -> str:
        return "test_ingestor"

    def fetch_content(self, source, metadata):
        if "error" in source:
            return False, "Test error"
        return True, "Test content"

    def process_content(self, content, metadata):
        return True


@pytest.fixture
def config():
    return {
        "data_directory": "output",
        "article_output_path": "output/articles",
    }


@pytest.fixture
def ingestor(config):
    return TestIngestor(config, ContentType.ARTICLE, "test_ingestor")


def test_ingest_single_success(ingestor):
    result = ingestor.ingest_single("http://test.com/page")
    assert result.success
    assert result.metadata.title is None


def test_ingest_single_error(ingestor):
    result = ingestor.ingest_single("http://test.com/error")
    assert not result.success
    assert result.error == "Test error"


def test_batch_ingest(ingestor):
    sources = ["http://test.com/1", "http://test.com/2"]
    results = ingestor.ingest_batch(sources)
    assert len(results) == 2
    assert results["http://test.com/1"].success
    assert results["http://test.com/2"].success


@patch("helpers.base_ingestor.log_info")
def test_batch_ingest_logs(mock_log_info, ingestor):
    sources = ["http://test.com/1", "http://test.com/2"]
    ingestor.ingest_batch(sources)
    assert mock_log_info.call_count == 3


@patch("helpers.base_ingestor.log_error")
def test_handle_error_logs(mock_log_error, ingestor):
    ingestor.handle_error("Test error", "http://test.com/error")
    assert mock_log_error.call_count == 1
