"""
Pytest configuration and shared fixtures for Atlas v4 testing.
"""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import MagicMock

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from atlas.config import AtlasConfig, VaultConfig, LoggingConfig

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp(prefix="atlas_test_"))
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config() -> AtlasConfig:
    """Create a sample Atlas configuration for testing."""
    return AtlasConfig(
        vault=VaultConfig(root="./test_vault"),
        logging=LoggingConfig(level="DEBUG", enable_console=False)
    )


@pytest.fixture
def config_file(temp_dir: Path, sample_config: AtlasConfig) -> Path:
    """Create a temporary configuration file."""
    config_path = temp_dir / "test_config.yaml"

    # Create basic config file
    config_content = """
version: "4.0.0"

vault:
  root: "./test_vault"
  inbox_dir: "inbox"
  logs_dir: "logs"
  failures_dir: "failures"

logging:
  level: "DEBUG"
  enable_console: false

processing:
  max_concurrent_jobs: 2
  timeout_seconds: 60
  retry_attempts: 1
"""

    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_rss_content() -> str:
    """Sample RSS feed content for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Podcast</title>
        <description>A test podcast for Atlas</description>
        <link>https://example.com/podcast</link>
        <language>en</language>
        <item>
            <title>Test Episode 1</title>
            <description>This is a test episode description with enough content to be valid.</description>
            <link>https://example.com/episode1</link>
            <pubDate>Mon, 16 Oct 2024 12:00:00 GMT</pubDate>
            <guid>episode1-12345</guid>
            <enclosure url="https://example.com/episode1.mp3" type="audio/mpeg" length="1000000" />
        </item>
        <item>
            <title>Test Episode 2</title>
            <description>Another test episode with different content for testing deduplication.</description>
            <link>https://example.com/episode2</link>
            <pubDate>Tue, 17 Oct 2024 14:30:00 GMT</pubDate>
            <guid>episode2-67890</guid>
            <enclosure url="https://example.com/episode2.mp3" type="audio/mpeg" length="1500000" />
        </item>
    </channel>
</rss>"""


@pytest.fixture
def sample_article_content() -> str:
    """Sample article content for testing."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Test Article: Atlas Development</title>
    <meta name="author" content="Test Author">
    <meta name="description" content="A test article about Atlas development">
    <meta property="article:published_time" content="2024-10-16T12:00:00Z">
</head>
<body>
    <article>
        <h1>Building Atlas v4</h1>
        <p>This is a comprehensive test article about building Atlas v4, the personal knowledge automation system. It contains multiple paragraphs to ensure it meets the minimum content requirements for validation testing.</p>

        <h2>Core Principles</h2>
        <p>Atlas follows the philosophy of simplicity over complexity. Each module is designed to be under 300 lines of code and focus on doing one thing well. This approach ensures maintainability and reliability.</p>

        <h2>Architecture</h2>
        <p>The system is built with independent ingestion modules that can run standalone. Content is stored as Markdown+YAML files, making it compatible with Obsidian and other knowledge management tools.</p>

        <p>This article provides sufficient content length for testing the ingestion and validation pipeline. It includes proper structure and metadata that would be found in a real article.</p>
    </article>
</body>
</html>
"""


@pytest.fixture
def sample_content_item() -> Dict[str, Any]:
    """Sample content item data structure."""
    return {
        "id": "test-article-2024-10-16",
        "type": "article",
        "source": "test-source",
        "title": "Test Article: Atlas Development",
        "date": "2024-10-16T12:00:00Z",
        "author": "Test Author",
        "url": "https://example.com/test-article",
        "content_hash": "abcd1234567890abcd1234567890abcd1234567890abcd1234567890abcd1234",
        "tags": ["test", "atlas", "development"],
        "ingested_at": "2024-10-16T12:30:00Z",
        "content": "# Test Article: Atlas Development\n\nThis is the content of the test article..."
    }


@pytest.fixture
def mock_requests_response():
    """Create a mock requests Response object."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.text = "<html><body>Test content</body></html>"
    mock_response.content = b"<html><body>Test content</body></html>"
    mock_response.headers = {"Content-Type": "text/html"}
    return mock_response


@pytest.fixture
def vault_structure(temp_dir: Path) -> Path:
    """Create a sample vault directory structure."""
    vault_path = temp_dir / "vault"

    # Create vault structure
    (vault_path / "inbox" / "newsletters" / "2024" / "10").mkdir(parents=True)
    (vault_path / "inbox" / "podcasts" / "2024" / "10").mkdir(parents=True)
    (vault_path / "inbox" / "articles" / "2024" / "10").mkdir(parents=True)
    (vault_path / "inbox" / "youtube" / "2024" / "10").mkdir(parents=True)
    (vault_path / "inbox" / "emails" / "2024" / "10").mkdir(parents=True)
    (vault_path / "logs").mkdir(parents=True)
    (vault_path / "failures").mkdir(parents=True)

    return vault_path


@pytest.fixture(autouse=True)
def cleanup_env(monkeypatch):
    """Clean up environment variables for tests."""
    # Clear potentially problematic environment variables
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_USER_ID", raising=False)
    monkeypatch.delenv("ATLAS_CONFIG", raising=False)


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock()
