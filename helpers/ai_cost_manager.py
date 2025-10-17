#!/usr/bin/env python3
"""
AI Cost Manager - Production-grade AI API cost management and monitoring
Addresses feedback: AI Feature Dependence & Cost, Graceful degradation
"""

import json
import os
import sqlite3
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from functools import wraps
from collections import defaultdict
import hashlib
import threading

from helpers.utils import log_info, log_error


@dataclass
class APIUsage:
    """Track API usage metrics."""
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    response_time: float
    success: bool
    error_type: Optional[str] = None


@dataclass
class CostLimits:
    """Cost limiting configuration."""
    daily_limit_usd: float = 10.0
    monthly_limit_usd: float = 100.0
    hourly_request_limit: int = 100
    max_tokens_per_request: int = 4000
    emergency_stop_threshold: float = 50.0  # Hard stop threshold


class AICostManager:
    """
    Comprehensive AI API cost management system.

    Features:
    - Real-time cost tracking and budget enforcement
    - Request rate limiting and token management
    - Graceful degradation with fallback strategies
    - Cost prediction and optimization
    - Usage analytics and reporting
    - Emergency stop mechanisms
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize AI Cost Manager."""
        self.config = config or {}

        # Database for cost tracking
        self.db_path = Path(self.config.get('cost_db', 'data/ai_costs.db'))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Cost limits
        self.limits = CostLimits(
            daily_limit_usd=self.config.get('daily_ai_budget', 10.0),
            monthly_limit_usd=self.config.get('monthly_ai_budget', 100.0),
            hourly_request_limit=self.config.get('hourly_request_limit', 100),
            max_tokens_per_request=self.config.get('max_tokens_per_request', 4000),
            emergency_stop_threshold=self.config.get('emergency_stop_threshold', 50.0)
        )

        # Rate limiting
        self.request_history = defaultdict(list)
        self.cost_cache = {}

        # Thread safety
        self.cost_lock = threading.RLock()

        # API configurations
        self.api_configs = {
            'openrouter': {
                'base_url': 'https://openrouter.ai/api/v1',
                'api_key': self.config.get('openrouter_api_key', ''),
                'cost_per_1k_input': 0.0005,  # Default estimate
                'cost_per_1k_output': 0.0015,  # Default estimate
                'timeout': self.config.get('api_timeout', 30)
            },
            # Add other providers as needed
        }

        # Fallback strategies
        self.fallback_strategies = [
            'cache_lookup',
            'simple_extraction',
            'keyword_based',
            'template_based',
            'skip_ai_features'
        ]

        # Set up logging
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'ai_cost_manager.log')

        # Initialize database
        self._init_cost_database()

        # Load current usage
        self.current_usage = self._get_current_usage()

        log_info(self.log_path, "AI Cost Manager initialized with budget enforcement")

    def _init_cost_database(self):
        """Initialize cost tracking database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # API usage tracking
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS api_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        input_tokens INTEGER DEFAULT 0,
                        output_tokens INTEGER DEFAULT 0,
                        total_tokens INTEGER DEFAULT 0,
                        cost_usd REAL DEFAULT 0.0,
                        response_time REAL DEFAULT 0.0,
                        success BOOLEAN DEFAULT TRUE,
                        error_type TEXT,
                        metadata TEXT
                    )
                ''')

                # Cost budgets and limits
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS cost_budgets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        period_type TEXT NOT NULL, -- 'daily', 'monthly', 'hourly'
                        period_start TEXT NOT NULL,
                        budget_usd REAL NOT NULL,
                        spent_usd REAL DEFAULT 0.0,
                        requests_made INTEGER DEFAULT 0,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Cache for AI responses to reduce costs
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS ai_response_cache (
                        cache_key TEXT PRIMARY KEY,
                        request_hash TEXT NOT NULL,
                        response_data TEXT NOT NULL,
                        tokens_saved INTEGER DEFAULT 0,
                        cost_saved REAL DEFAULT 0.0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        expires_at TEXT
                    )
                ''')

                # Fallback usage tracking
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS fallback_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        operation TEXT NOT NULL,
                        fallback_strategy TEXT NOT NULL,
                        reason TEXT,
                        success BOOLEAN DEFAULT TRUE,
                        metadata TEXT
                    )
                ''')

                # Create indexes for performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON api_usage(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_usage_provider ON api_usage(provider)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires ON ai_response_cache(expires_at)')

            log_info(self.log_path, "AI cost database initialized")

        except Exception as e:
            log_error(self.log_path, f"Error initializing cost database: {str(e)}")

    def _get_current_usage(self) -> Dict[str, float]:
        """Get current usage statistics."""
        try:
            usage = {
                'daily_cost': 0.0,
                'monthly_cost': 0.0,
                'hourly_requests': 0,
                'total_requests_today': 0
            }

            now = datetime.now()
            today = now.strftime('%Y-%m-%d')
            this_month = now.strftime('%Y-%m')
            this_hour = now.strftime('%Y-%m-%d %H')

            with sqlite3.connect(self.db_path) as conn:
                # Daily cost
                daily_cost = conn.execute('''
                    SELECT SUM(cost_usd) FROM api_usage
                    WHERE date(timestamp) = ?
                ''', (today,)).fetchone()[0]
                usage['daily_cost'] = daily_cost or 0.0

                # Monthly cost
                monthly_cost = conn.execute('''
                    SELECT SUM(cost_usd) FROM api_usage
                    WHERE strftime('%Y-%m', timestamp) = ?
                ''', (this_month,)).fetchone()[0]
                usage['monthly_cost'] = monthly_cost or 0.0

                # Hourly requests
                hourly_requests = conn.execute('''
                    SELECT COUNT(*) FROM api_usage
                    WHERE strftime('%Y-%m-%d %H', timestamp) = ?
                ''', (this_hour,)).fetchone()[0]
                usage['hourly_requests'] = hourly_requests or 0

                # Daily requests
                daily_requests = conn.execute('''
                    SELECT COUNT(*) FROM api_usage
                    WHERE date(timestamp) = ?
                ''', (today,)).fetchone()[0]
                usage['total_requests_today'] = daily_requests or 0

            return usage

        except Exception as e:
            log_error(self.log_path, f"Error getting current usage: {str(e)}")
            return {'daily_cost': 0.0, 'monthly_cost': 0.0, 'hourly_requests': 0, 'total_requests_today': 0}

    def check_budget_limits(self, estimated_cost: float = 0.0) -> Dict[str, Any]:
        """Check if request would exceed budget limits."""
        with self.cost_lock:
            # Refresh current usage
            self.current_usage = self._get_current_usage()

            status = {
                'allowed': True,
                'reason': None,
                'current_usage': self.current_usage,
                'limits': {
                    'daily_limit': self.limits.daily_limit_usd,
                    'monthly_limit': self.limits.monthly_limit_usd,
                    'hourly_request_limit': self.limits.hourly_request_limit
                },
                'estimated_new_total': {
                    'daily': self.current_usage['daily_cost'] + estimated_cost,
                    'monthly': self.current_usage['monthly_cost'] + estimated_cost
                }
            }

            # Emergency stop check
            if self.current_usage['monthly_cost'] > self.limits.emergency_stop_threshold:
                status['allowed'] = False
                status['reason'] = f"Emergency stop: Monthly cost ${self.current_usage['monthly_cost']:.2f} exceeds emergency threshold ${self.limits.emergency_stop_threshold}"
                return status

            # Daily limit check
            if self.current_usage['daily_cost'] + estimated_cost > self.limits.daily_limit_usd:
                status['allowed'] = False
                status['reason'] = f"Daily budget exceeded: ${self.current_usage['daily_cost'] + estimated_cost:.2f} > ${self.limits.daily_limit_usd}"
                return status

            # Monthly limit check
            if self.current_usage['monthly_cost'] + estimated_cost > self.limits.monthly_limit_usd:
                status['allowed'] = False
                status['reason'] = f"Monthly budget exceeded: ${self.current_usage['monthly_cost'] + estimated_cost:.2f} > ${self.limits.monthly_limit_usd}"
                return status

            # Rate limit check
            if self.current_usage['hourly_requests'] >= self.limits.hourly_request_limit:
                status['allowed'] = False
                status['reason'] = f"Hourly rate limit exceeded: {self.current_usage['hourly_requests']} >= {self.limits.hourly_request_limit}"
                return status

            return status

    def with_cost_management(self, operation: str, fallback_strategies: List[str] = None):
        """Decorator for AI operations with cost management and graceful degradation."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Dict[str, Any]:
                start_time = time.time()

                # Estimate cost if possible
                estimated_cost = self._estimate_request_cost(kwargs)

                # Check budget limits
                budget_check = self.check_budget_limits(estimated_cost)

                if not budget_check['allowed']:
                    log_info(self.log_path, f"AI request blocked: {budget_check['reason']}")

                    # Try fallback strategies
                    fallback_result = self._try_fallback_strategies(
                        operation,
                        fallback_strategies or self.fallback_strategies,
                        *args, **kwargs
                    )

                    if fallback_result['success']:
                        return fallback_result
                    else:
                        return {
                            'success': False,
                            'error': budget_check['reason'],
                            'fallback_attempted': True,
                            'fallback_result': fallback_result
                        }

                # Check cache first
                cache_key = self._generate_cache_key(operation, args, kwargs)
                cached_result = self._get_cached_response(cache_key)

                if cached_result:
                    log_info(self.log_path, f"AI request served from cache: {operation}")
                    self._record_cache_hit(operation, estimated_cost)
                    return cached_result

                # Execute the AI function
                try:
                    result = func(*args, **kwargs)

                    # Record successful usage
                    actual_cost = result.get('cost', estimated_cost)
                    response_time = time.time() - start_time

                    self._record_api_usage(
                        operation=operation,
                        cost=actual_cost,
                        response_time=response_time,
                        success=True,
                        tokens_used=result.get('tokens_used', 0),
                        metadata=result.get('metadata', {})
                    )

                    # Cache successful results
                    if result.get('success'):
                        self._cache_response(cache_key, result, estimated_cost)

                    return result

                except Exception as e:
                    log_error(self.log_path, f"AI request failed for {operation}: {str(e)}")

                    # Record failed usage
                    response_time = time.time() - start_time
                    self._record_api_usage(
                        operation=operation,
                        cost=0.0,
                        response_time=response_time,
                        success=False,
                        error_type=type(e).__name__,
                        metadata={'error': str(e)}
                    )

                    # Try fallback strategies
                    fallback_result = self._try_fallback_strategies(
                        operation,
                        fallback_strategies or self.fallback_strategies,
                        *args, **kwargs
                    )

                    if fallback_result['success']:
                        return fallback_result
                    else:
                        return {
                            'success': False,
                            'error': str(e),
                            'fallback_attempted': True,
                            'fallback_result': fallback_result
                        }

            return wrapper
        return decorator

    def _estimate_request_cost(self, request_data: Dict[str, Any]) -> float:
        """Estimate the cost of an API request."""
        try:
            # Basic estimation based on content length
            content = request_data.get('content', '')
            prompt = request_data.get('prompt', '')

            # Rough token estimation (1 token ≈ 4 characters)
            input_chars = len(content) + len(prompt)
            estimated_input_tokens = input_chars // 4

            # Estimate output tokens (usually 10-20% of input for summaries)
            estimated_output_tokens = max(100, estimated_input_tokens // 5)

            # Use OpenRouter pricing as default
            cost_per_1k_input = self.api_configs['openrouter']['cost_per_1k_input']
            cost_per_1k_output = self.api_configs['openrouter']['cost_per_1k_output']

            estimated_cost = (
                (estimated_input_tokens / 1000) * cost_per_1k_input +
                (estimated_output_tokens / 1000) * cost_per_1k_output
            )

            return round(estimated_cost, 4)

        except Exception as e:
            log_error(f"Error estimating request cost: {str(e)}")
            return 0.01  # Default small cost estimate

    def _generate_cache_key(self, operation: str, args: tuple, kwargs: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        try:
            # Create deterministic cache key
            cache_data = {
                'operation': operation,
                'args': args,
                'kwargs': {k: v for k, v in kwargs.items() if k not in ['api_key', 'timestamp']}
            }

            cache_string = json.dumps(cache_data, sort_keys=True)
            return hashlib.md5(cache_string.encode()).hexdigest()

        except Exception:
            return f"{operation}_{hash(str(args) + str(kwargs))}"

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached AI response."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute('''
                    SELECT response_data, cost_saved FROM ai_response_cache
                    WHERE cache_key = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
                ''', (cache_key,)).fetchone()

                if result:
                    response_data, cost_saved = result
                    return json.loads(response_data)

        except Exception as e:
            log_error(f"Error getting cached response: {str(e)}")

        return None

    def _cache_response(self, cache_key: str, response: Dict[str, Any], cost_saved: float):
        """Cache AI response."""
        try:
            # Set expiry (24 hours for most responses)
            expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO ai_response_cache
                    (cache_key, request_hash, response_data, cost_saved, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    cache_key,
                    cache_key[:32],  # Short hash for indexing
                    json.dumps(response),
                    cost_saved,
                    expires_at
                ))

        except Exception as e:
            log_error(f"Error caching response: {str(e)}")

    def _record_cache_hit(self, operation: str, cost_saved: float):
        """Record cache hit statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO fallback_usage (operation, fallback_strategy, reason, success, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    operation,
                    'cache_hit',
                    'Response served from cache',
                    True,
                    json.dumps({'cost_saved': cost_saved})
                ))

        except Exception as e:
            log_error(f"Error recording cache hit: {str(e)}")

    def _record_api_usage(self, operation: str, cost: float, response_time: float,
                         success: bool, tokens_used: int = 0, error_type: str = None,
                         metadata: Dict[str, Any] = None):
        """Record API usage statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO api_usage
                    (timestamp, provider, model, operation, total_tokens, cost_usd,
                     response_time, success, error_type, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    'openrouter',  # Default provider
                    'auto',  # Model selection
                    operation,
                    tokens_used,
                    cost,
                    response_time,
                    success,
                    error_type,
                    json.dumps(metadata or {})
                ))

        except Exception as e:
            log_error(f"Error recording API usage: {str(e)}")

    def _try_fallback_strategies(self, operation: str, strategies: List[str], *args, **kwargs) -> Dict[str, Any]:
        """Try fallback strategies when AI is unavailable."""
        for strategy in strategies:
            try:
                result = self._execute_fallback_strategy(strategy, operation, *args, **kwargs)

                if result.get('success'):
                    log_info(f"Fallback strategy '{strategy}' successful for {operation}")

                    # Record fallback usage
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute('''
                            INSERT INTO fallback_usage (operation, fallback_strategy, success, metadata)
                            VALUES (?, ?, ?, ?)
                        ''', (operation, strategy, True, json.dumps(result.get('metadata', {}))))

                    return {**result, 'fallback_used': strategy}

            except Exception as e:
                log_error(f"Fallback strategy '{strategy}' failed: {str(e)}")
                continue

        # All fallback strategies failed
        return {
            'success': False,
            'error': 'All fallback strategies failed',
            'strategies_attempted': strategies
        }

    def _execute_fallback_strategy(self, strategy: str, operation: str, *args, **kwargs) -> Dict[str, Any]:
        """Execute a specific fallback strategy."""
        content = kwargs.get('content', '')

        if strategy == 'simple_extraction' and operation == 'summarize':
            # Extract first few sentences as summary
            sentences = content.split('. ')[:3]
            summary = '. '.join(sentences) + '.' if sentences else content[:200]

            return {
                'success': True,
                'summary': summary,
                'method': 'extractive_fallback',
                'metadata': {'strategy': strategy}
            }

        elif strategy == 'keyword_based' and operation == 'summarize':
            # Extract key phrases and create summary
            words = content.lower().split()
            word_freq = Counter(words)

            # Get most common meaningful words
            common_words = [word for word, count in word_freq.most_common(10)
                          if len(word) > 4 and word.isalpha()]

            summary = f"Key topics: {', '.join(common_words[:5])}. "
            summary += content.split('.')[0] + '.' if content else "Content summary unavailable."

            return {
                'success': True,
                'summary': summary,
                'method': 'keyword_fallback',
                'metadata': {'keywords': common_words[:5], 'strategy': strategy}
            }

        elif strategy == 'template_based':
            # Use template-based response
            return {
                'success': True,
                'summary': f"Content processed using template strategy. Length: {len(content)} characters.",
                'method': 'template_fallback',
                'metadata': {'strategy': strategy}
            }

        elif strategy == 'skip_ai_features':
            # Return minimal result indicating AI features are skipped
            return {
                'success': True,
                'summary': "AI features temporarily unavailable due to budget limits.",
                'method': 'skip_fallback',
                'metadata': {'strategy': strategy, 'ai_skipped': True}
            }

        return {'success': False, 'error': f'Unknown fallback strategy: {strategy}'}

    def get_cost_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive cost and usage report."""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'period_days': days,
                'current_usage': self.current_usage,
                'budget_status': {},
                'cost_breakdown': {},
                'usage_trends': {},
                'fallback_statistics': {},
                'recommendations': []
            }

            # Budget status
            report['budget_status'] = {
                'daily_remaining': max(0, self.limits.daily_limit_usd - self.current_usage['daily_cost']),
                'monthly_remaining': max(0, self.limits.monthly_limit_usd - self.current_usage['monthly_cost']),
                'daily_utilization_percent': (self.current_usage['daily_cost'] / self.limits.daily_limit_usd) * 100,
                'monthly_utilization_percent': (self.current_usage['monthly_cost'] / self.limits.monthly_limit_usd) * 100,
                'emergency_stop_triggered': self.current_usage['monthly_cost'] > self.limits.emergency_stop_threshold
            }

            # Cost breakdown and trends
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                # Cost by operation
                operation_costs = conn.execute('''
                    SELECT operation, SUM(cost_usd), COUNT(*)
                    FROM api_usage
                    WHERE timestamp > ? AND success = 1
                    GROUP BY operation
                    ORDER BY SUM(cost_usd) DESC
                ''', (cutoff_date,)).fetchall()

                report['cost_breakdown']['by_operation'] = [
                    {'operation': op, 'cost': cost, 'requests': count}
                    for op, cost, count in operation_costs
                ]

                # Daily cost trend
                daily_costs = conn.execute('''
                    SELECT date(timestamp) as day, SUM(cost_usd)
                    FROM api_usage
                    WHERE timestamp > ? AND success = 1
                    GROUP BY date(timestamp)
                    ORDER BY day DESC
                    LIMIT 30
                ''', (cutoff_date,)).fetchall()

                report['usage_trends']['daily_costs'] = [
                    {'date': day, 'cost': cost} for day, cost in daily_costs
                ]

                # Success rate
                success_stats = conn.execute('''
                    SELECT success, COUNT(*)
                    FROM api_usage
                    WHERE timestamp > ?
                    GROUP BY success
                ''', (cutoff_date,)).fetchall()

                total_requests = sum(count for _, count in success_stats)
                successful_requests = next((count for success, count in success_stats if success), 0)

                report['usage_trends']['success_rate'] = (successful_requests / total_requests * 100) if total_requests > 0 else 0

                # Fallback statistics
                fallback_stats = conn.execute('''
                    SELECT fallback_strategy, COUNT(*), SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)
                    FROM fallback_usage
                    WHERE timestamp > ?
                    GROUP BY fallback_strategy
                ''', (cutoff_date,)).fetchall()

                report['fallback_statistics'] = [
                    {
                        'strategy': strategy,
                        'total_uses': total,
                        'successful_uses': successful,
                        'success_rate': (successful / total * 100) if total > 0 else 0
                    }
                    for strategy, total, successful in fallback_stats
                ]

            # Recommendations
            if report['budget_status']['monthly_utilization_percent'] > 80:
                report['recommendations'].append("Monthly budget utilization is high - consider optimizing AI usage")

            if report['usage_trends']['success_rate'] < 90:
                report['recommendations'].append("AI request success rate is low - check API connectivity")

            cache_hits = sum(1 for fs in report['fallback_statistics'] if fs['strategy'] == 'cache_hit')
            if cache_hits < (total_requests * 0.2):  # Less than 20% cache hits
                report['recommendations'].append("Low cache hit rate - consider increasing cache TTL")

            return report

        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Global cost manager instance
_cost_manager = None

def get_cost_manager(config: Dict[str, Any] = None) -> AICostManager:
    """Get global cost manager instance."""
    global _cost_manager
    if _cost_manager is None:
        _cost_manager = AICostManager(config)
    return _cost_manager


def with_ai_cost_management(operation: str, fallback_strategies: List[str] = None):
    """Decorator for AI operations with cost management."""
    return get_cost_manager().with_cost_management(operation, fallback_strategies)


if __name__ == "__main__":
    # Test cost manager
    manager = AICostManager()

    print("🎯 AI Cost Manager - Test Mode")
    print("=" * 50)

    # Test budget check
    budget_check = manager.check_budget_limits(0.01)
    print(f"Budget check: {'✅ Allowed' if budget_check['allowed'] else '❌ Blocked'}")

    if not budget_check['allowed']:
        print(f"Reason: {budget_check['reason']}")

    # Test cost report
    report = manager.get_cost_report(7)
    print(f"Weekly cost report generated: {len(report)} sections")
    print(f"Current daily usage: ${report['current_usage']['daily_cost']:.4f}")
    print(f"Monthly budget utilization: {report['budget_status']['monthly_utilization_percent']:.1f}%")