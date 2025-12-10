import os
from unittest.mock import MagicMock, patch

import pytest

from helpers.instapaper_ingestor import InstapaperIngestor


@pytest.fixture
def dummy_config(tmp_path):
    return {
        "data_directory": str(tmp_path),
        "article_output_path": os.path.join(str(tmp_path), "articles"),
        "INSTAPAPER_LOGIN": "user",
        "INSTAPAPER_PASSWORD": "pass",
    }


@pytest.fixture
def ingestor(dummy_config):
    return InstapaperIngestor(dummy_config)


def test_initialization(ingestor):
    assert ingestor.config is not None
    assert hasattr(ingestor, "error_handler")
    assert hasattr(ingestor, "login")
    assert hasattr(ingestor, "password")
    assert hasattr(ingestor, "meta_save_dir")
    assert hasattr(ingestor, "md_save_dir")
    assert hasattr(ingestor, "html_save_dir")
    assert hasattr(ingestor, "log_path")


def test_missing_credentials(tmp_path):
    config = {
        "data_directory": str(tmp_path),
        "article_output_path": os.path.join(str(tmp_path), "articles"),
    }
    ingestor = InstapaperIngestor(config)
    with patch("helpers.instapaper_ingestor.log_error") as mock_log_error:
        ingestor.ingest_articles()
        mock_log_error.assert_called_with(
            ingestor.log_path,
            "Instapaper credentials not found in .env file. Skipping.",
        )


@patch("helpers.instapaper_ingestor.sync_playwright")
def test_ingest_articles_playwright_error(mock_playwright, ingestor):
    mock_playwright.side_effect = Exception("Playwright error")
    with patch.object(ingestor.error_handler, "handle_error") as mock_handle_error:
        ingestor.ingest_articles()
        mock_handle_error.assert_called_once()


@patch("helpers.instapaper_ingestor.sync_playwright")
def test_ingest_articles_success(mock_playwright, ingestor):
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = (
        mock_browser
    )
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_page.locator.return_value.all.return_value = []
    ingestor.ingest_articles()
    mock_page.goto.assert_called_with(
        "https://www.instapaper.com/user/login", timeout=60000
    )
    mock_page.fill.assert_any_call('input[name="username"]', "user")
    mock_page.fill.assert_any_call('input[name="password"]', "pass")
    mock_page.click.assert_called_with('button[type="submit"]')
    mock_page.wait_for_url.assert_called_with(
        "https://www.instapaper.com/u", timeout=60000
    )
