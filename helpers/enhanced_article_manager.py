#!/usr/bin/env python3
"""
Enhanced Article Manager using the Article Source Registry

This replaces the hardcoded strategy system with a flexible, configurable registry
that automatically handles service outages and provides better management.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

from .article_source_registry import article_source_registry, ArticleFetchResult, ArticleSourceConfig
from .utils import log_info, log_error

logger = logging.getLogger(__name__)

@dataclass
class EnhancedArticleManagerStats:
    """Enhanced statistics for article processing"""
    total_attempts: int = 0
    successful_fetches: int = 0
    failed_fetches: int = 0
    source_usage: Dict[str, int] = None
    average_processing_time: float = 0.0
    last_updated: str = ""

    def __post_init__(self):
        if self.source_usage is None:
            self.source_usage = {}

@dataclass
class ArticleProcessingResult:
    """Enhanced result with registry information"""
    success: bool
    content: str = ""
    source: str = ""
    source_display_name: str = ""
    method: str = ""
    url: str = ""
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None
    error_message: str = ""
    is_fallback: bool = False
    content_quality_score: float = 0.0

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class EnhancedArticleManager:
    """
    Enhanced Article Manager using the Article Source Registry

    This system:
    - Uses the centralized registry for source management
    - Automatically handles service outages and failover
    - Provides detailed performance analytics
    - Supports easy source addition and configuration
    """

    def __init__(self, stats_file: str = "/home/ubuntu/dev/atlas/logs/article_manager_stats.json"):
        self.registry = article_source_registry
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(exist_ok=True)

        self.stats = self._load_stats()
        self._initialize_processing()

    def _initialize_processing(self):
        """Initialize processing system"""
        logger.info("🚀 Enhanced Article Manager initialized with source registry")
        self._log_current_sources()

    def _load_stats(self) -> EnhancedArticleManagerStats:
        """Load statistics from disk"""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    return EnhancedArticleManagerStats(**data)
        except Exception as e:
            logger.error(f"Failed to load article manager stats: {e}")

        return EnhancedArticleManagerStats()

    def _save_stats(self):
        """Save statistics to disk"""
        try:
            self.stats.last_updated = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(asdict(self.stats), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save article manager stats: {e}")

    def _log_current_sources(self):
        """Log current source configuration"""
        sources = self.registry.list_sources()
        logger.info(f"📊 Managing {len(sources)} article sources:")
        for source in sources[:5]:  # Log top 5
            health = "💚" if self.registry.health_status.get(source.name, True) else "❤️‍🩹"
            logger.info(f"   {health} {source.display_name} (priority: {source.priority}, rate: {source.success_rate:.1%})")
        if len(sources) > 5:
            logger.info(f"   ... and {len(sources) - 5} more sources")

    def process_article(self, url: str, content_preview: str = None, log_path: str = "") -> ArticleProcessingResult:
        """
        Process article using enhanced registry-based system
        """
        start_time = time.time()
        self.stats.total_attempts += 1

        try:
            # Get content preview if not provided
            if not content_preview:
                content_preview = self._get_content_preview(url)

            # Use registry to fetch article
            fetch_result = self.registry.fetch_article(url, content_preview, log_path)

            processing_time = time.time() - start_time

            # Update statistics
            self._update_processing_stats(fetch_result, processing_time)

            # Convert to enhanced result
            result = ArticleProcessingResult(
                success=fetch_result.success,
                content=fetch_result.content,
                source=fetch_result.source,
                method=fetch_result.method,
                url=url,
                processing_time=processing_time,
                metadata=fetch_result.metadata,
                error_message=fetch_result.error_message,
                is_fallback=fetch_result.is_fallback
            )

            # Add source display name
            if fetch_result.source in self.registry.sources:
                result.source_display_name = self.registry.sources[fetch_result.source].display_name

            # Calculate content quality score
            if result.success:
                result.content_quality_score = self._calculate_content_quality(result.content)

            # Log result
            self._log_processing_result(result)

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Article processing failed for {url}: {e}")
            self.stats.failed_fetches += 1

            return ArticleProcessingResult(
                success=False,
                url=url,
                processing_time=processing_time,
                error_message=f"Processing error: {str(e)}"
            )

    def _get_content_preview(self, url: str) -> str:
        """Get content preview for URL"""
        try:
            import requests
            response = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if response.status_code == 200:
                # Extract first 1000 characters for analysis
                content = response.text[:1000]
                return content
        except:
            pass

        return ""

    def _calculate_content_quality(self, content: str) -> float:
        """Calculate content quality score (0.0-1.0)"""
        if not content:
            return 0.0

        score = 0.0
        word_count = len(content.split())

        # Length scoring
        if word_count > 500:
            score += 0.3
        elif word_count > 200:
            score += 0.2
        elif word_count > 100:
            score += 0.1

        # Content quality indicators
        quality_indicators = [
            r'\b\w{10,}\b',  # Long words indicate substantial content
            r'\.\s',         # Sentences with periods
            r',\s',          # Commas indicate complex sentences
        ]

        for pattern in quality_indicators:
            import re
            if re.search(pattern, content):
                score += 0.2

        # Penalty for error messages
        error_patterns = [
            'javascript required',
            'please enable',
            'access denied',
            '404 not found',
            '403 forbidden',
            'subscribe to continue'
        ]

        content_lower = content.lower()
        for pattern in error_patterns:
            if pattern in content_lower:
                score -= 0.3

        return max(0.0, min(1.0, score))

    def _update_processing_stats(self, result: ArticleFetchResult, processing_time: float):
        """Update processing statistics"""
        # Update success/failure counts
        if result.success:
            self.stats.successful_fetches += 1
        else:
            self.stats.failed_fetches += 1

        # Update source usage
        if result.source:
            self.stats.source_usage[result.source] = self.stats.source_usage.get(result.source, 0) + 1

        # Update average processing time
        if self.stats.total_attempts > 0:
            current_avg = self.stats.average_processing_time
            new_avg = (current_avg * (self.stats.total_attempts - 1) + processing_time) / self.stats.total_attempts
            self.stats.average_processing_time = new_avg

        # Save stats periodically
        if self.stats.total_attempts % 10 == 0:
            self._save_stats()

    def _log_processing_result(self, result: ArticleProcessingResult):
        """Log processing result"""
        if result.success:
            source_info = f"via {result.source_display_name}" if result.source_display_name else ""
            logger.info(f"✅ Article fetched {source_info}: {result.url}")
            logger.info(f"   Method: {result.method}, Quality: {result.content_quality_score:.2f}")
            logger.info(f"   Processing time: {result.processing_time:.3f}s")
        else:
            logger.warning(f"❌ Article fetch failed: {result.url}")
            logger.warning(f"   Error: {result.error_message}")
            logger.warning(f"   Processing time: {result.processing_time:.3f}s")

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing and source statistics"""
        return {
            "processing_stats": {
                "total_attempts": self.stats.total_attempts,
                "successful_fetches": self.stats.successful_fetches,
                "failed_fetches": self.stats.failed_fetches,
                "success_rate": self.stats.successful_fetches / max(1, self.stats.total_attempts),
                "average_processing_time": self.stats.average_processing_time,
                "last_updated": self.stats.last_updated
            },
            "source_stats": self.registry.get_source_stats(),
            "source_usage": self.stats.source_usage,
            "health_status": self.registry.check_health()
        }

    def optimize_source_priorities(self):
        """Optimize source priorities based on performance"""
        try:
            logger.info("🔧 Optimizing source priorities based on performance...")

            stats = self.registry.get_source_stats()
            optimizations_made = 0

            for source_name, source_stats in stats.items():
                source = self.registry.sources[source_name]

                if not source.enabled:
                    continue

                old_priority = source.priority
                new_priority = old_priority

                # Adjust priority based on success rate
                if source_stats['success_rate'] > 0.8:
                    new_priority += 20
                elif source_stats['success_rate'] > 0.6:
                    new_priority += 10
                elif source_stats['success_rate'] < 0.3:
                    new_priority -= 30

                # Adjust based on health
                if not source_stats['healthy']:
                    new_priority -= 50

                # Adjust based on failure count
                failure_ratio = source_stats['failure_count'] / max(1, source_stats['max_failures'])
                if failure_ratio > 0.7:
                    new_priority -= 40

                # Apply minimum and maximum priorities
                new_priority = max(100, min(1000, new_priority))

                if new_priority != old_priority:
                    source.priority = new_priority
                    optimizations_made += 1
                    logger.info(f"  {source.display_name}: {old_priority} → {new_priority}")

            if optimizations_made > 0:
                self.registry.save_sources()
                logger.info(f"✅ Optimized {optimizations_made} source priorities")
            else:
                logger.info("ℹ️  No priority optimizations needed")

        except Exception as e:
            logger.error(f"Failed to optimize source priorities: {e}")

    def handle_service_outage(self, service_name: str):
        """Handle service outage with intelligent failover"""
        try:
            logger.warning(f"🚨 Handling service outage for: {service_name}")

            # Get source info
            source = self.registry.sources.get(service_name)
            if not source:
                logger.error(f"Unknown service: {service_name}")
                return

            # Find alternatives based on source type
            alternatives = self._find_alternative_sources(source)

            # Handle outage
            self.registry.handle_outage(service_name, alternatives)

            # Log the action
            logger.info(f"📋 Outage handling complete for {service_name}")
            logger.info(f"   Status: Disabled")
            if alternatives:
                logger.info(f"   Alternatives promoted: {len(alternatives)}")

        except Exception as e:
            logger.error(f"Failed to handle service outage: {e}")

    def _find_alternative_sources(self, failed_source: ArticleSourceConfig) -> List[str]:
        """Find alternative sources for a failed service"""
        alternatives = []

        # Find sources of the same type with good performance
        for source in self.registry.sources.values():
            if (source.name != failed_source.name and
                source.enabled and
                source.source_type == failed_source.source_type and
                source.success_rate > 0.5):

                alternatives.append(source.name)

        # If no same-type alternatives, find any high-performing sources
        if not alternatives:
            for source in self.registry.sources.values():
                if (source.name != failed_source.name and
                    source.enabled and
                    source.success_rate > 0.7):

                    alternatives.append(source.name)
                    if len(alternatives) >= 3:  # Limit to top 3 alternatives
                        break

        return alternatives

    def emergency_recover(self):
        """Emergency recovery when all sources are failing"""
        try:
            logger.warning("🚨 EMERGENCY RECOVERY ACTIVATED")

            # Check overall health
            health_status = self.registry.check_health()
            healthy_sources = [name for name, healthy in health_status.items() if healthy]

            if len(healthy_sources) < 2:
                logger.warning("⚠️  Critical: Most sources are unhealthy")

                # Enable basic sources as fallback
                basic_sources = ['direct', 'googlebot', 'playwright']
                for source_name in basic_sources:
                    if source_name in self.registry.sources:
                        source = self.registry.sources[source_name]
                        if not source.enabled:
                            source.enabled = True
                            source.failure_count = 0
                            source.priority = 2000  # Highest priority
                            logger.info(f"  Emergency enabled: {source.display_name}")

                self.registry.save_sources()
                logger.info("✅ Emergency recovery complete")

        except Exception as e:
            logger.error(f"Emergency recovery failed: {e}")

    def test_all_sources(self, test_url: str = "https://example.com") -> Dict[str, Any]:
        """Test all sources with a sample URL"""
        logger.info(f"🧪 Testing all sources with: {test_url}")

        results = {}
        for source_name, source in self.registry.sources.items():
            if not source.enabled:
                results[source_name] = {"status": "disabled", "reason": "Manually disabled"}
                continue

            try:
                logger.info(f"Testing {source.display_name}...")
                result = self.registry.fetch_article(test_url)

                results[source_name] = {
                    "status": "success" if result.success else "failed",
                    "processing_time": result.processing_time,
                    "error": result.error_message if not result.success else None,
                    "content_length": len(result.content) if result.success else 0
                }

            except Exception as e:
                results[source_name] = {
                    "status": "error",
                    "error": str(e)
                }

        return results

    def cleanup_old_stats(self, days_to_keep: int = 30):
        """Clean up old statistics and reset counters"""
        try:
            logger.info(f"🧹 Cleaning up stats older than {days_to_keep} days")

            # Reset statistics but keep configuration
            old_stats = self.stats
            self.stats = EnhancedArticleManagerStats()

            # Preserve some aggregate stats
            self.stats.average_processing_time = old_stats.average_processing_time

            self._save_stats()
            logger.info("✅ Statistics cleanup complete")

        except Exception as e:
            logger.error(f"Failed to cleanup stats: {e}")

    def close(self):
        """Cleanup and save final stats"""
        try:
            self._save_stats()
            logger.info("Enhanced Article Manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.close()
        except:
            pass

# Convenience function for quick article processing
def process_article_enhanced(url: str, content_preview: str = None, log_path: str = "") -> ArticleProcessingResult:
    """Quick article processing using the enhanced system"""
    manager = EnhancedArticleManager()
    return manager.process_article(url, content_preview, log_path)

# Test function
def test_enhanced_article_manager():
    """Test the enhanced article manager system"""
    print("🧪 Testing Enhanced Article Manager")

    # Test URLs
    test_urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://jsonplaceholder.typicode.com/posts/1"
    ]

    manager = EnhancedArticleManager()

    for url in test_urls:
        print(f"\n🔍 Testing: {url}")
        result = manager.process_article(url)

        print(f"  Success: {result.success}")
        print(f"  Source: {result.source_display_name or result.source}")
        print(f"  Method: {result.method}")
        print(f"  Quality: {result.content_quality_score:.2f}")
        print(f"  Processing time: {result.processing_time:.3f}s")

        if result.success:
            print(f"  Content length: {len(result.content)} chars")
        else:
            print(f"  Error: {result.error_message}")

    # Show statistics
    print(f"\n📊 Processing Statistics:")
    stats = manager.get_comprehensive_stats()
    proc_stats = stats["processing_stats"]
    print(f"  Total attempts: {proc_stats['total_attempts']}")
    print(f"  Success rate: {proc_stats['success_rate']:.1%}")
    print(f"  Average time: {proc_stats['average_processing_time']:.3f}s")

    manager.close()

if __name__ == "__main__":
    test_enhanced_article_manager()