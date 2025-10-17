#!/usr/bin/env python3
"""
Atlas Resilience Integration - Phase 3.3
Integrates error recovery and circuit breakers throughout Atlas services
"""

import logging
from typing import Dict, Any, List
from pathlib import Path
import json

from .error_recovery import (
    ErrorRecoveryManager, RetryConfig, RecoveryConfigs,
    with_error_recovery
)
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig

class AtlasResilienceManager:
    """
    Central management of resilience patterns across Atlas services
    Provides pre-configured error recovery and circuit breakers for different Atlas components
    """

    def __init__(self, base_path: str = "/home/ubuntu/dev/atlas"):
        self.base_path = Path(base_path)
        self.config_file = self.base_path / "config" / "resilience_config.json"
        self.logger = logging.getLogger("AtlasResilience")

        # Recovery managers for different Atlas services
        self.recovery_managers: Dict[str, ErrorRecoveryManager] = {}

        # Initialize common Atlas service recovery managers
        self._initialize_service_managers()

    def _initialize_service_managers(self):
        """Initialize recovery managers for Atlas services"""

        # Article processing - Network heavy with potential timeouts
        self.recovery_managers['article_processing'] = (
            ErrorRecoveryManager('article_processing')
            .set_circuit_breaker(CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=120,
                success_threshold=3
            ))
        )

        # Database operations - Critical, need high reliability
        self.recovery_managers['database_operations'] = (
            ErrorRecoveryManager('database_operations')
            .set_circuit_breaker(CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
                success_threshold=2
            ))
        )

        # API calls - Quick operations, fast retry
        self.recovery_managers['api_calls'] = (
            ErrorRecoveryManager('api_calls')
            .set_circuit_breaker(CircuitBreakerConfig(
                failure_threshold=4,
                recovery_timeout=60,
                success_threshold=2
            ))
        )

        # LLM operations - Expensive, conservative retry
        self.recovery_managers['llm_operations'] = (
            ErrorRecoveryManager('llm_operations')
            .set_circuit_breaker(CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=180,
                success_threshold=2
            ))
        )

        # Background processing - Long-running, tolerant of delays
        self.recovery_managers['background_processing'] = (
            ErrorRecoveryManager('background_processing')
            .set_circuit_breaker(CircuitBreakerConfig(
                failure_threshold=7,
                recovery_timeout=300,
                success_threshold=3
            ))
        )

        # Search operations - User-facing, fast response needed
        self.recovery_managers['search_operations'] = (
            ErrorRecoveryManager('search_operations')
            .set_circuit_breaker(CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=45,
                success_threshold=2
            ))
        )

        self.logger.info(f"Initialized {len(self.recovery_managers)} Atlas service recovery managers")

    def get_recovery_manager(self, service_name: str) -> ErrorRecoveryManager:
        """Get recovery manager for specific Atlas service"""
        if service_name not in self.recovery_managers:
            # Create default recovery manager for unknown services
            self.recovery_managers[service_name] = (
                ErrorRecoveryManager(service_name)
                .set_circuit_breaker(CircuitBreakerConfig())
            )
            self.logger.info(f"Created default recovery manager for service: {service_name}")

        return self.recovery_managers[service_name]

    def execute_with_resilience(self, service_name: str, operation_func,
                               config: RetryConfig = None, *args, **kwargs):
        """Execute operation with service-specific resilience patterns"""
        recovery_manager = self.get_recovery_manager(service_name)

        # Use service-specific default config if none provided
        if config is None:
            config = self._get_default_config(service_name)

        return recovery_manager.execute_with_recovery(
            operation_func, config, *args, **kwargs
        )

    def _get_default_config(self, service_name: str) -> RetryConfig:
        """Get default retry config for service type"""
        service_configs = {
            'article_processing': RecoveryConfigs.NETWORK_OPERATIONS,
            'database_operations': RecoveryConfigs.CRITICAL_OPERATIONS,
            'api_calls': RecoveryConfigs.QUICK_OPERATIONS,
            'llm_operations': RecoveryConfigs.HEAVY_OPERATIONS,
            'background_processing': RecoveryConfigs.HEAVY_OPERATIONS,
            'search_operations': RecoveryConfigs.QUICK_OPERATIONS
        }

        return service_configs.get(service_name, RecoveryConfigs.NETWORK_OPERATIONS)

    def get_system_resilience_status(self) -> Dict[str, Any]:
        """Get comprehensive resilience status across all Atlas services"""
        from datetime import datetime
        status = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'summary': {
                'total_services': len(self.recovery_managers),
                'healthy_services': 0,
                'degraded_services': 0,
                'failed_services': 0,
                'circuit_breakers_open': 0
            }
        }

        for service_name, recovery_manager in self.recovery_managers.items():
            try:
                service_stats = recovery_manager.get_recovery_stats()

                # Determine service health
                success_rate = service_stats.get('success_rate', 100.0)
                circuit_breaker_state = 'closed'

                if service_stats.get('circuit_breaker_metrics'):
                    circuit_breaker_state = service_stats['circuit_breaker_metrics']['state']

                if circuit_breaker_state == 'open':
                    health = 'failed'
                    status['summary']['failed_services'] += 1
                    status['summary']['circuit_breakers_open'] += 1
                elif success_rate < 50:
                    health = 'degraded'
                    status['summary']['degraded_services'] += 1
                else:
                    health = 'healthy'
                    status['summary']['healthy_services'] += 1

                status['services'][service_name] = {
                    'health': health,
                    'success_rate': success_rate,
                    'circuit_breaker_state': circuit_breaker_state,
                    'total_attempts': service_stats.get('total_attempts', 0),
                    'last_attempt': service_stats.get('last_attempt')
                }

            except Exception as e:
                status['services'][service_name] = {
                    'health': 'unknown',
                    'error': str(e)
                }

        return status

    def create_service_decorator(self, service_name: str, config: RetryConfig = None):
        """Create decorator for specific Atlas service"""
        recovery_manager = self.get_recovery_manager(service_name)
        default_config = config or self._get_default_config(service_name)

        def decorator(func):
            def wrapper(*args, **kwargs):
                return recovery_manager.execute_with_recovery(
                    func, default_config, *args, **kwargs
                )

            wrapper.recovery_manager = recovery_manager
            wrapper.service_name = service_name
            return wrapper

        return decorator

    def reset_service(self, service_name: str):
        """Reset recovery state for specific service"""
        if service_name in self.recovery_managers:
            recovery_manager = self.recovery_managers[service_name]
            recovery_manager.clear_history()
            if recovery_manager.circuit_breaker:
                recovery_manager.circuit_breaker.reset()
            self.logger.info(f"Reset resilience state for service: {service_name}")

    def reset_all_services(self):
        """Reset all service recovery states"""
        for service_name in self.recovery_managers:
            self.reset_service(service_name)
        self.logger.info("Reset resilience state for all services")

# Global resilience manager instance
_atlas_resilience = AtlasResilienceManager()

# Convenience decorators for Atlas services
atlas_article_processing = _atlas_resilience.create_service_decorator('article_processing')
atlas_database_operations = _atlas_resilience.create_service_decorator('database_operations')
atlas_api_calls = _atlas_resilience.create_service_decorator('api_calls')
atlas_llm_operations = _atlas_resilience.create_service_decorator('llm_operations')
atlas_background_processing = _atlas_resilience.create_service_decorator('background_processing')
atlas_search_operations = _atlas_resilience.create_service_decorator('search_operations')

# Convenience functions
def execute_with_atlas_resilience(service_name: str, operation_func, *args, **kwargs):
    """Execute operation with Atlas resilience patterns"""
    return _atlas_resilience.execute_with_resilience(
        service_name, operation_func, None, *args, **kwargs
    )

def get_atlas_resilience_status():
    """Get Atlas system resilience status"""
    return _atlas_resilience.get_system_resilience_status()

def reset_atlas_resilience(service_name: str = None):
    """Reset Atlas resilience state"""
    if service_name:
        _atlas_resilience.reset_service(service_name)
    else:
        _atlas_resilience.reset_all_services()

# End of file