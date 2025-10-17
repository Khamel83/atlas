"""
Search Engine Module

This module provides full-text search capabilities using Meilisearch for fast,
typo-tolerant search with intelligent ranking and filtering.
"""

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import meilisearch
    from meilisearch.client import Client
    from meilisearch.index import Index

    MEILISEARCH_AVAILABLE = True
except ImportError:
    meilisearch = None
    Client = None
    Index = None
    MEILISEARCH_AVAILABLE = False

from helpers.config import load_config
from helpers.metadata_manager import ContentType, MetadataManager
from helpers.path_manager import PathManager, PathType

logger = logging.getLogger(__name__)


class SearchConfig:
    """Configuration for search engine settings."""

    DEFAULT_SETTINGS = {
        "searchableAttributes": [
            "title",
            "content",
            "summary",
            "tags",
            "source",
            "author",
            "description",
            "podcast_name",
            "episode_title",
        ],
        "filterableAttributes": [
            "content_type",
            "tags",
            "source",
            "author",
            "created_at",
            "updated_at",
            "processing_status",
            "podcast_name",
            "podcast_slug",
            "duration",
            "publish_date",
        ],
        "sortableAttributes": [
            "created_at",
            "updated_at",
            "title",
            "relevance_score",
            "publish_date",
            "duration",
        ],
        "rankingRules": [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
        ],
        "stopWords": [
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "will",
            "with",
        ],
        "synonyms": {
            "javascript": ["js", "ecmascript"],
            "python": ["py"],
            "artificial intelligence": ["ai", "machine learning", "ml"],
            "tutorial": ["guide", "howto", "walkthrough"],
            "podcast": ["episode", "show", "interview"],
            "transcript": ["transcription", "text", "dialogue"],
            "documentation": ["docs", "reference", "manual"],
        },
        "typoTolerance": {
            "enabled": True,
            "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8},
        },
    }


