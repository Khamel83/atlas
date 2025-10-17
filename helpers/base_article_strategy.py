#!/usr/bin/env python3
"""
Base Article Strategy Interface

Provides a standardized interface for all article fetching strategies,
ensuring consistent behavior and enabling intelligent strategy management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum


class StrategyCapability(Enum):
    """Capabilities that strategies may support"""
    BASIC_FETCH = "basic_fetch"
    PAYWALL_BYPASS = "paywall_bypass"
    AUTHENTICATION = "authentication"
    JAVASCRIPT_RENDERING = "javascript_rendering"
    ARCHIVE_ACCESS = "archive_access"
    AI_EXTRACTION = "ai_extraction"
    RATE_LIMITED = "rate_limited"


class StrategyPriority(Enum):
    """Priority levels for strategy selection"""
    HIGHEST = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    FALLBACK = 5


@dataclass
class StrategyMetadata:
    """Metadata about a strategy's capabilities and characteristics"""
    name: str
    priority: StrategyPriority
    capabilities: list[StrategyCapability]
    estimated_success_rate: float = 0.5  # Default neutral rate
    average_response_time: float = 5.0   # Default 5 seconds
    requires_auth: bool = False
    has_usage_limits: bool = False
    usage_limit_remaining: Optional[int] = None
    rate_limit_delay: float = 0.0  # Seconds to wait between requests
    supported_domains: list[str] = None  # None means all domains
    description: str = ""

    def __post_init__(self):
        if self.supported_domains is None:
            self.supported_domains = []


@dataclass
class FetchResult:
    """Standardized result container for article fetching"""
    success: bool
    url: str
    content: str = None
    title: str = None
    method: str = None
    strategy: str = None
    error: str = None
    is_truncated: bool = False
    metadata: Dict[str, Any] = None
    response_time: float = 0.0

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        # Ensure method and strategy are synchronized for backward compatibility
        if self.method and not self.strategy:
            self.strategy = self.method
        elif self.strategy and not self.method:
            self.method = self.strategy


class BaseArticleStrategy(ABC):
    """
    Abstract base class for all article fetching strategies.

    This interface ensures consistent behavior across all strategies and enables
    intelligent strategy management by the ArticleManager.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize strategy with configuration."""
        self.config = config or {}
        self._metadata = None

    @property
    def metadata(self) -> StrategyMetadata:
        """Get strategy metadata (cached)."""
        if self._metadata is None:
            self._metadata = self.get_metadata()
        return self._metadata

    @abstractmethod
    def get_metadata(self) -> StrategyMetadata:
        """Return metadata describing this strategy's capabilities."""
        pass

    @abstractmethod
    def fetch(self, url: str, log_path: str = "", **kwargs) -> FetchResult:
        """
        Fetch article content from the given URL.

        Args:
            url: URL to fetch
            log_path: Path for logging output
            **kwargs: Additional strategy-specific arguments

        Returns:
            FetchResult with success/failure and content
        """
        pass

    def can_handle_url(self, url: str) -> bool:
        """
        Check if this strategy can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if strategy can handle this URL
        """
        # Default: can handle any URL unless supported_domains is specified
        if not self.metadata.supported_domains:
            return True

        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()

        for supported_domain in self.metadata.supported_domains:
            if domain.endswith(supported_domain.lower()):
                return True

        return False

    def get_success_rate(self, historical_stats: Dict[str, Any] = None) -> float:
        """
        Get historical success rate for this strategy.

        Args:
            historical_stats: Optional stats from ArticleManager

        Returns:
            Success rate between 0.0 and 1.0
        """
        if historical_stats and self.metadata.name in historical_stats:
            stats = historical_stats[self.metadata.name]
            attempts = stats.get('attempts', 0)
            if attempts > 0:
                return stats.get('successes', 0) / attempts

        return self.metadata.estimated_success_rate

    def check_usage_limit(self) -> bool:
        """
        Check if strategy has remaining usage limit.

        Returns:
            True if strategy can be used (no limits or limits not exceeded)
        """
        if not self.metadata.has_usage_limits:
            return True

        if self.metadata.usage_limit_remaining is None:
            return True  # Unknown limit state, assume OK

        return self.metadata.usage_limit_remaining > 0

    def update_usage_count(self, consumed: int = 1):
        """
        Update usage count for strategies with limits.

        Args:
            consumed: Number of API calls or requests consumed
        """
        if (self.metadata.has_usage_limits and
            self.metadata.usage_limit_remaining is not None):
            self.metadata.usage_limit_remaining = max(0,
                self.metadata.usage_limit_remaining - consumed)

    def get_rate_limit_delay(self) -> float:
        """Get recommended delay before next request."""
        return self.metadata.rate_limit_delay

    def __str__(self) -> str:
        """String representation of strategy."""
        return f"{self.metadata.name} (priority: {self.metadata.priority.name})"

    def __repr__(self) -> str:
        """Detailed representation of strategy."""
        return (f"<{self.__class__.__name__} "
                f"name='{self.metadata.name}' "
                f"priority={self.metadata.priority.name} "
                f"capabilities={[c.value for c in self.metadata.capabilities]}>")


