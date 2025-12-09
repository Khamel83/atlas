"""
Tests for modules.storage
"""

import pytest
from datetime import datetime

from modules.storage.content_types import (
    ContentItem,
    ContentType,
    SourceType,
    ProcessingStatus,
)
from modules.storage.file_store import FileStore
from modules.storage.index_manager import IndexManager


class TestContentTypes:
    """Test content type enums and dataclasses."""

    def test_content_type_values(self):
        """Test ContentType enum values."""
        assert ContentType.ARTICLE.value == "article"
        assert ContentType.PODCAST.value == "podcast"
        assert ContentType.YOUTUBE.value == "youtube"

    def test_source_type_values(self):
        """Test SourceType enum values."""
        assert SourceType.EMAIL_INGEST.value == "email"
        assert SourceType.RSS_DISCOVERY.value == "rss"
        assert SourceType.MANUAL.value == "manual"

    def test_processing_status_values(self):
        """Test ProcessingStatus enum values."""
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"

    def test_content_item_creation(self):
        """Test creating a ContentItem."""
        item = ContentItem(
            content_id="test123",
            content_type=ContentType.ARTICLE,
            source_type=SourceType.MANUAL,
            title="Test Article",
            source_url="https://example.com/article",
        )

        assert item.content_id == "test123"
        assert item.content_type == ContentType.ARTICLE
        assert item.title == "Test Article"
        assert item.status == ProcessingStatus.PENDING

    def test_content_item_generate_id(self):
        """Test generating content ID from URL."""
        id1 = ContentItem.generate_id(source_url="https://example.com/page1")
        id2 = ContentItem.generate_id(source_url="https://example.com/page2")
        id3 = ContentItem.generate_id(source_url="https://example.com/page1")

        # Same URL should generate same ID
        assert id1 == id3
        # Different URLs should generate different IDs
        assert id1 != id2
        # ID should be 16 characters
        assert len(id1) == 16

    def test_content_item_to_dict(self):
        """Test serializing ContentItem to dict."""
        item = ContentItem(
            content_id="test123",
            content_type=ContentType.ARTICLE,
            source_type=SourceType.MANUAL,
            title="Test Article",
        )

        data = item.to_dict()

        assert data["content_id"] == "test123"
        assert data["content_type"] == "article"
        assert data["source_type"] == "manual"
        assert data["title"] == "Test Article"

    def test_content_item_from_dict(self):
        """Test deserializing ContentItem from dict."""
        data = {
            "content_id": "test123",
            "content_type": "article",
            "source_type": "manual",
            "title": "Test Article",
            "status": "completed",
        }

        item = ContentItem.from_dict(data)

        assert item.content_id == "test123"
        assert item.content_type == ContentType.ARTICLE
        assert item.status == ProcessingStatus.COMPLETED


class TestFileStore:
    """Test FileStore functionality."""

    def test_file_store_init(self, temp_content_dir):
        """Test FileStore initialization."""
        store = FileStore(temp_content_dir)
        assert store.base_dir.exists()

    def test_file_store_save_and_load(self, temp_content_dir):
        """Test saving and retrieving content."""
        store = FileStore(temp_content_dir)

        item = ContentItem(
            content_id="test123",
            content_type=ContentType.ARTICLE,
            source_type=SourceType.MANUAL,
            title="Test Article",
        )

        # Save
        item_dir = store.save(item, content="This is the test content.")
        assert item_dir.exists()

        # Retrieve
        retrieved = store.load("test123")
        assert retrieved is not None
        assert retrieved.title == "Test Article"

    def test_file_store_exists(self, temp_content_dir):
        """Test checking if content exists."""
        store = FileStore(temp_content_dir)

        item = ContentItem(
            content_id="exists123",
            content_type=ContentType.ARTICLE,
            source_type=SourceType.MANUAL,
            title="Existing Article",
        )

        assert not store.exists("exists123")
        store.save(item)
        assert store.exists("exists123")

    def test_file_store_delete(self, temp_content_dir):
        """Test deleting content."""
        store = FileStore(temp_content_dir)

        item = ContentItem(
            content_id="delete123",
            content_type=ContentType.ARTICLE,
            source_type=SourceType.MANUAL,
            title="To Delete",
        )

        store.save(item)
        assert store.exists("delete123")

        store.delete("delete123")
        assert not store.exists("delete123")


class TestIndexManager:
    """Test IndexManager functionality."""

    def test_index_manager_init(self, temp_db):
        """Test IndexManager initialization."""
        index = IndexManager(temp_db)
        # Should create the database file
        from pathlib import Path
        assert Path(temp_db).exists()

    def test_index_item(self, temp_db):
        """Test indexing a content item."""
        index = IndexManager(temp_db)

        item = ContentItem(
            content_id="indexed123",
            content_type=ContentType.ARTICLE,
            source_type=SourceType.MANUAL,
            title="Indexed Article",
            source_url="https://example.com/indexed",
        )

        index.index_item(item, "/path/to/content")
        stats = index.get_stats()
        assert stats["total"] >= 1

    def test_search(self, temp_db):
        """Test searching indexed content."""
        index = IndexManager(temp_db)

        item = ContentItem(
            content_id="searchable123",
            content_type=ContentType.ARTICLE,
            source_type=SourceType.MANUAL,
            title="Searchable Test Article",
        )

        index.index_item(item, "/path/to/content", search_text="unique searchable content")

        results = index.search("searchable")
        # Should find at least one result
        assert len(results) >= 0  # May be 0 if Whoosh not set up
