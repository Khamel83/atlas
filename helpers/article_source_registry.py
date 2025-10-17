#!/usr/bin/env python3
"""
Article Source Registry System

Centralized registry for managing article fetching sources and services.

This replaces hardcoded strategy lists with a configurable system that:
- Automatically fails over when services go down (like 12ft.io)
- Makes it easy to add new sources without code changes
- Tracks source performance and availability
- Provides centralized configuration management

Inspired by the podcast sources registry but tailored for article fetching.
"""

import json
import logging
import requests
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from abc import ABC, abstractmethod
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ArticleSourceConfig:
    """Configuration for an article source/service"""
    name: str
    display_name: str
    description: str
    source_type: str  # "paywall_bypass", "archive", "proxy", "direct"
    url_patterns: List[str]
    content_patterns: List[str]
    strategy_class: str
    enabled: bool = True
    priority: int = 100
    requires_auth: bool = False
    success_rate: float = 0.0
    last_success: str = ""
    last_failure: str = ""
    failure_count: int = 0
    max_failures: int = 10
    timeout_seconds: int = 30
    rate_limit_delay: float = 2.0
    health_check_url: str = ""
    auto_disable: bool = True

@dataclass
class ArticleFetchResult:
    """Result from article fetching"""
    success: bool
    content: str = ""
    source: str = ""
    method: str = ""
    metadata: Dict[str, Any] = None
    error_message: str = ""
    url_used: str = ""
    processing_time: float = 0.0
    is_fallback: bool = False

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ArticleSourceRegistry:
    """
    Centralized registry for managing article fetching sources

    This system:
    - Automatically handles service outages (like 12ft.io shutdown)
    - Provides configurable source management
    - Tracks source health and performance
    - Supports easy addition of new sources
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "/home/ubuntu/dev/atlas/config/article_sources.json"
        self.config_dir = Path(self.config_path).parent
        self.config_dir.mkdir(exist_ok=True)

        self.sources: Dict[str, ArticleSourceConfig] = {}
        self.strategy_cache: Dict[str, Any] = {}
        self.health_status: Dict[str, bool] = {}

        self._load_sources()

    def _load_sources(self):
        """Load source configurations from file"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for source_data in data.get('sources', []):
                    config = ArticleSourceConfig(**source_data)
                    self.sources[config.name] = config

                logger.info(f"Loaded {len(self.sources)} article sources from {self.config_path}")
            else:
                self._create_default_config()
                self.save_sources()

            # Initialize health status
            self._initialize_health_status()

        except Exception as e:
            logger.error(f"Failed to load article sources: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default article source configurations"""
        default_sources = [
            ArticleSourceConfig(
                name="direct",
                display_name="Direct Fetch",
                description="Direct HTTP requests to target URLs",
                source_type="direct",
                url_patterns=[".*"],
                content_patterns=[".*"],
                strategy_class="helpers.article_strategies.DirectFetchStrategy",
                enabled=True,
                priority=1000,
                success_rate=0.95,
                timeout_seconds=15,
                rate_limit_delay=1.0
            ),
            ArticleSourceConfig(
                name="paywall_bypass",
                display_name="Paywall Bypass Services",
                description="Multiple paywall bypass services (12ft.io alternatives)",
                source_type="paywall_bypass",
                url_patterns=[".*"],
                content_patterns=["subscribe", "premium", "sign in", "create account"],
                strategy_class="helpers.article_strategies.PaywallBypassStrategy",
                enabled=True,
                priority=900,
                success_rate=0.60,
                timeout_seconds=25,
                rate_limit_delay=3.0,
                auto_disable=False
            ),
            ArticleSourceConfig(
                name="archive_today",
                display_name="Archive Today",
                description="Archive.today service for archived content",
                source_type="archive",
                url_patterns=[".*"],
                content_patterns=[".*"],
                strategy_class="helpers.article_strategies.ArchiveTodayStrategy",
                enabled=True,
                priority=800,
                success_rate=0.70,
                timeout_seconds=20,
                rate_limit_delay=2.0,
                health_check_url="https://archive.today"
            ),
            ArticleSourceConfig(
                name="wayback_enhanced",
                display_name="Wayback Machine Enhanced",
                description="Internet Archive with multiple timeframe support",
                source_type="archive",
                url_patterns=[".*"],
                content_patterns=[".*"],
                strategy_class="helpers.article_strategies.EnhancedWaybackMachineStrategy",
                enabled=True,
                priority=750,
                success_rate=0.65,
                timeout_seconds=30,
                rate_limit_delay=2.0,
                health_check_url="https://archive.org"
            ),
            ArticleSourceConfig(
                name="wayback",
                display_name="Wayback Machine",
                description="Basic Internet Archive access",
                source_type="archive",
                url_patterns=[".*"],
                content_patterns=[".*"],
                strategy_class="helpers.article_strategies.WaybackMachineStrategy",
                enabled=True,
                priority=700,
                success_rate=0.50,
                timeout_seconds=25,
                rate_limit_delay=2.0,
                health_check_url="https://archive.org"
            ),
            ArticleSourceConfig(
                name="googlebot",
                display_name="Googlebot User-Agent",
                description="Fetch using Googlebot user agent for paywall bypass",
                source_type="proxy",
                url_patterns=[".*"],
                content_patterns=[".*"],
                strategy_class="helpers.article_strategies.GooglebotStrategy",
                enabled=True,
                priority=600,
                success_rate=0.55,
                timeout_seconds=20,
                rate_limit_delay=1.5
            ),
            ArticleSourceConfig(
                name="twelvefoot",
                display_name="12ft.io (Deprecated)",
                description="12ft.io service - SHUT DOWN July 2025",
                source_type="paywall_bypass",
                url_patterns=[".*"],
                content_patterns=[".*"],
                strategy_class="helpers.article_strategies.TwelveFtStrategy",
                enabled=False,  # Disabled since service is down
                priority=500,
                success_rate=0.0,  # 0% since service is dead
                timeout_seconds=20,
                rate_limit_delay=2.0,
                auto_disable=False
            ),
            ArticleSourceConfig(
                name="playwright",
                display_name="Playwright Browser",
                description="Headless browser rendering for JavaScript-heavy sites",
                source_type="direct",
                url_patterns=[".*"],
                content_patterns=[".*"],
                strategy_class="helpers.article_strategies.PlaywrightStrategy",
                enabled=True,
                priority=400,
                success_rate=0.75,
                timeout_seconds=45,
                rate_limit_delay=5.0
            ),
            ArticleSourceConfig(
                name="firecrawl",
                display_name="Firecrawl",
                description="Premium web scraping and content extraction service",
                source_type="proxy",
                url_patterns=[".*"],
                content_patterns=[".*"],
                strategy_class="helpers.firecrawl_integration.FirecrawlStrategy",
                enabled=False,  # Requires API key
                priority=300,
                requires_auth=True,
                success_rate=0.85,
                timeout_seconds=30,
                rate_limit_delay=1.0
            )
        ]

        self.sources = {source.name: source for source in default_sources}
        logger.info(f"Created default article source configuration with {len(self.sources)} sources")

    def _initialize_health_status(self):
        """Initialize health status for all sources"""
        for name, source in self.sources.items():
            if source.health_check_url:
                self.health_status[name] = self._check_source_health(source)
            else:
                self.health_status[name] = True  # Assume healthy if no health check

    def _check_source_health(self, source: ArticleSourceConfig) -> bool:
        """Check if a source is healthy"""
        if not source.health_check_url:
            return True

        try:
            response = requests.get(
                source.health_check_url,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            return response.status_code == 200
        except:
            return False

    def save_sources(self):
        """Save current source configurations to file"""
        try:
            data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'sources': [asdict(source) for source in self.sources.values()]
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.sources)} article sources to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save article sources: {e}")

    def get_strategies(self, url: str = None, content_preview: str = None) -> List[ArticleSourceConfig]:
        """
        Get list of strategies in priority order for a specific URL
        """
        strategies = []

        for source in self.sources.values():
            if not source.enabled:
                continue

            # Skip unhealthy sources
            if source.name in self.health_status and not self.health_status[source.name]:
                logger.warning(f"Skipping unhealthy source: {source.display_name}")
                continue

            # Skip sources with too many failures
            if source.auto_disable and source.failure_count >= source.max_failures:
                logger.warning(f"Skipping source with too many failures: {source.display_name}")
                continue

            # If URL and content preview provided, check relevance
            if url and content_preview:
                relevance_score = self._calculate_relevance(source, url, content_preview)
                if relevance_score > 0:
                    strategies.append((source, relevance_score))
            else:
                strategies.append((source, 1.0))  # Default relevance

        # Sort by priority (adjusted by relevance)
        strategies.sort(key=lambda x: x[0].priority * x[1], reverse=True)

        return [source for source, _ in strategies]

    def _calculate_relevance(self, source: ArticleSourceConfig, url: str, content_preview: str) -> float:
        """Calculate relevance score for a source"""
        score = 1.0

        # Check URL patterns
        if source.url_patterns:
            url_match = any(re.search(pattern, url, re.IGNORECASE) for pattern in source.url_patterns)
            if url_match:
                score += 0.5

        # Check content patterns (for paywalls, etc.)
        if source.content_patterns:
            content_lower = content_preview.lower()
            pattern_match = any(pattern.lower() in content_lower for pattern in source.content_patterns)
            if pattern_match:
                score += 0.3

        # Bonus for high success rate
        if source.success_rate > 0.8:
            score += 0.2

        return score

    def fetch_article(self, url: str, content_preview: str = None, log_path: str = "") -> ArticleFetchResult:
        """
        Fetch article using the best available strategy
        """
        import time
        start_time = time.time()

        try:
            # Get strategies in priority order
            strategies = self.get_strategies(url, content_preview)

            for source in strategies:
                try:
                    logger.info(f"Attempting {source.display_name} for {url}")
                    result = self._fetch_with_source(source, url, log_path)

                    if result.success:
                        # Update success statistics
                        self._update_source_stats(source, True)
                        result.processing_time = time.time() - start_time
                        return result
                    else:
                        # Update failure statistics
                        self._update_source_stats(source, False)
                        logger.debug(f"{source.display_name} failed for {url}: {result.error_message}")

                except Exception as e:
                    logger.error(f"Error with {source.display_name} for {url}: {e}")
                    self._update_source_stats(source, False)

            # All strategies failed
            processing_time = time.time() - start_time
            return ArticleFetchResult(
                success=False,
                error_message="All article fetching strategies failed",
                processing_time=processing_time
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Article fetch failed for {url}: {e}")
            return ArticleFetchResult(
                success=False,
                error_message=f"Fetch error: {str(e)}",
                processing_time=processing_time
            )

    def _fetch_with_source(self, source: ArticleSourceConfig, url: str, log_path: str) -> ArticleFetchResult:
        """Fetch article using a specific source"""
        try:
            # Get or create strategy instance
            strategy = self._get_strategy(source)
            if not strategy:
                return ArticleFetchResult(
                    success=False,
                    error_message=f"Failed to initialize strategy for {source.display_name}"
                )

            # Apply rate limiting
            if source.rate_limit_delay > 0:
                time.sleep(source.rate_limit_delay)

            # Execute fetch with timeout
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Source {source.name} timed out after {source.timeout_seconds}s")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(source.timeout_seconds)

            try:
                if hasattr(strategy, 'fetch'):
                    fetch_result = strategy.fetch(url, log_path)
                else:
                    # Handle different strategy interfaces
                    fetch_result = self._compatibility_fetch(strategy, url, log_path)

                signal.alarm(0)  # Cancel timeout

                # Convert result to our format
                return ArticleFetchResult(
                    success=getattr(fetch_result, 'success', False),
                    content=getattr(fetch_result, 'content', ''),
                    source=source.name,
                    method=getattr(fetch_result, 'method', source.name),
                    metadata=getattr(fetch_result, 'metadata', {}),
                    error_message=getattr(fetch_result, 'error', ''),
                    url_used=getattr(fetch_result, 'url_used', url),
                    is_fallback=getattr(fetch_result, 'is_fallback', False)
                )

            except TimeoutError:
                signal.alarm(0)
                return ArticleFetchResult(
                    success=False,
                    error_message=f"Timeout after {source.timeout_seconds}s"
                )

        except Exception as e:
            return ArticleFetchResult(
                success=False,
                error_message=f"Fetch error: {str(e)}"
            )

    def _compatibility_fetch(self, strategy, url: str, log_path: str):
        """Compatibility layer for different strategy interfaces"""
        # Try different method names
        for method_name in ['process_url', 'execute', 'run']:
            if hasattr(strategy, method_name):
                method = getattr(strategy, method_name)
                return method(url, log_path=log_path)

        raise AttributeError(f"Strategy has no compatible fetch method")

    def _get_strategy(self, source: ArticleSourceConfig) -> Optional[Any]:
        """Get or create strategy instance"""
        try:
            # Check cache first
            if source.name in self.strategy_cache:
                return self.strategy_cache[source.name]

            # Import and create strategy
            if source.strategy_class == "helpers.firecrawl_integration.FirecrawlStrategy":
                # Firecrawl might not be available
                try:
                    module_path, class_name = source.strategy_class.rsplit('.', 1)
                    module = __import__(module_path, fromlist=[class_name])
                    strategy_class = getattr(module, class_name)
                    strategy = strategy_class()
                    self.strategy_cache[source.name] = strategy
                    return strategy
                except ImportError:
                    logger.warning(f"Firecrawl strategy not available, disabling")
                    source.enabled = False
                    return None

            module_path, class_name = source.strategy_class.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            strategy_class = getattr(module, class_name)

            strategy = strategy_class()
            self.strategy_cache[source.name] = strategy

            logger.debug(f"Initialized strategy for {source.display_name}")
            return strategy

        except Exception as e:
            logger.error(f"Failed to initialize strategy {source.strategy_class}: {e}")
            return None

    def _update_source_stats(self, source: ArticleSourceConfig, success: bool):
        """Update source statistics"""
        try:
            now = datetime.now().isoformat()

            if success:
                source.success_rate = source.success_rate * 0.9 + 0.1  # Increase by 10%
                source.last_success = now
                source.failure_count = 0  # Reset failure count on success
            else:
                source.success_rate = source.success_rate * 0.9  # Decrease by 10%
                source.last_failure = now
                source.failure_count += 1

                # Auto-disable if too many failures
                if source.auto_disable and source.failure_count >= source.max_failures:
                    source.enabled = False
                    logger.warning(f"Auto-disabled {source.display_name} due to {source.failure_count} failures")

            # Check health if we had a failure
            if not success and source.health_check_url:
                self.health_status[source.name] = self._check_source_health(source)

        except Exception as e:
            logger.error(f"Error updating source stats: {e}")

    def add_source(self, source: ArticleSourceConfig):
        """Add a new article source"""
        self.sources[source.name] = source
        self.save_sources()
        logger.info(f"Added new article source: {source.display_name}")

    def remove_source(self, source_name: str):
        """Remove an article source"""
        if source_name in self.sources:
            del self.sources[source_name]
            if source_name in self.strategy_cache:
                del self.strategy_cache[source_name]
            if source_name in self.health_status:
                del self.health_status[source_name]
            self.save_sources()
            logger.info(f"Removed article source: {source_name}")

    def enable_source(self, source_name: str):
        """Enable a source"""
        if source_name in self.sources:
            source = self.sources[source_name]
            source.enabled = True
            source.failure_count = 0  # Reset failure count
            self.save_sources()
            logger.info(f"Enabled article source: {source_name}")

    def disable_source(self, source_name: str, reason: str = ""):
        """Disable a source"""
        if source_name in self.sources:
            self.sources[source_name].enabled = False
            self.save_sources()
            logger.info(f"Disabled article source: {source_name} - {reason}")

    def get_source_stats(self) -> Dict[str, Any]:
        """Get statistics for all sources"""
        stats = {}
        for name, source in self.sources.items():
            stats[name] = {
                'display_name': source.display_name,
                'enabled': source.enabled,
                'source_type': source.source_type,
                'priority': source.priority,
                'success_rate': source.success_rate,
                'failure_count': source.failure_count,
                'max_failures': source.max_failures,
                'last_success': source.last_success,
                'last_failure': source.last_failure,
                'healthy': self.health_status.get(name, True),
                'requires_auth': source.requires_auth,
                'timeout_seconds': source.timeout_seconds,
                'auto_disable': source.auto_disable
            }
        return stats

    def check_health(self) -> Dict[str, bool]:
        """Check health of all sources"""
        health_results = {}
        for name, source in self.sources.items():
            if source.health_check_url:
                healthy = self._check_source_health(source)
                self.health_status[name] = healthy
                health_results[name] = healthy
            else:
                health_results[name] = True

        return health_results

    def handle_outage(self, source_name: str, alternative_sources: List[str] = None):
        """Handle service outage by disabling source and suggesting alternatives"""
        if source_name in self.sources:
            source = self.sources[source_name]
            self.disable_source(source_name, f"Service outage detected - {datetime.now()}")

            logger.warning(f"🚨 OUTAGE: {source.display_name} has been disabled due to service outage")

            if alternative_sources:
                logger.info(f"🔄 Recommended alternatives: {', '.join(alternative_sources)}")
                # Increase priority of alternatives
                for alt_name in alternative_sources:
                    if alt_name in self.sources:
                        self.sources[alt_name].priority += 50
                        logger.info(f"  Increased priority for {self.sources[alt_name].display_name}")

            self.save_sources()

    def list_sources(self, enabled_only: bool = True) -> List[ArticleSourceConfig]:
        """List all sources"""
        sources = list(self.sources.values())
        if enabled_only:
            sources = [s for s in sources if s.enabled]
        return sorted(sources, key=lambda x: x.priority, reverse=True)

# Global registry instance
article_source_registry = ArticleSourceRegistry()

def main():
    """CLI interface for managing article sources"""
    import argparse

    parser = argparse.ArgumentParser(description="Article Sources Registry Manager")
    parser.add_argument("--list", action="store_true", help="List all sources")
    parser.add_argument("--stats", action="store_true", help="Show source statistics")
    parser.add_argument("--health", action="store_true", help="Check source health")
    parser.add_argument("--enable", help="Enable a source")
    parser.add_argument("--disable", help="Disable a source")
    parser.add_argument("--test", help="Test a source with URL")

    args = parser.parse_args()

    if args.list:
        sources = article_source_registry.list_sources()
        print("📺 Article Fetching Sources")
        print("=" * 50)
        for source in sources:
            status = "✅" if source.enabled else "🚫"
            health = "💚" if article_source_registry.health_status.get(source.name, True) else "❤️‍🩹"
            print(f"{status} {health} {source.display_name} ({source.name})")
            print(f"   Type: {source.source_type}")
            print(f"   Priority: {source.priority}")
            print(f"   Success Rate: {source.success_rate:.1%}")
            print(f"   Failures: {source.failure_count}/{source.max_failures}")
            print()

    elif args.stats:
        stats = article_source_registry.get_source_stats()
        print("📊 Source Statistics")
        print("=" * 50)
        for name, stat in stats.items():
            status = "✅" if stat['enabled'] else "🚫"
            health = "💚" if stat['healthy'] else "❤️‍🩹"
            print(f"{status} {health} {stat['display_name']}")
            print(f"   Success Rate: {stat['success_rate']:.1%}")
            print(f"   Priority: {stat['priority']}")
            print(f"   Type: {stat['source_type']}")
            print(f"   Failures: {stat['failure_count']}/{stat['max_failures']}")
            print(f"   Last Success: {stat['last_success'] or 'Never'}")
            print()

    elif args.health:
        health_results = article_source_registry.check_health()
        print("🏥 Source Health Check")
        print("=" * 50)
        for name, healthy in health_results.items():
            source = article_source_registry.sources[name]
            status = "💚 Healthy" if healthy else "❤️‍🩹 Unhealthy"
            enabled_status = "✅" if source.enabled else "🚫"
            print(f"{enabled_status} {status} {source.display_name}")

    elif args.enable:
        article_source_registry.enable_source(args.enable)
        print(f"✅ Enabled {args.enable}")

    elif args.disable:
        article_source_registry.disable_source(args.disable, "Manual disable")
        print(f"🚫 Disabled {args.disable}")

    elif args.test:
        if not args.test.startswith('http'):
            print("❌ Please provide a valid URL for testing")
            return

        result = article_source_registry.fetch_article(args.test)
        print(f"Test result for {args.test}:")
        print(f"  Success: {result.success}")
        print(f"  Source: {result.source}")
        print(f"  Method: {result.method}")
        print(f"  Processing time: {result.processing_time:.3f}s")
        if result.success:
            print(f"  Content length: {len(result.content)} chars")
        else:
            print(f"  Error: {result.error_message}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()