class LegacyStrategyAdapter(BaseArticleStrategy):
    """
    Adapter to wrap legacy ArticleFetchStrategy instances.

    This allows existing strategies to work with the new interface without modification.
    """

    def __init__(self, legacy_strategy, config: Dict[str, Any] = None):
        """
        Initialize adapter with legacy strategy.

        Args:
            legacy_strategy: Instance of old ArticleFetchStrategy
            config: Configuration dict
        """
        super().__init__(config)
        self.legacy_strategy = legacy_strategy

    def get_metadata(self) -> StrategyMetadata:
        """Generate metadata for legacy strategy."""
        strategy_name = self.legacy_strategy.get_strategy_name()

        # Map known strategy names to capabilities
        capability_mapping = {
            'direct': [StrategyCapability.BASIC_FETCH],
            'auth': [StrategyCapability.AUTHENTICATION, StrategyCapability.PAYWALL_BYPASS],
            'paywall_bypass': [StrategyCapability.PAYWALL_BYPASS],
            'archive_today': [StrategyCapability.ARCHIVE_ACCESS],
            'googlebot': [StrategyCapability.BASIC_FETCH],
            'playwright': [StrategyCapability.JAVASCRIPT_RENDERING, StrategyCapability.PAYWALL_BYPASS],
            'twelvefoot': [StrategyCapability.PAYWALL_BYPASS],
            'wayback_enhanced': [StrategyCapability.ARCHIVE_ACCESS],
            'wayback': [StrategyCapability.ARCHIVE_ACCESS],
            'firecrawl': [StrategyCapability.AI_EXTRACTION, StrategyCapability.RATE_LIMITED],
        }

        # Map to priority levels
        priority_mapping = {
            'direct': StrategyPriority.HIGHEST,
            'auth': StrategyPriority.HIGH,
            'paywall_bypass': StrategyPriority.MEDIUM,
            'googlebot': StrategyPriority.MEDIUM,
            'twelvefoot': StrategyPriority.MEDIUM,
            'archive_today': StrategyPriority.LOW,
            'wayback_enhanced': StrategyPriority.LOW,
            'wayback': StrategyPriority.FALLBACK,
            'playwright': StrategyPriority.FALLBACK,
            'firecrawl': StrategyPriority.FALLBACK,
        }

        capabilities = capability_mapping.get(strategy_name, [StrategyCapability.BASIC_FETCH])
        priority = priority_mapping.get(strategy_name, StrategyPriority.MEDIUM)

        # Check if strategy has usage limits (Firecrawl)
        has_limits = False
        limit_remaining = None
        if hasattr(self.legacy_strategy, '_check_usage_limit'):
            has_limits = True
            try:
                if hasattr(self.legacy_strategy, 'usage_remaining'):
                    limit_remaining = self.legacy_strategy.usage_remaining
            except:
                pass

        return StrategyMetadata(
            name=strategy_name,
            priority=priority,
            capabilities=capabilities,
            estimated_success_rate=0.5,  # Default for legacy
            average_response_time=5.0,
            requires_auth=(strategy_name in ['auth', 'nytimes_auth', 'wsj_auth']),
            has_usage_limits=has_limits,
            usage_limit_remaining=limit_remaining,
            rate_limit_delay=1.0 if strategy_name == 'firecrawl' else 0.0,
            description=f"Legacy {strategy_name} strategy"
        )

    def fetch(self, url: str, log_path: str = "", **kwargs) -> FetchResult:
        """Delegate to legacy strategy and adapt result."""
        import time

        start_time = time.time()

        try:
            legacy_result = self.legacy_strategy.fetch(url, log_path)
            response_time = time.time() - start_time

            # Adapt legacy FetchResult to new FetchResult
            return FetchResult(
                success=legacy_result.success,
                url=url,
                content=legacy_result.content,
                title=getattr(legacy_result, 'title', None),
                method=legacy_result.method or legacy_result.strategy,
                strategy=legacy_result.strategy or legacy_result.method,
                error=legacy_result.error,
                is_truncated=getattr(legacy_result, 'is_truncated', False),
                metadata=legacy_result.metadata or {},
                response_time=response_time
            )

        except Exception as e:
            response_time = time.time() - start_time
            return FetchResult(
                success=False,
                url=url,
                error=str(e),
                method=self.metadata.name,
                strategy=self.metadata.name,
                response_time=response_time
            )

    def check_usage_limit(self) -> bool:
        """Check usage limit on legacy strategy."""
        if hasattr(self.legacy_strategy, '_check_usage_limit'):
            try:
                return self.legacy_strategy._check_usage_limit()
            except:
                return True
        return True


