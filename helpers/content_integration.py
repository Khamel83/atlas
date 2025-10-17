#!/usr/bin/env python3
"""
Content Processing Integration Layer

Provides integration between ContentPipeline and existing Atlas content processing
components, ensuring backward compatibility while leveraging the new unified system.
"""

import warnings
from typing import Any, Dict, List, Optional, Union
from helpers.utils import log_info, log_error


class ContentIntegration:
    """Integration layer for unified content processing."""

    def __init__(self):
        self._pipeline = None
        self._article_manager = None

    @property
    def pipeline(self):
        """Lazy load ContentPipeline."""
        if self._pipeline is None:
            from helpers.content_pipeline import ContentPipeline
            self._pipeline = ContentPipeline()
        return self._pipeline

    @property
    def article_manager(self):
        """Lazy load ArticleManager."""
        if self._article_manager is None:
            from helpers.article_manager import ArticleManager
            self._article_manager = ArticleManager()
        return self._article_manager


# Global integration instance
_integration = ContentIntegration()


def process_article_with_pipeline(url: str, config: Dict[str, Any] = None, log_path: str = ""):
    """
    Process article through complete ArticleManager + ContentPipeline workflow.

    Args:
        url: Article URL to process
        config: Configuration for processing
        log_path: Path for logging

    Returns:
        Tuple of (article_result, content_result)
    """
    log_info(log_path, f"Processing article with full pipeline: {url}")

    # Update configs if provided
    if config:
        _integration.article_manager.config.update(config)
        _integration.pipeline.config.update(config)

    # Step 1: Fetch article content
    article_result = _integration.article_manager.process_article(url, log_path=log_path)

    if not article_result.success:
        log_error(log_path, f"Article fetching failed: {article_result.error}")
        return article_result, None

    # Step 2: Process content through pipeline
    content_result = _integration.pipeline.process_content(
        content=article_result.content,
        title=article_result.title,
        url=url,
        log_path=log_path
    )

    log_info(log_path, f"Article processing complete: fetch={article_result.method}, pipeline={len(content_result.processing_stages)} stages")

    return article_result, content_result


def bulk_process_articles_with_pipeline(urls: List[str], config: Dict[str, Any] = None, log_path: str = ""):
    """
    Bulk process articles through complete workflow.

    Args:
        urls: List of article URLs
        config: Configuration for processing
        log_path: Path for logging

    Returns:
        List of (article_result, content_result) tuples
    """
    log_info(log_path, f"Bulk processing {len(urls)} articles with full pipeline")

    results = []

    # Update configs if provided
    if config:
        _integration.article_manager.config.update(config)
        _integration.pipeline.config.update(config)

    # Step 1: Bulk fetch articles
    article_results = _integration.article_manager.bulk_process_articles(urls, log_path=log_path)

    # Step 2: Process successful articles through content pipeline
    successful_articles = [
        (url, result) for url, result in article_results.items()
        if result.success
    ]

    if successful_articles:
        content_items = [
            {
                'content': result.content,
                'title': result.title,
                'url': url
            }
            for url, result in successful_articles
        ]

        content_results = _integration.pipeline.bulk_process_content(content_items, log_path=log_path)

        # Combine results
        content_dict = {item['url']: result for item, result in zip(content_items, content_results)}

        for url, article_result in article_results.items():
            content_result = content_dict.get(url) if article_result.success else None
            results.append((article_result, content_result))
    else:
        # No successful articles to process through pipeline
        for url, article_result in article_results.items():
            results.append((article_result, None))

    success_count = sum(1 for ar, cr in results if ar.success and cr is not None)
    log_info(log_path, f"Bulk processing complete: {success_count}/{len(urls)} fully successful")

    return results


# Legacy compatibility functions
def enhanced_article_processing(url: str, config: Dict[str, Any] = None):
    """Legacy enhanced article processing function."""
    warnings.warn(
        "enhanced_article_processing is deprecated, use process_article_with_pipeline",
        DeprecationWarning,
        stacklevel=2
    )

    article_result, content_result = process_article_with_pipeline(url, config)

    # Return in legacy format
    return {
        'success': article_result.success,
        'url': url,
        'content': article_result.content,
        'title': article_result.title,
        'method': article_result.method,
        'error': article_result.error,
        'classification': content_result.classification if content_result else None,
        'summary': content_result.summary if content_result else None,
        'quality_score': content_result.quality_score if content_result else 0.0
    }


def process_content_comprehensive(content: str, title: str = None, url: str = None, config: Dict[str, Any] = None):
    """Legacy comprehensive content processing."""
    warnings.warn(
        "process_content_comprehensive is deprecated, use ContentPipeline.process_content",
        DeprecationWarning,
        stacklevel=2
    )

    if config:
        _integration.pipeline.config.update(config)

    result = _integration.pipeline.process_content(content=content, title=title, url=url)

    # Return in legacy format
    return {
        'processed_content': result.processed_content or result.content,
        'classification': result.classification,
        'summary': result.summary,
        'topics': result.topics,
        'quality_score': result.quality_score,
        'metadata': result.metadata
    }


