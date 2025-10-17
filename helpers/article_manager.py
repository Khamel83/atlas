#!/usr/bin/env python3
"""
Unified Article Manager - Consolidates all article processing strategies

This manager provides a unified interface for all article fetching and processing,
combining multiple strategies with intelligent cascade and statistical tracking.

Key Features:
- Unified strategy interface with intelligent selection
- Comprehensive statistics and success tracking
- Bulk processing with concurrency controls
- Enhanced recovery for failed articles
- Configuration-driven strategy preferences
- Backward compatibility with existing code
"""

import json
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from helpers.utils import log_info, log_error


class StrategyResult(Enum):
    """Result types for strategy attempts"""
    SUCCESS = "success"
    FAILED = "failed"
    TRUNCATED = "truncated"
    SKIP = "skip"


@dataclass
class ProcessingStats:
    """Statistics container for article processing"""
    total_attempts: int = 0
    total_successes: int = 0
    total_failures: int = 0
    strategy_stats: Dict[str, Dict[str, int]] = None
    processing_times: List[float] = None
    last_updated: str = None

    def __post_init__(self):
        if self.strategy_stats is None:
            self.strategy_stats = {}
        if self.processing_times is None:
            self.processing_times = []
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()


@dataclass
class ArticleResult:
    """Unified result container for article processing"""
    success: bool
    url: str
    content: str = None
    title: str = None
    method: str = None
    strategy: str = None
    error: str = None
    is_truncated: bool = False
    metadata: Dict[str, Any] = None
    processing_time: float = 0.0
    timestamp: str = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        # Ensure method and strategy are synchronized
        if self.method and not self.strategy:
            self.strategy = self.method
        elif self.strategy and not self.method:
            self.method = self.strategy


