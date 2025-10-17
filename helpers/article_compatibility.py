#!/usr/bin/env python3
"""
Article Processing Compatibility Layer

Provides backward compatibility during migration to unified ArticleManager.
Maintains existing interfaces while redirecting to new unified system.
"""

import warnings
from typing import Any, Dict, List, Optional
from helpers.utils import log_info


class ArticleProcessingCompat:
    """Compatibility layer for article processing migration."""

    def __init__(self):
        self._manager = None

    @property
    def manager(self):
        """Lazy load ArticleManager to avoid circular imports."""
        if self._manager is None:
            from helpers.article_manager import ArticleManager
            self._manager = ArticleManager()
        return self._manager

    def show_deprecation_warning(self, old_method: str, new_method: str = None):
        """Show deprecation warning for migrated functionality."""
        if new_method:
            message = f"{old_method} is deprecated, use ArticleManager.{new_method} instead"
        else:
            message = f"{old_method} is deprecated, use ArticleManager instead"

        warnings.warn(message, DeprecationWarning, stacklevel=3)


# Global compatibility instance
_compat = ArticleProcessingCompat()


# Legacy ArticleFetcher compatibility
class DeprecatedArticleFetcher:
    """Deprecated ArticleFetcher - use ArticleManager instead."""

    def __init__(self, config=None):
        _compat.show_deprecation_warning("ArticleFetcher.__init__", "ArticleManager.__init__")
        self.config = config

    def fetch_with_fallbacks(self, url: str, log_path: str = ""):
        """Legacy method - use ArticleManager.process_article instead."""
        _compat.show_deprecation_warning("fetch_with_fallbacks", "process_article")

        result = _compat.manager.process_article(url, log_path=log_path)

        # Convert to legacy FetchResult for backward compatibility
        from helpers.article_strategies import FetchResult
        return FetchResult(
            success=result.success,
            content=result.content,
            method=result.method,
            error=result.error,
            is_truncated=result.is_truncated,
            metadata=result.metadata,
            title=result.title,
            strategy=result.strategy
        )


# Legacy strategy functions
def fetch_article_direct(url: str, log_path: str = ""):
    """Legacy direct fetch function."""
    _compat.show_deprecation_warning("fetch_article_direct", "process_article with preferred_strategies=['direct']")

    result = _compat.manager.process_article(
        url,
        preferred_strategies=['direct'],
        log_path=log_path
    )

    return result.success, result.content, result.error


def fetch_article_with_auth(url: str, config: Dict[str, Any], log_path: str = ""):
    """Legacy authenticated fetch function."""
    _compat.show_deprecation_warning("fetch_article_with_auth", "process_article with preferred_strategies=['auth']")

    # Update manager config
    _compat.manager.config.update(config)

    result = _compat.manager.process_article(
        url,
        preferred_strategies=['auth'],
        log_path=log_path
    )

    return result.success, result.content, result.error


def fetch_article_wayback(url: str, log_path: str = ""):
    """Legacy Wayback Machine fetch function."""
    _compat.show_deprecation_warning("fetch_article_wayback", "process_article with preferred_strategies=['wayback_enhanced']")

    result = _compat.manager.process_article(
        url,
        preferred_strategies=['wayback_enhanced', 'wayback'],
        log_path=log_path
    )

    return result.success, result.content, result.error


def bulk_fetch_articles(urls: List[str], config: Dict[str, Any] = None, log_path: str = ""):
    """Legacy bulk fetch function."""
    _compat.show_deprecation_warning("bulk_fetch_articles", "bulk_process_articles")

    if config:
        _compat.manager.config.update(config)

    results = _compat.manager.bulk_process_articles(urls, log_path=log_path)

    # Convert to legacy format: list of (url, success, content, error) tuples
    legacy_results = []
    for url, result in results.items():
        legacy_results.append((url, result.success, result.content, result.error))

    return legacy_results


# ArticleIngestor compatibility
class ArticleIngestorCompat:
    """Compatibility wrapper for ArticleIngestor using ArticleManager."""

    def __init__(self, config):
        _compat.show_deprecation_warning("ArticleIngestor", "ArticleManager with content processing")
        self.config = config

    def process_urls(self, urls: List[str]) -> Dict[str, Any]:
        """Legacy process_urls method."""
        log_info("", f"Processing {len(urls)} URLs through compatibility layer")

        # Use ArticleManager for fetching
        results = _compat.manager.bulk_process_articles(urls)

        # Process each result through the original ArticleIngestor for content processing
        try:
            from helpers.article_ingestor import ArticleIngestor
            original_ingestor = ArticleIngestor(self.config)

            # Convert results to format expected by original ingestor
            processed_results = {"results": []}

            for url, result in results.items():
                if result.success:
                    # Let original ingestor handle content processing/metadata extraction
                    processed_result = original_ingestor._process_single_url(url, result.content)
                    processed_results["results"].append(processed_result)
                else:
                    # Add failed result
                    processed_results["results"].append({
                        "url": url,
                        "success": False,
                        "error": result.error,
                        "fetch_method": result.method
                    })

            return processed_results

        except ImportError:
            # Fallback if original ingestor not available
            processed_results = {"results": []}

            for url, result in results.items():
                processed_results["results"].append({
                    "url": url,
                    "success": result.success,
                    "content": result.content,
                    "title": result.title,
                    "error": result.error,
                    "fetch_method": result.method,
                    "metadata": result.metadata
                })

            return processed_results


