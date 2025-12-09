"""
Pytest configuration and shared fixtures.
"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def temp_db(temp_dir):
    """Create a temporary database path."""
    return str(Path(temp_dir) / "test.db")


@pytest.fixture
def temp_content_dir(temp_dir):
    """Create a temporary content directory."""
    content_dir = Path(temp_dir) / "content"
    content_dir.mkdir(parents=True)
    return str(content_dir)