class ArticleManager:
    """
    Unified article manager with intelligent strategy cascade.

    Consolidates all article fetching strategies into a single, configurable interface
    with comprehensive statistics, bulk processing, and failure recovery.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize ArticleManager with configuration."""
        self.config = config or {}
        self.stats_file = Path(self.config.get('stats_file', 'data/article_processing_stats.json'))
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize statistics
        self.stats = self._load_stats()

        # Initialize strategies lazily to avoid import conflicts
        self._strategies = None
        self._strategy_cache = {}

        # Processing configuration
        self.max_concurrent = self.config.get('max_concurrent', 5)
        self.default_timeout = self.config.get('default_timeout', 30)
        self.retry_attempts = self.config.get('retry_attempts', 2)
        self.preferred_strategies = self.config.get('preferred_strategies', [])

        log_info("", f"ArticleManager initialized with {len(self.preferred_strategies)} preferred strategies")

    @property
    def strategies(self):
        """Lazy load strategies to avoid circular imports."""
        if self._strategies is None:
            self._strategies = self._initialize_strategies()
        return self._strategies

    def _initialize_strategies(self):
        """Initialize all available article fetching strategies."""
        strategies = []

        try:
            # Import all strategy classes
            from helpers.article_strategies import (
                DirectFetchStrategy,
                PaywallBypassStrategy,
                ArchiveTodayStrategy,
                GooglebotStrategy,
                PlaywrightStrategy,
                PaywallAuthenticatedStrategy,
                TwelveFtStrategy,
                EnhancedWaybackMachineStrategy,
                WaybackMachineStrategy
            )

            # Simple auth strategy (preferred over Playwright for compatibility)
            try:
                from helpers.simple_auth_strategy import SimpleAuthStrategy
                auth_strategy = SimpleAuthStrategy(self.config)
            except ImportError:
                auth_strategy = PaywallAuthenticatedStrategy(self.config)

            # Firecrawl strategy (optional, usage limited)
            try:
                from helpers.firecrawl_strategy import FirecrawlStrategy
                firecrawl = FirecrawlStrategy(self.config)
                if firecrawl._check_usage_limit():
                    strategies.append(('firecrawl', firecrawl))
                    log_info("", "Firecrawl strategy loaded with remaining usage")
            except ImportError:
                log_info("", "Firecrawl strategy not available")

            # Core strategies in intelligent order
            strategy_instances = [
                ('direct', DirectFetchStrategy()),
                ('auth', auth_strategy),
                ('paywall_bypass', PaywallBypassStrategy()),
                ('archive_today', ArchiveTodayStrategy()),
                ('googlebot', GooglebotStrategy()),
                ('twelvefoot', TwelveFtStrategy()),
                ('wayback_enhanced', EnhancedWaybackMachineStrategy()),
                ('wayback', WaybackMachineStrategy()),
                ('playwright', PlaywrightStrategy()),  # Last resort due to potential conflicts
            ]

            strategies.extend(strategy_instances)

            log_info("", f"Initialized {len(strategies)} article fetching strategies")

        except ImportError as e:
            log_error("", f"Failed to import article strategies: {e}")
            strategies = []

        return strategies

    def _load_stats(self) -> ProcessingStats:
        """Load processing statistics from disk."""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    return ProcessingStats(**data)
        except Exception as e:
            log_error("", f"Failed to load stats: {e}")

        return ProcessingStats()

    def _save_stats(self):
        """Save processing statistics to disk."""
        try:
            self.stats.last_updated = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(asdict(self.stats), f, indent=2)
        except Exception as e:
            log_error("", f"Failed to save stats: {e}")

    def _record_attempt(self, strategy_name: str, result_type: StrategyResult, url: str, processing_time: float = 0.0):
        """Record a strategy attempt in statistics."""
        self.stats.total_attempts += 1

        if strategy_name not in self.stats.strategy_stats:
            self.stats.strategy_stats[strategy_name] = {
                'attempts': 0,
                'successes': 0,
                'failures': 0,
                'truncated': 0,
                'avg_time': 0.0
            }

        strategy_stats = self.stats.strategy_stats[strategy_name]
        strategy_stats['attempts'] += 1

        if result_type == StrategyResult.SUCCESS:
            self.stats.total_successes += 1
            strategy_stats['successes'] += 1
        elif result_type == StrategyResult.TRUNCATED:
            strategy_stats['truncated'] += 1
        else:
            self.stats.total_failures += 1
            strategy_stats['failures'] += 1

        # Update timing statistics
        if processing_time > 0:
            self.stats.processing_times.append(processing_time)
            # Keep only last 1000 times to prevent unbounded growth
            if len(self.stats.processing_times) > 1000:
                self.stats.processing_times = self.stats.processing_times[-1000:]

            # Update strategy average time
            current_avg = strategy_stats.get('avg_time', 0.0)
            attempts = strategy_stats['attempts']
            strategy_stats['avg_time'] = ((current_avg * (attempts - 1)) + processing_time) / attempts

    def process_article(self,
                       url: str,
                       preferred_strategies: List[str] = None,
                       log_path: str = "",
                       **kwargs) -> ArticleResult:
        """
        Process a single article using intelligent strategy selection.

        Args:
            url: URL to process
            preferred_strategies: List of strategy names to try first
            log_path: Path for logging
            **kwargs: Additional arguments passed to strategies

        Returns:
            ArticleResult with processing outcome
        """
        start_time = time.time()

        log_info(log_path, f"Processing article: {url}")

        # Determine strategy order
        strategy_order = self._get_strategy_order(preferred_strategies)

        last_error = None

        for strategy_name, strategy in strategy_order:
            try:
                strategy_start = time.time()
                log_info(log_path, f"Trying {strategy_name} strategy for {url}")

                # Execute strategy
                result = strategy.fetch(url, log_path, **kwargs)
                strategy_time = time.time() - strategy_start

                if result.success:
                    # Import here to avoid circular imports
                    from helpers.article_strategies import ContentAnalyzer

                    # Check content quality
                    is_truncated = ContentAnalyzer.is_truncated(result.content, log_path)

                    if is_truncated:
                        self._record_attempt(strategy_name, StrategyResult.TRUNCATED, url, strategy_time)
                        log_info(log_path, f"{strategy_name} succeeded but content appears truncated, trying next strategy...")
                        continue

                    # Success!
                    self._record_attempt(strategy_name, StrategyResult.SUCCESS, url, strategy_time)
                    processing_time = time.time() - start_time

                    log_info(log_path, f"Successfully processed {url} using {strategy_name} in {processing_time:.2f}s")

                    article_result = ArticleResult(
                        success=True,
                        url=url,
                        content=result.content,
                        title=getattr(result, 'title', None),
                        method=strategy_name,
                        strategy=strategy_name,
                        is_truncated=False,
                        metadata=result.metadata,
                        processing_time=processing_time
                    )

                    self._save_stats()
                    return article_result

                else:
                    self._record_attempt(strategy_name, StrategyResult.FAILED, url, strategy_time)
                    last_error = result.error
                    log_info(log_path, f"{strategy_name} strategy failed: {result.error}")

            except Exception as e:
                self._record_attempt(strategy_name, StrategyResult.FAILED, url)
                last_error = str(e)
                log_error(log_path, f"{strategy_name} strategy raised exception: {e}")
                continue

        # All strategies failed
        processing_time = time.time() - start_time
        log_error(log_path, f"All strategies failed for {url} after {processing_time:.2f}s")

        self._save_stats()
        return ArticleResult(
            success=False,
            url=url,
            error=f"All strategies failed. Last error: {last_error}",
            processing_time=processing_time
        )

    def _get_strategy_order(self, preferred_strategies: List[str] = None) -> List[Tuple[str, Any]]:
        """Get ordered list of strategies to try."""
        strategy_dict = dict(self.strategies)

        # Start with preferred strategies if specified
        ordered_strategies = []
        used_strategies = set()

        if preferred_strategies:
            for strategy_name in preferred_strategies:
                if strategy_name in strategy_dict:
                    ordered_strategies.append((strategy_name, strategy_dict[strategy_name]))
                    used_strategies.add(strategy_name)

        # Add remaining strategies in default order, sorted by historical success rate
        remaining_strategies = [(name, strategy) for name, strategy in self.strategies
                             if name not in used_strategies]

        # Sort by success rate (higher first)
        def get_success_rate(strategy_name):
            stats = self.stats.strategy_stats.get(strategy_name, {})
            attempts = stats.get('attempts', 0)
            if attempts == 0:
                return 0.5  # Default for untried strategies
            return stats.get('successes', 0) / attempts

        remaining_strategies.sort(key=lambda x: get_success_rate(x[0]), reverse=True)
        ordered_strategies.extend(remaining_strategies)

        return ordered_strategies

    def bulk_process_articles(self,
                            urls: List[str],
                            max_concurrent: int = None,
                            log_path: str = "",
                            **kwargs) -> Dict[str, ArticleResult]:
        """
        Process multiple articles concurrently with rate limiting.

        Args:
            urls: List of URLs to process
            max_concurrent: Maximum concurrent processing (default: self.max_concurrent)
            log_path: Path for logging
            **kwargs: Additional arguments passed to process_article

        Returns:
            Dictionary mapping URLs to ArticleResult objects
        """
        if not urls:
            return {}

        max_concurrent = max_concurrent or self.max_concurrent
        log_info(log_path, f"Bulk processing {len(urls)} articles with concurrency {max_concurrent}")

        results = {}

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all jobs
            future_to_url = {
                executor.submit(self.process_article, url, log_path=log_path, **kwargs): url
                for url in urls
            }

            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results[url] = result

                    if result.success:
                        log_info(log_path, f"✓ Completed {url} ({result.strategy})")
                    else:
                        log_error(log_path, f"✗ Failed {url}: {result.error}")

                except Exception as e:
                    log_error(log_path, f"✗ Exception processing {url}: {e}")
                    results[url] = ArticleResult(
                        success=False,
                        url=url,
                        error=f"Processing exception: {e}"
                    )

        success_count = sum(1 for r in results.values() if r.success)
        log_info(log_path, f"Bulk processing complete: {success_count}/{len(urls)} successful")

        return results

    def recover_failed_articles(self,
                              urls: List[str],
                              additional_strategies: List[str] = None,
                              log_path: str = "",
                              **kwargs) -> Dict[str, ArticleResult]:
        """
        Specialized recovery for previously failed articles using enhanced strategies.

        Args:
            urls: List of URLs that previously failed
            additional_strategies: Extra strategies to try for recovery
            log_path: Path for logging
            **kwargs: Additional arguments passed to strategies

        Returns:
            Dictionary mapping URLs to ArticleResult objects
        """
        if not urls:
            return {}

        log_info(log_path, f"Attempting recovery for {len(urls)} failed articles")

        # Enhanced strategy list for recovery
        recovery_strategies = [
            'auth',  # Try authentication first
            'wayback_enhanced',  # Enhanced Wayback with multiple timeframes
            'archive_today',  # Archive.today with mirrors
            'firecrawl',  # AI-powered extraction (if available)
            'playwright',  # Browser-based as last resort
        ]

        if additional_strategies:
            recovery_strategies = additional_strategies + recovery_strategies

        # Remove duplicates while preserving order
        seen = set()
        recovery_strategies = [s for s in recovery_strategies if not (s in seen or seen.add(s))]

        return self.bulk_process_articles(
            urls,
            preferred_strategies=recovery_strategies,
            log_path=log_path,
            **kwargs
        )

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get detailed processing statistics."""
        stats_dict = asdict(self.stats)

        # Calculate additional metrics
        if self.stats.total_attempts > 0:
            stats_dict['overall_success_rate'] = self.stats.total_successes / self.stats.total_attempts
        else:
            stats_dict['overall_success_rate'] = 0.0

        if self.stats.processing_times:
            times = self.stats.processing_times
            stats_dict['avg_processing_time'] = sum(times) / len(times)
            stats_dict['median_processing_time'] = sorted(times)[len(times) // 2]
        else:
            stats_dict['avg_processing_time'] = 0.0
            stats_dict['median_processing_time'] = 0.0

        # Strategy success rates
        strategy_rates = {}
        for strategy, data in self.stats.strategy_stats.items():
            attempts = data.get('attempts', 0)
            if attempts > 0:
                strategy_rates[strategy] = {
                    'success_rate': data.get('successes', 0) / attempts,
                    'attempts': attempts,
                    'avg_time': data.get('avg_time', 0.0)
                }
        stats_dict['strategy_success_rates'] = strategy_rates

        return stats_dict

    def reset_stats(self):
        """Reset all processing statistics."""
        self.stats = ProcessingStats()
        self._save_stats()
        log_info("", "Processing statistics reset")

    def export_stats(self, filepath: str = None) -> str:
        """Export statistics to JSON file."""
        if not filepath:
            filepath = f"article_processing_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        stats_export = self.get_processing_stats()

        with open(filepath, 'w') as f:
            json.dump(stats_export, f, indent=2)

        log_info("", f"Statistics exported to {filepath}")
        return filepath


# Backward compatibility function
def create_article_manager(config: Dict[str, Any] = None) -> ArticleManager:
    """Create ArticleManager instance with backward compatibility."""
    return ArticleManager(config)


# Legacy interface for gradual migration
class ArticleFetcher:
    """Legacy ArticleFetcher interface for backward compatibility."""

    def __init__(self, config=None):
        import warnings
        warnings.warn(
            "ArticleFetcher is deprecated, use ArticleManager instead",
            DeprecationWarning,
            stacklevel=2
        )
        self.manager = ArticleManager(config)

    def fetch_with_fallbacks(self, url: str, log_path: str = ""):
        """Legacy method - delegates to ArticleManager."""
        result = self.manager.process_article(url, log_path=log_path)

        # Convert to old FetchResult format for compatibility
        from helpers.article_strategies import FetchResult
        return FetchResult(
            success=result.success,
            content=result.content,
            method=result.method,
            error=result.error,
            is_truncated=result.is_truncated,
            metadata=result.metadata,
            title=result.title
        )


if __name__ == "__main__":
    # Example usage
    config = {
        'max_concurrent': 3,
        'preferred_strategies': ['direct', 'auth']
    }

    manager = ArticleManager(config)

    # Test single article
    result = manager.process_article("https://example.com/article")
    print(f"Result: {result.success}, Method: {result.method}")

    # Test bulk processing
    urls = ["https://example.com/1", "https://example.com/2"]
    results = manager.bulk_process_articles(urls)
    print(f"Bulk results: {len(results)} processed")

    # Print statistics
    stats = manager.get_processing_stats()
    print(f"Success rate: {stats['overall_success_rate']:.2%}")