class AtlasSearchEngine:
    """Full-text search engine using Meilisearch."""

    def __init__(
        self, config: Optional[Dict] = None, host: str = None, api_key: str = None
    ):
        """Initialize search engine with Meilisearch client."""
        if not MEILISEARCH_AVAILABLE:
            raise ImportError(
                "Meilisearch client not available. Install with: pip install meilisearch"
            )

        self.config = config or load_config()
        self.metadata_manager = MetadataManager()
        self.path_manager = PathManager(self.config)

        # Meilisearch connection settings
        self.host = host or self.config.get("meilisearch_host", "http://localhost:7700")
        self.api_key = api_key or self.config.get("meilisearch_api_key", None)
        self.index_name = self.config.get("meilisearch_index", "atlas_content")

        # Initialize client
        try:
            self.client = Client(self.host, self.api_key)
            self.index = self.client.index(self.index_name)
            logger.info(f"Connected to Meilisearch at {self.host}")
        except Exception as e:
            logger.error(f"Failed to connect to Meilisearch: {e}")
            raise

        # Search settings
        self.search_limit = self.config.get("search_limit", 50)
        self.index_batch_size = self.config.get("index_batch_size", 100)

    def health_check(self) -> Dict[str, Any]:
        """Check Meilisearch server health and connectivity."""
        try:
            health = self.client.health()
            stats = self.index.get_stats()

            return {
                "status": "healthy",
                "server_health": health,
                "index_stats": stats,
                "index_name": self.index_name,
                "host": self.host,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "host": self.host}

    def setup_index(self, reset: bool = False) -> bool:
        """Set up search index with proper configuration."""
        try:
            if reset:
                try:
                    self.client.delete_index(self.index_name)
                    logger.info(f"Deleted existing index: {self.index_name}")
                except Exception:
                    pass  # Index might not exist

                # Wait for deletion to complete
                time.sleep(1)

            # Create or get index
            try:
                self.index = self.client.create_index(
                    self.index_name, {"primaryKey": "uid"}
                )
                logger.info(f"Created new index: {self.index_name}")
            except Exception:
                self.index = self.client.index(self.index_name)
                logger.info(f"Using existing index: {self.index_name}")

            # Configure index settings
            settings = SearchConfig.DEFAULT_SETTINGS.copy()

            # Apply custom settings from config
            if "search_settings" in self.config:
                settings.update(self.config["search_settings"])

            self.index.update_settings(settings)
            logger.info("Applied search index settings")

            return True

        except Exception as e:
            logger.error(f"Failed to setup search index: {e}")
            return False

    def index_content(
        self,
        content_type: Optional[ContentType] = None,
        batch_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Index content from Atlas metadata for search."""
        batch_size = batch_size or self.index_batch_size

        result = {
            "indexed_count": 0,
            "error_count": 0,
            "errors": [],
            "content_types_processed": set(),
            "processing_time": 0,
        }

        start_time = time.time()

        try:
            # Get all metadata or filter by content type
            all_metadata = self.metadata_manager.get_all_metadata()

            if content_type:
                all_metadata = [
                    item
                    for item in all_metadata
                    if item.get("content_type") == content_type.value
                ]

            logger.info(f"Indexing {len(all_metadata)} items")

            # Process in batches
            documents = []

            for item in all_metadata:
                try:
                    search_doc = self._prepare_document_for_search(item)
                    if search_doc:
                        documents.append(search_doc)
                        result["content_types_processed"].add(
                            item.get("content_type", "unknown")
                        )

                        # Process batch when full
                        if len(documents) >= batch_size:
                            self._index_batch(documents, result)
                            documents = []

                except Exception as e:
                    result["error_count"] += 1
                    result["errors"].append(
                        f"Error preparing {item.get('uid', 'unknown')}: {str(e)}"
                    )
                    logger.warning(f"Error preparing document for indexing: {e}")

            # Process remaining documents
            if documents:
                self._index_batch(documents, result)

            result["processing_time"] = time.time() - start_time
            logger.info(
                f"Indexing completed: {result['indexed_count']} documents in {result['processing_time']:.2f}s"
            )

        except Exception as e:
            result["errors"].append(f"Fatal error during indexing: {str(e)}")
            logger.error(f"Fatal error during content indexing: {e}")

        result["content_types_processed"] = list(result["content_types_processed"])
        return result

    def _prepare_document_for_search(self, metadata: Dict) -> Optional[Dict]:
        """Prepare content metadata for search indexing."""
        if not metadata.get("uid"):
            return None

        # Read content files if available
        content_text = ""
        summary_text = metadata.get("summary", "")

        try:
            content_type_str = metadata.get("content_type", "article")
            content_type = ContentType(content_type_str)

            # Try to read markdown content
            path_set = self.path_manager.get_path_set(content_type, metadata["uid"])
            markdown_path = path_set.get_path(PathType.MARKDOWN)

            if markdown_path and os.path.exists(markdown_path):
                with open(markdown_path, "r", encoding="utf-8") as f:
                    content_text = f.read()
        except Exception:
            # If we can't read content, use summary or description
            content_text = summary_text or metadata.get("description", "")

        # Extract searchable tags
        tags = []
        if isinstance(metadata.get("tags"), list):
            tags = metadata["tags"]
        elif isinstance(metadata.get("tags"), str):
            tags = [tag.strip() for tag in metadata["tags"].split(",") if tag.strip()]

        # Create search document
        search_doc = {
            "uid": metadata["uid"],
            "title": metadata.get("title", ""),
            "content": content_text[:10000],  # Limit content length for indexing
            "summary": summary_text,
            "description": metadata.get("description", ""),
            "content_type": metadata.get("content_type", "unknown"),
            "url": metadata.get("url", ""),
            "source": metadata.get("source", ""),
            "author": metadata.get("author", ""),
            "tags": tags,
            "created_at": metadata.get("created_at", ""),
            "updated_at": metadata.get("updated_at", ""),
            "processing_status": metadata.get("processing_status", "unknown"),
            "relevance_score": self._calculate_relevance_score(metadata, content_text),
        }

        # Add type-specific fields
        if content_type_str == "youtube":
            search_doc["duration"] = metadata.get("duration", "")
            search_doc["channel"] = metadata.get("channel", "")
        elif content_type_str == "podcast":
            # Handle both legacy and new podcast metadata formats
            type_specific = metadata.get("type_specific", {})
            search_doc["podcast_name"] = type_specific.get(
                "podcast_name", metadata.get("podcast_title", "")
            )
            search_doc["podcast_slug"] = type_specific.get("podcast_slug", "")
            search_doc["episode_title"] = type_specific.get(
                "episode_title", metadata.get("title", "")
            )
            search_doc["duration"] = type_specific.get(
                "duration", metadata.get("duration", "")
            )
            search_doc["publish_date"] = type_specific.get(
                "publish_date", metadata.get("publish_date", "")
            )
            search_doc["episode_number"] = metadata.get("episode_number", "")

        return search_doc

    def _calculate_relevance_score(self, metadata: Dict, content: str) -> float:
        """Calculate relevance score for search ranking."""
        score = 1.0

        # Boost based on content quality indicators
        if metadata.get("title"):
            score += 0.3

        if content and len(content) > 500:
            score += 0.2

        if metadata.get("tags"):
            score += 0.2

        if metadata.get("author"):
            score += 0.1

        # Boost recent content slightly
        try:
            if metadata.get("created_at"):
                created = datetime.fromisoformat(
                    metadata["created_at"].replace("Z", "+00:00")
                )
                days_old = (datetime.now() - created.replace(tzinfo=None)).days
                if days_old < 30:
                    score += 0.2
                elif days_old < 90:
                    score += 0.1
        except Exception:
            pass

        return round(score, 2)

    def _index_batch(self, documents: List[Dict], result: Dict):
        """Index a batch of documents."""
        try:
            self.index.add_documents(documents)
            result["indexed_count"] += len(documents)
            logger.debug(f"Indexed batch of {len(documents)} documents")
        except Exception as e:
            result["error_count"] += len(documents)
            result["errors"].append(f"Batch indexing error: {str(e)}")
            logger.error(f"Error indexing batch: {e}")

    def search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Perform full-text search with optional filters and sorting."""
        limit = limit or self.search_limit

        search_params = {
            "limit": limit,
            "offset": offset,
            "attributesToHighlight": ["title", "content", "summary"],
            "cropLength": 200,
            "showMatchesPosition": True,
        }

        # Add filters
        if filters:
            filter_expressions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    # Multiple values (OR condition)
                    filter_expr = " OR ".join([f"{key} = '{v}'" for v in value])
                    filter_expressions.append(f"({filter_expr})")
                else:
                    filter_expressions.append(f"{key} = '{value}'")

            if filter_expressions:
                search_params["filter"] = " AND ".join(filter_expressions)

        # Add sorting
        if sort:
            search_params["sort"] = sort

        try:
            start_time = time.time()
            # Pass all parameters to the index search method
            results = self.index.search(query, search_params)
            search_time = time.time() - start_time

            # Process results
            processed_results = {
                "query": query,
                "hits": results.get("hits", []),
                "total_hits": results.get("estimatedTotalHits", 0),
                "processing_time_ms": results.get("processingTimeMs", 0),
                "search_time": round(search_time * 1000, 2),
                "limit": limit,
                "offset": offset,
                "facet_distribution": results.get("facetDistribution", {}),
                "has_more": results.get("estimatedTotalHits", 0) > (offset + limit),
            }

            return processed_results

        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "query": query,
                "hits": [],
                "total_hits": 0,
                "error": str(e),
                "search_time": 0,
            }

    def suggest(self, query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on indexed content."""
        try:
            # Use a broad search to find related terms
            results = self.search(query, limit=limit)

            suggestions = []
            for hit in results["hits"]:
                title = hit.get("title", "")
                if title and title.lower() not in [s.lower() for s in suggestions]:
                    suggestions.append(title)

                # Extract relevant terms from tags
                for tag in hit.get("tags", []):
                    if (
                        query.lower() in tag.lower()
                        and tag.lower() not in [s.lower() for s in suggestions]
                        and len(suggestions) < limit
                    ):
                        suggestions.append(tag)

            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Suggestion error: {e}")
            return []

    def get_facets(
        self, query: str = "", facet_attributes: Optional[List[str]] = None
    ) -> Dict:
        """Get faceted search results for filtering."""
        facet_attributes = facet_attributes or [
            "content_type",
            "tags",
            "source",
            "author",
        ]

        try:
            search_params = {
                "limit": 0,  # We only want facets
                "facets": facet_attributes,
            }

            results = self.index.search(query, search_params)
            return results.get("facetDistribution", {})

        except Exception as e:
            logger.error(f"Facet retrieval error: {e}")
            return {}

    def delete_document(self, uid: str) -> bool:
        """Delete a document from the search index."""
        try:
            self.index.delete_document(uid)
            return True
        except Exception as e:
            logger.error(f"Error deleting document {uid}: {e}")
            return False

    def update_document(self, uid: str) -> bool:
        """Update a single document in the search index."""
        try:
            # Get metadata for the item
            all_metadata = self.metadata_manager.get_all_metadata()
            item_metadata = None

            for item in all_metadata:
                if item.get("uid") == uid:
                    item_metadata = item
                    break

            if not item_metadata:
                logger.warning(f"No metadata found for UID: {uid}")
                return False

            # Prepare and index the document
            search_doc = self._prepare_document_for_search(item_metadata)
            if search_doc:
                self.index.add_documents([search_doc])
                return True
            else:
                logger.warning(f"Could not prepare document for UID: {uid}")
                return False

        except Exception as e:
            logger.error(f"Error updating document {uid}: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get search index statistics."""
        try:
            stats = self.index.get_stats()
            settings = self.index.get_settings()

            return {
                "index_stats": stats,
                "settings": settings,
                "index_name": self.index_name,
                "server_url": self.host,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}

    def clear_index(self) -> bool:
        """Clear all documents from the search index."""
        try:
            self.index.delete_all_documents()
            logger.info("Cleared all documents from search index")
            return True
        except Exception as e:
            logger.error(f"Error clearing index: {e}")
            return False


# Global search engine instance
_global_search_engine: Optional[AtlasSearchEngine] = None


def get_search_engine(config: Optional[Dict] = None) -> AtlasSearchEngine:
    """Get global search engine instance."""
    global _global_search_engine

    if not MEILISEARCH_AVAILABLE:
        raise ImportError(
            "Meilisearch not available. Install with: pip install meilisearch"
        )

    if _global_search_engine is None:
        _global_search_engine = AtlasSearchEngine(config)

    return _global_search_engine


def search_content(
    query: str, content_type: Optional[str] = None, limit: int = 20
) -> Dict[str, Any]:
    """Convenience function for content search."""
    try:
        search_engine = get_search_engine()

        filters = {}
        if content_type:
            filters["content_type"] = content_type

        return search_engine.search(query, filters=filters, limit=limit)

    except Exception as e:
        logger.error(f"Search convenience function error: {e}")
        return {"query": query, "hits": [], "total_hits": 0, "error": str(e)}


def is_search_available() -> bool:
    """Check if search functionality is available."""
    if not MEILISEARCH_AVAILABLE:
        return False

    try:
        search_engine = get_search_engine()
        health = search_engine.health_check()
        return health["status"] == "healthy"
    except Exception:
        return False