# Module-level compatibility functions
def create_article_fetcher(config: Dict[str, Any] = None):
    """Create article fetcher with compatibility warning."""
    _compat.show_deprecation_warning("create_article_fetcher", "ArticleManager")
    return DeprecatedArticleFetcher(config)


def migrate_article_processing_code():
    """
    Utility to help migrate existing code to new ArticleManager.

    Returns a migration guide as a string.
    """
    guide = """
ARTICLE PROCESSING MIGRATION GUIDE
==================================

OLD CODE → NEW CODE

1. Basic fetching:
   OLD: fetcher = ArticleFetcher(config); result = fetcher.fetch_with_fallbacks(url, log_path)
   NEW: manager = ArticleManager(config); result = manager.process_article(url, log_path=log_path)

2. Bulk processing:
   OLD: results = bulk_fetch_articles(urls, config, log_path)
   NEW: results = manager.bulk_process_articles(urls, log_path=log_path)

3. Strategy-specific fetching:
   OLD: strategy = DirectFetchStrategy(); result = strategy.fetch(url, log_path)
   NEW: result = manager.process_article(url, preferred_strategies=['direct'], log_path=log_path)

4. Authentication:
   OLD: auth_strategy = PaywallAuthenticatedStrategy(config); result = auth_strategy.fetch(url, log_path)
   NEW: result = manager.process_article(url, preferred_strategies=['auth'], log_path=log_path)

5. Failed article recovery:
   OLD: [manual retry with different strategies]
   NEW: results = manager.recover_failed_articles(failed_urls, log_path=log_path)

6. Statistics tracking:
   OLD: [manual tracking]
   NEW: stats = manager.get_processing_stats()

KEY BENEFITS OF MIGRATION:
- Unified interface for all article processing
- Automatic strategy selection and fallback
- Built-in statistics and performance tracking
- Bulk processing with concurrency control
- Enhanced recovery for failed articles
- Configuration-driven strategy preferences

MIGRATION STEPS:
1. Replace ArticleFetcher imports with ArticleManager
2. Update method calls to use new interface
3. Remove manual strategy orchestration code
4. Add configuration for strategy preferences
5. Leverage new bulk processing and recovery features
6. Use built-in statistics for monitoring

COMPATIBILITY:
- Old code continues to work with deprecation warnings
- Gradual migration is supported
- Full backward compatibility maintained during transition
"""

    return guide


# Legacy imports for backward compatibility
# These allow existing "from helpers.article_xxx import ..." statements to work
def ArticleFetcher(config=None):
    """Legacy ArticleFetcher import compatibility."""
    return DeprecatedArticleFetcher(config)


# Import aliases for common legacy patterns
try:
    # Re-export commonly used classes with warnings
    from helpers.article_strategies import FetchResult, ContentAnalyzer

    def DirectFetchStrategy():
        _compat.show_deprecation_warning("DirectFetchStrategy", "process_article with preferred_strategies=['direct']")
        from helpers.article_strategies import DirectFetchStrategy as _DirectFetchStrategy
        return _DirectFetchStrategy()

    def PaywallAuthenticatedStrategy(config=None):
        _compat.show_deprecation_warning("PaywallAuthenticatedStrategy", "process_article with preferred_strategies=['auth']")
        try:
            from helpers.simple_auth_strategy import SimpleAuthStrategy
            return SimpleAuthStrategy(config)
        except ImportError:
            from helpers.article_strategies import PaywallAuthenticatedStrategy as _PaywallAuthenticatedStrategy
            return _PaywallAuthenticatedStrategy(config)

except ImportError:
    pass


if __name__ == "__main__":
    # Print migration guide
    print(migrate_article_processing_code())

    # Test compatibility layer
    print("\n" + "="*50)
    print("TESTING COMPATIBILITY LAYER")
    print("="*50)

    # Test legacy fetcher
    fetcher = ArticleFetcher()
    print(f"Created legacy fetcher: {fetcher}")

    # Test legacy functions
    print("\nTesting legacy functions...")
    success, content, error = fetch_article_direct("https://example.com")
    print(f"Direct fetch result: success={success}, error={error}")

    # Show statistics
    stats = _compat.manager.get_processing_stats()
    print(f"\nManager statistics: {stats.get('total_attempts', 0)} total attempts")