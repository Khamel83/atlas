from unittest.mock import Mock, patch

import pytest

from helpers.metadata_manager import ContentType
from helpers.search_engine import (MEILISEARCH_AVAILABLE, AtlasSearchEngine,
                                   SearchConfig, get_search_engine,
                                   is_search_available, search_content)

# Skip all tests if Meilisearch is not available
pytestmark = pytest.mark.skipif(
    not MEILISEARCH_AVAILABLE, reason="Meilisearch not available"
)


class TestSearchConfig:
    """Test SearchConfig class."""

    def test_default_settings(self):
        """Test default search configuration."""
        settings = SearchConfig.DEFAULT_SETTINGS

        assert "searchableAttributes" in settings
        assert "title" in settings["searchableAttributes"]
        assert "content" in settings["searchableAttributes"]

        assert "filterableAttributes" in settings
        assert "content_type" in settings["filterableAttributes"]

        assert "rankingRules" in settings
        assert "words" in settings["rankingRules"]

        assert "typoTolerance" in settings
        assert settings["typoTolerance"]["enabled"] is True


@pytest.mark.skipif(not MEILISEARCH_AVAILABLE, reason="Meilisearch not available")
class TestAtlasSearchEngine:
    """Test AtlasSearchEngine class methods."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return {
            "meilisearch_host": "http://test-host:7700",
            "meilisearch_api_key": "test_key",
            "meilisearch_index": "test_index",
            "search_limit": 25,
            "index_batch_size": 50,
        }

    @pytest.fixture
    def mock_meilisearch_client(self):
        """Create mock Meilisearch client."""
        client = Mock()
        index = Mock()

        client.index.return_value = index
        client.health.return_value = {"status": "available"}

        index.get_stats.return_value = {
            "numberOfDocuments": 100,
            "isIndexing": False,
            "fieldDistribution": {},
        }

        return client, index

    @pytest.fixture
    def search_engine(self, mock_config, mock_meilisearch_client):
        """Create AtlasSearchEngine instance with mocked dependencies."""
        client, index = mock_meilisearch_client

        with patch("helpers.search_engine.Client", return_value=client), patch(
            "helpers.search_engine.MetadataManager"
        ) as mock_mm, patch("helpers.search_engine.PathManager") as mock_pm:

            mock_mm.return_value = Mock()
            mock_pm.return_value = Mock()

            engine = AtlasSearchEngine(mock_config)
            engine.index = index  # Set the mock index directly
            return engine

    def test_init(self, mock_config):
        """Test search engine initialization."""
        with patch("helpers.search_engine.Client") as mock_client, patch(
            "helpers.search_engine.MetadataManager"
        ) as mock_mm, patch("helpers.search_engine.PathManager") as mock_pm:

            mock_client_instance = Mock()
            mock_index = Mock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.index.return_value = mock_index

            mock_mm.return_value = Mock()
            mock_pm.return_value = Mock()

            engine = AtlasSearchEngine(mock_config)

            assert engine.host == "http://test-host:7700"
            assert engine.api_key == "test_key"
            assert engine.index_name == "test_index"
            assert engine.search_limit == 25
            assert engine.index_batch_size == 50

    def test_init_with_defaults(self):
        """Test initialization with default configuration."""
        with patch("helpers.search_engine.load_config") as mock_load_config, patch(
            "helpers.search_engine.Client"
        ) as mock_client, patch(
            "helpers.search_engine.MetadataManager"
        ) as mock_mm, patch(
            "helpers.search_engine.PathManager"
        ) as mock_pm:

            mock_load_config.return_value = {}
            mock_client_instance = Mock()
            mock_index = Mock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.index.return_value = mock_index

            mock_mm.return_value = Mock()
            mock_pm.return_value = Mock()

            engine = AtlasSearchEngine()

            assert engine.host == "http://localhost:7700"
            assert engine.api_key is None
            assert engine.index_name == "atlas_content"

    def test_health_check_healthy(self, search_engine):
        """Test health check when service is healthy."""
        search_engine.client.health.return_value = {"status": "available"}
        search_engine.index.get_stats.return_value = {"numberOfDocuments": 100}

        health = search_engine.health_check()

        assert health["status"] == "healthy"
        assert "server_health" in health
        assert "index_stats" in health

    def test_health_check_unhealthy(self, search_engine):
        """Test health check when service is unhealthy."""
        search_engine.client.health.side_effect = Exception("Connection failed")

        health = search_engine.health_check()

        assert health["status"] == "unhealthy"
        assert "error" in health

    def test_setup_index_new(self, search_engine):
        """Test setting up a new search index."""
        search_engine.client.create_index.return_value = Mock()

        result = search_engine.setup_index(reset=False)

        assert result is True
        search_engine.index.update_settings.assert_called_once()

    def test_setup_index_reset(self, search_engine):
        """Test setting up index with reset."""
        search_engine.client.delete_index.return_value = Mock()
        search_engine.client.create_index.return_value = Mock()

        result = search_engine.setup_index(reset=True)

        assert result is True
        search_engine.client.delete_index.assert_called_once_with("test_index")

    def test_setup_index_error(self, search_engine):
        """Test setup index with error."""
        search_engine.client.create_index.side_effect = Exception("Setup failed")
        search_engine.client.index.side_effect = Exception("Index access failed")

        result = search_engine.setup_index()

        assert result is False

    def test_prepare_document_for_search(self, search_engine):
        """Test preparing metadata for search indexing."""
        metadata = {
            "uid": "test_uid",
            "title": "Test Article",
            "summary": "This is a test summary",
            "content_type": "article",
            "url": "https://example.com/test",
            "tags": ["python", "testing"],
            "author": "Test Author",
            "created_at": "2024-01-01T00:00:00Z",
        }

        # Mock path manager to return no file
        path_set = Mock()
        path_set.get_path.return_value = None
        search_engine.path_manager.get_path_set.return_value = path_set

        doc = search_engine._prepare_document_for_search(metadata)

        assert doc is not None
        assert doc["uid"] == "test_uid"
        assert doc["title"] == "Test Article"
        assert doc["content_type"] == "article"
        assert doc["tags"] == ["python", "testing"]
        assert "relevance_score" in doc

    def test_prepare_document_with_content_file(self, search_engine, tmp_path):
        """Test preparing document with content file."""
        # Create test content file
        content_file = tmp_path / "test_content.md"
        content_file.write_text("# Test Content\n\nThis is test markdown content.")

        metadata = {
            "uid": "test_uid",
            "title": "Test Article",
            "content_type": "article",
        }

        # Mock path manager to return the test file
        path_set = Mock()
        path_set.get_path.return_value = str(content_file)
        search_engine.path_manager.get_path_set.return_value = path_set

        doc = search_engine._prepare_document_for_search(metadata)

        assert doc is not None
        assert "Test Content" in doc["content"]
        assert "test markdown content" in doc["content"]

    def test_prepare_document_no_uid(self, search_engine):
        """Test preparing document without UID."""
        metadata = {"title": "No UID"}

        doc = search_engine._prepare_document_for_search(metadata)

        assert doc is None

    def test_calculate_relevance_score(self, search_engine):
        """Test relevance score calculation."""
        # Metadata with all quality indicators
        good_metadata = {
            "title": "Good Article",
            "tags": ["python"],
            "author": "Author Name",
            "created_at": "2024-01-01T00:00:00Z",
        }

        good_content = (
            "This is a long piece of content that exceeds 500 characters. " * 10
        )

        score = search_engine._calculate_relevance_score(good_metadata, good_content)

        assert score > 1.0  # Should have boosts

        # Metadata with minimal information
        basic_metadata = {}
        basic_content = "Short content"

        basic_score = search_engine._calculate_relevance_score(
            basic_metadata, basic_content
        )

        assert basic_score == 1.0  # Base score only
        assert score > basic_score

    def test_index_content(self, search_engine):
        """Test content indexing."""
        mock_metadata = [
            {"uid": "item1", "title": "Article 1", "content_type": "article"},
            {"uid": "item2", "title": "Article 2", "content_type": "article"},
        ]

        search_engine.metadata_manager.get_all_metadata.return_value = mock_metadata
        search_engine.index.add_documents.return_value = Mock()

        # Mock path manager
        path_set = Mock()
        path_set.get_path.return_value = None
        search_engine.path_manager.get_path_set.return_value = path_set

        result = search_engine.index_content()

        assert result["indexed_count"] == 2
        assert result["error_count"] == 0
        assert "article" in result["content_types_processed"]

    def test_index_content_with_filter(self, search_engine):
        """Test content indexing with content type filter."""
        mock_metadata = [
            {"uid": "article1", "content_type": "article"},
            {"uid": "youtube1", "content_type": "youtube"},
        ]

        search_engine.metadata_manager.get_all_metadata.return_value = mock_metadata
        search_engine.index.add_documents.return_value = Mock()

        # Mock path manager
        path_set = Mock()
        path_set.get_path.return_value = None
        search_engine.path_manager.get_path_set.return_value = path_set

        result = search_engine.index_content(ContentType.ARTICLE)

        assert result["indexed_count"] == 1  # Only article should be indexed
        assert "article" in result["content_types_processed"]
        assert "youtube" not in result["content_types_processed"]

    def test_search_basic(self, search_engine):
        """Test basic search functionality."""
        mock_search_results = {
            "hits": [
                {"uid": "item1", "title": "Test Article", "content": "Content here"},
                {"uid": "item2", "title": "Another Article", "content": "More content"},
            ],
            "estimatedTotalHits": 2,
            "processingTimeMs": 5,
            "facetDistribution": {},
        }

        search_engine.index.search.return_value = mock_search_results

        result = search_engine.search("test query")

        assert result["query"] == "test query"
        assert len(result["hits"]) == 2
        assert result["total_hits"] == 2
        assert "search_time" in result

    def test_search_with_filters(self, search_engine):
        """Test search with filters."""
        search_engine.index.search.return_value = {
            "hits": [],
            "estimatedTotalHits": 0,
            "processingTimeMs": 1,
        }

        filters = {"content_type": "article", "tags": ["python", "tutorial"]}

        search_engine.search("test", filters=filters)

        # Verify search was called with proper filter syntax
        search_engine.index.search.assert_called_once()
        call_args = search_engine.index.search.call_args
        search_params = call_args[1]

        assert "filter" in search_params
        filter_expr = search_params["filter"]
        assert "content_type = 'article'" in filter_expr
        assert "tags = 'python' OR tags = 'tutorial'" in filter_expr

    def test_search_with_sorting(self, search_engine):
        """Test search with sorting."""
        search_engine.index.search.return_value = {
            "hits": [],
            "estimatedTotalHits": 0,
            "processingTimeMs": 1,
        }

        search_engine.search("test", sort=["created_at:desc"])

        # Verify sort parameter was passed
        search_params = search_engine.index.search.call_args[1]
        assert search_params["sort"] == ["created_at:desc"]

    def test_search_error(self, search_engine):
        """Test search with error."""
        search_engine.index.search.side_effect = Exception("Search failed")

        result = search_engine.search("test query")

        assert "error" in result
        assert result["hits"] == []
        assert result["total_hits"] == 0

    def test_suggest(self, search_engine):
        """Test search suggestions."""
        mock_search_results = {
            "hits": [
                {"title": "Python Tutorial", "tags": ["python", "programming"]},
                {"title": "Advanced Python", "tags": ["python", "advanced"]},
            ]
        }

        search_engine.index.search.return_value = mock_search_results

        suggestions = search_engine.suggest("python")

        assert len(suggestions) > 0
        assert "Python Tutorial" in suggestions or "python" in suggestions

    def test_get_facets(self, search_engine):
        """Test getting faceted search results."""
        mock_facets = {
            "content_type": {"article": 50, "youtube": 30},
            "tags": {"python": 25, "javascript": 15},
        }

        search_engine.index.search.return_value = {"facetDistribution": mock_facets}

        facets = search_engine.get_facets("test query")

        assert facets == mock_facets

    def test_delete_document(self, search_engine):
        """Test deleting document from index."""
        search_engine.index.delete_document.return_value = Mock()

        result = search_engine.delete_document("test_uid")

        assert result is True
        search_engine.index.delete_document.assert_called_once_with("test_uid")

    def test_delete_document_error(self, search_engine):
        """Test delete document with error."""
        search_engine.index.delete_document.side_effect = Exception("Delete failed")

        result = search_engine.delete_document("test_uid")

        assert result is False

    def test_update_document(self, search_engine):
        """Test updating document in index."""
        mock_metadata = [
            {"uid": "test_uid", "title": "Updated Article", "content_type": "article"}
        ]

        search_engine.metadata_manager.get_all_metadata.return_value = mock_metadata
        search_engine.index.add_documents.return_value = Mock()

        # Mock path manager
        path_set = Mock()
        path_set.get_path.return_value = None
        search_engine.path_manager.get_path_set.return_value = path_set

        result = search_engine.update_document("test_uid")

        assert result is True

    def test_update_document_not_found(self, search_engine):
        """Test updating non-existent document."""
        search_engine.metadata_manager.get_all_metadata.return_value = []

        result = search_engine.update_document("nonexistent_uid")

        assert result is False

    def test_get_stats(self, search_engine):
        """Test getting index statistics."""
        mock_stats = {"numberOfDocuments": 100, "isIndexing": False}
        mock_settings = {"searchableAttributes": ["title", "content"]}

        search_engine.index.get_stats.return_value = mock_stats
        search_engine.index.get_settings.return_value = mock_settings

        stats = search_engine.get_stats()

        assert stats["index_stats"] == mock_stats
        assert stats["settings"] == mock_settings
        assert "index_name" in stats

    def test_clear_index(self, search_engine):
        """Test clearing search index."""
        search_engine.index.delete_all_documents.return_value = Mock()

        result = search_engine.clear_index()

        assert result is True
        search_engine.index.delete_all_documents.assert_called_once()


@pytest.mark.skipif(not MEILISEARCH_AVAILABLE, reason="Meilisearch not available")
class TestGlobalFunctions:
    """Test module-level global functions."""

    @patch("helpers.search_engine._global_search_engine", None)
    def test_get_search_engine(self):
        """Test getting global search engine instance."""
        with patch("helpers.search_engine.AtlasSearchEngine") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            # First call should create instance
            result1 = get_search_engine()
            assert result1 == mock_instance
            mock_class.assert_called_once()

            # Second call should return same instance
            result2 = get_search_engine()
            assert result2 == mock_instance
            # Should not create another instance
            mock_class.assert_called_once()

    def test_search_content(self):
        """Test convenience search function."""
        with patch("helpers.search_engine.get_search_engine") as mock_get:
            mock_engine = Mock()
            mock_engine.search.return_value = {
                "query": "test",
                "hits": [],
                "total_hits": 0,
            }
            mock_get.return_value = mock_engine

            result = search_content("test", content_type="article", limit=10)

            assert result["query"] == "test"
            mock_engine.search.assert_called_once_with(
                "test", filters={"content_type": "article"}, limit=10
            )

    def test_search_content_error(self):
        """Test search content with error."""
        with patch("helpers.search_engine.get_search_engine") as mock_get:
            mock_get.side_effect = Exception("Engine failed")

            result = search_content("test")

            assert "error" in result
            assert result["hits"] == []

    def test_is_search_available_true(self):
        """Test search availability check when available."""
        with patch("helpers.search_engine.get_search_engine") as mock_get:
            mock_engine = Mock()
            mock_engine.health_check.return_value = {"status": "healthy"}
            mock_get.return_value = mock_engine

            assert is_search_available() is True

    def test_is_search_available_false(self):
        """Test search availability check when unavailable."""
        with patch("helpers.search_engine.get_search_engine") as mock_get:
            mock_engine = Mock()
            mock_engine.health_check.return_value = {"status": "unhealthy"}
            mock_get.return_value = mock_engine

            assert is_search_available() is False

    def test_is_search_available_exception(self):
        """Test search availability check with exception."""
        with patch("helpers.search_engine.get_search_engine") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            assert is_search_available() is False


# Test when Meilisearch is not available
class TestMeilisearchUnavailable:
    """Test behavior when Meilisearch is not available."""

    @patch("helpers.search_engine.MEILISEARCH_AVAILABLE", False)
    def test_search_engine_import_error(self):
        """Test AtlasSearchEngine raises ImportError when Meilisearch unavailable."""
        with pytest.raises(ImportError, match="Meilisearch client not available"):
            AtlasSearchEngine()

    @patch("helpers.search_engine.MEILISEARCH_AVAILABLE", False)
    def test_get_search_engine_import_error(self):
        """Test get_search_engine raises ImportError when unavailable."""
        with pytest.raises(ImportError, match="Meilisearch not available"):
            get_search_engine()

    @patch("helpers.search_engine.MEILISEARCH_AVAILABLE", False)
    def test_is_search_available_false_no_meilisearch(self):
        """Test is_search_available returns False when Meilisearch unavailable."""
        assert is_search_available() is False