# Integration with existing ingestors
class EnhancedArticleIngestor:
    """Enhanced ArticleIngestor using unified processing."""

    def __init__(self, config):
        self.config = config
        warnings.warn(
            "EnhancedArticleIngestor is deprecated, integrate ArticleManager + ContentPipeline directly",
            DeprecationWarning,
            stacklevel=2
        )

    def process_urls(self, urls: List[str]) -> Dict[str, Any]:
        """Process URLs through enhanced pipeline."""
        results = bulk_process_articles_with_pipeline(urls, self.config)

        # Convert to expected format
        processed_results = {
            "timestamp": _integration.pipeline.stats.last_updated,
            "total_urls": len(urls),
            "processed": [],
            "failed": [],
            "results": []
        }

        for article_result, content_result in results:
            if article_result.success:
                processed_results["processed"].append(article_result.url)

                result_item = {
                    "url": article_result.url,
                    "success": True,
                    "title": article_result.title,
                    "fetch_method": article_result.method,
                    "processing_time": article_result.processing_time,
                    "content_length": len(article_result.content) if article_result.content else 0
                }

                if content_result:
                    result_item.update({
                        "classification": content_result.classification,
                        "summary": content_result.summary,
                        "topics": content_result.topics,
                        "quality_score": content_result.quality_score,
                        "pipeline_stages": len(content_result.processing_stages),
                        "pipeline_success": any(s.success for s in content_result.processing_stages)
                    })

                processed_results["results"].append(result_item)
            else:
                processed_results["failed"].append(article_result.url)
                processed_results["results"].append({
                    "url": article_result.url,
                    "success": False,
                    "error": article_result.error,
                    "fetch_method": article_result.method
                })

        return processed_results


# Content processing component integration
class UnifiedContentProcessor:
    """Unified processor combining all content processing capabilities."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def process_article_url(self, url: str, **kwargs):
        """Process article from URL through complete pipeline."""
        return process_article_with_pipeline(url, self.config, **kwargs)

    def process_raw_content(self, content: str, **kwargs):
        """Process raw content through pipeline."""
        if self.config:
            _integration.pipeline.config.update(self.config)

        return _integration.pipeline.process_content(content=content, **kwargs)

    def bulk_process_urls(self, urls: List[str], **kwargs):
        """Bulk process URLs through complete pipeline."""
        return bulk_process_articles_with_pipeline(urls, self.config, **kwargs)

    def bulk_process_content(self, content_items: List[Dict], **kwargs):
        """Bulk process content through pipeline."""
        if self.config:
            _integration.pipeline.config.update(self.config)

        return _integration.pipeline.bulk_process_content(content_items, **kwargs)

    def get_processing_stats(self):
        """Get combined processing statistics."""
        article_stats = _integration.article_manager.get_processing_stats()
        pipeline_stats = _integration.pipeline.get_pipeline_stats()

        return {
            'article_processing': article_stats,
            'content_pipeline': pipeline_stats,
            'integration_stats': {
                'components_loaded': {
                    'article_manager': _integration._article_manager is not None,
                    'content_pipeline': _integration._pipeline is not None
                }
            }
        }

    def reset_all_stats(self):
        """Reset all processing statistics."""
        _integration.article_manager.reset_stats()
        _integration.pipeline.reset_stats()
        log_info("", "All processing statistics reset")


# Migration helpers
def migrate_to_unified_processing():
    """
    Migration guide for moving to unified processing.

    Returns migration instructions as string.
    """
    guide = """
UNIFIED CONTENT PROCESSING MIGRATION GUIDE
=========================================

The new unified system combines ArticleManager + ContentPipeline for complete content processing.

MIGRATION PATTERNS:

1. Simple article processing:
   OLD: ingestor = ArticleIngestor(config); ingestor.process_content(url, metadata)
   NEW: article_result, content_result = process_article_with_pipeline(url, config)

2. Bulk article processing:
   OLD: ingestor.process_urls(urls)
   NEW: results = bulk_process_articles_with_pipeline(urls, config)

3. Content-only processing:
   OLD: processor = ContentProcessor(config); processor.process(content)
   NEW: pipeline = ContentPipeline(config); result = pipeline.process_content(content)

4. Enhanced processing with all features:
   OLD: [multiple separate components]
   NEW: processor = UnifiedContentProcessor(config); result = processor.process_article_url(url)

KEY BENEFITS:
- Single unified interface
- Automatic article fetching + content processing
- Built-in statistics and monitoring
- Configurable pipeline stages
- Bulk processing optimization
- Enhanced error handling and recovery

CONFIGURATION:
- All existing config options supported
- New pipeline-specific options available
- Backward compatibility maintained

COMPONENTS UNIFIED:
- ArticleManager: Handles article fetching with multiple strategies
- ContentPipeline: Handles content processing through configurable stages
- ContentIntegration: Combines both with compatibility layer

GRADUAL MIGRATION:
- Legacy interfaces still work with deprecation warnings
- New and old code can coexist
- Statistics tracking across both systems
- Full backward compatibility during transition
"""

    return guide


def create_unified_processor(config: Dict[str, Any] = None) -> UnifiedContentProcessor:
    """Factory function for creating unified processor."""
    return UnifiedContentProcessor(config)


# Export commonly used functions
__all__ = [
    'process_article_with_pipeline',
    'bulk_process_articles_with_pipeline',
    'UnifiedContentProcessor',
    'create_unified_processor',
    'migrate_to_unified_processing'
]


if __name__ == "__main__":
    # Test the unified processing
    print("UNIFIED CONTENT PROCESSING TEST")
    print("="*40)

    # Test single article
    print("\n1. Testing single article processing:")
    try:
        article_result, content_result = process_article_with_pipeline("https://example.com/test")
        print(f"   Article: {article_result.success}, Method: {article_result.method}")
        if content_result:
            print(f"   Pipeline: {len(content_result.processing_stages)} stages, Quality: {content_result.quality_score:.2f}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test unified processor
    print("\n2. Testing unified processor:")
    try:
        processor = UnifiedContentProcessor({'enable_summarization': True})
        result = processor.process_raw_content("This is test content for processing.")
        print(f"   Processed with {len(result.processing_stages)} stages")
        print(f"   Quality score: {result.quality_score:.2f}")
    except Exception as e:
        print(f"   Error: {e}")

    # Show migration guide
    print("\n3. Migration guide:")
    print(migrate_to_unified_processing())