def adapt_legacy_strategies(legacy_strategies: list) -> list[BaseArticleStrategy]:
    """
    Convert a list of legacy strategies to new interface.

    Args:
        legacy_strategies: List of (name, strategy) tuples

    Returns:
        List of BaseArticleStrategy instances
    """
    adapted = []

    for name, strategy in legacy_strategies:
        try:
            # Check if it's already a BaseArticleStrategy
            if isinstance(strategy, BaseArticleStrategy):
                adapted.append(strategy)
            else:
                # Wrap with adapter
                adapted_strategy = LegacyStrategyAdapter(strategy)
                adapted.append(adapted_strategy)
        except Exception as e:
            from helpers.utils import log_error
            log_error("", f"Failed to adapt strategy {name}: {e}")

    return adapted


# Factory function for creating strategies
def create_strategy(strategy_name: str, config: Dict[str, Any] = None) -> Optional[BaseArticleStrategy]:
    """
    Factory function to create strategy instances by name.

    Args:
        strategy_name: Name of strategy to create
        config: Configuration for strategy

    Returns:
        Strategy instance or None if not found
    """
    try:
        if strategy_name == 'direct':
            from helpers.article_strategies import DirectFetchStrategy
            return LegacyStrategyAdapter(DirectFetchStrategy(), config)

        elif strategy_name == 'auth':
            try:
                from helpers.simple_auth_strategy import SimpleAuthStrategy
                return LegacyStrategyAdapter(SimpleAuthStrategy(config), config)
            except ImportError:
                from helpers.article_strategies import PaywallAuthenticatedStrategy
                return LegacyStrategyAdapter(PaywallAuthenticatedStrategy(config), config)

        elif strategy_name == 'paywall_bypass':
            from helpers.article_strategies import PaywallBypassStrategy
            return LegacyStrategyAdapter(PaywallBypassStrategy(), config)

        elif strategy_name == 'archive_today':
            from helpers.article_strategies import ArchiveTodayStrategy
            return LegacyStrategyAdapter(ArchiveTodayStrategy(), config)

        elif strategy_name == 'googlebot':
            from helpers.article_strategies import GooglebotStrategy
            return LegacyStrategyAdapter(GooglebotStrategy(), config)

        elif strategy_name == 'playwright':
            from helpers.article_strategies import PlaywrightStrategy
            return LegacyStrategyAdapter(PlaywrightStrategy(), config)

        elif strategy_name == 'twelvefoot':
            from helpers.article_strategies import TwelveFtStrategy
            return LegacyStrategyAdapter(TwelveFtStrategy(), config)

        elif strategy_name == 'wayback_enhanced':
            from helpers.article_strategies import EnhancedWaybackMachineStrategy
            return LegacyStrategyAdapter(EnhancedWaybackMachineStrategy(), config)

        elif strategy_name == 'wayback':
            from helpers.article_strategies import WaybackMachineStrategy
            return LegacyStrategyAdapter(WaybackMachineStrategy(), config)

        elif strategy_name == 'firecrawl':
            try:
                from helpers.firecrawl_strategy import FirecrawlStrategy
                return LegacyStrategyAdapter(FirecrawlStrategy(config), config)
            except ImportError:
                return None

        else:
            return None

    except Exception as e:
        from helpers.utils import log_error
        log_error("", f"Failed to create strategy {strategy_name}: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    strategy = create_strategy('direct')
    if strategy:
        print(f"Created strategy: {strategy}")
        print(f"Metadata: {strategy.metadata}")
        print(f"Can handle example.com: {strategy.can_handle_url('https://example.com')}")