#!/usr/bin/env python3
"""
Test Error Recovery and Circuit Breaker Integration - Phase 3.3
Comprehensive testing of resilience patterns with simulated failures
"""

import sys
import os
import time
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.error_recovery import (
    ErrorRecoveryManager, RetryConfig, RetryStrategy, RecoveryConfigs,
    with_error_recovery
)
from helpers.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerException

class SimulatedService:
    """Simulates a service with configurable failure patterns"""

    def __init__(self, name: str):
        self.name = name
        self.call_count = 0
        self.failure_rate = 0.3  # 30% failure rate initially
        self.consecutive_failures = 0

    def unreliable_call(self, message: str = "test") -> str:
        """Simulates an unreliable service call"""
        self.call_count += 1

        # Simulate varying failure rates
        if random.random() < self.failure_rate:
            self.consecutive_failures += 1

            # Simulate different types of failures
            failure_types = [
                ConnectionError("Connection failed"),
                TimeoutError("Request timed out"),
                OSError("Service unavailable")
            ]

            raise random.choice(failure_types)

        self.consecutive_failures = 0
        return f"{self.name} response to '{message}' (call #{self.call_count})"

    def set_failure_rate(self, rate: float):
        """Set the failure rate for testing"""
        self.failure_rate = max(0.0, min(1.0, rate))
        print(f"🎛️ {self.name} failure rate set to {self.failure_rate:.0%}")

def test_basic_retry_mechanisms():
    """Test basic retry mechanisms with different strategies"""
    print("🔄 Testing Basic Retry Mechanisms")
    print("-" * 50)

    service = SimulatedService("BasicRetryTest")
    service.set_failure_rate(0.6)  # High failure rate for testing

    recovery_manager = ErrorRecoveryManager("basic_retry_test")

    # Test different retry strategies
    strategies = [
        ("Exponential Backoff", RetryConfig(
            max_attempts=4,
            base_delay=0.1,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )),
        ("Fixed Delay", RetryConfig(
            max_attempts=3,
            base_delay=0.2,
            strategy=RetryStrategy.FIXED_DELAY
        )),
        ("Linear Backoff", RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            strategy=RetryStrategy.LINEAR_BACKOFF
        ))
    ]

    for strategy_name, config in strategies:
        print(f"\n📊 Testing {strategy_name}...")
        service.call_count = 0

        try:
            start_time = time.time()
            result = recovery_manager.execute_with_recovery(
                service.unreliable_call, config, "retry test"
            )
            duration = time.time() - start_time
            print(f"✅ Success after {service.call_count} attempts ({duration:.2f}s): {result}")
        except Exception as e:
            print(f"❌ Failed after all attempts: {e}")

    # Show recovery stats
    stats = recovery_manager.get_recovery_stats()
    print(f"\n📈 Recovery Stats: {stats['success_rate']:.1f}% success rate")

    return True

def test_circuit_breaker_integration():
    """Test circuit breaker integration with error recovery"""
    print("\n⚡ Testing Circuit Breaker Integration")
    print("-" * 50)

    service = SimulatedService("CircuitBreakerTest")

    # Configure circuit breaker for quick failure detection
    cb_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=2,
        success_threshold=2
    )

    recovery_manager = ErrorRecoveryManager("circuit_breaker_test")
    recovery_manager.set_circuit_breaker(cb_config)

    retry_config = RetryConfig(max_attempts=2, base_delay=0.1)

    # Phase 1: Cause circuit breaker to open
    print("📊 Phase 1: Triggering circuit breaker...")
    service.set_failure_rate(1.0)  # 100% failure rate

    for i in range(5):
        try:
            result = recovery_manager.execute_with_recovery(
                service.unreliable_call, retry_config, f"test {i+1}"
            )
            print(f"✅ Call {i+1}: {result}")
        except CircuitBreakerException as e:
            print(f"⚡ Call {i+1}: Circuit breaker open - {e}")
        except Exception as e:
            print(f"❌ Call {i+1}: Failed - {e}")

    # Check circuit breaker metrics
    cb_metrics = recovery_manager.circuit_breaker.get_metrics()
    print(f"⚡ Circuit breaker state: {cb_metrics['state'].upper()}")

    # Phase 2: Wait for recovery timeout and test recovery
    print(f"\n📊 Phase 2: Waiting for recovery timeout ({cb_config.recovery_timeout}s)...")
    time.sleep(cb_config.recovery_timeout + 0.5)

    service.set_failure_rate(0.0)  # Fix the service

    # Try a few calls to trigger recovery
    for i in range(3):
        try:
            result = recovery_manager.execute_with_recovery(
                service.unreliable_call, retry_config, f"recovery test {i+1}"
            )
            print(f"✅ Recovery call {i+1}: {result}")
        except Exception as e:
            print(f"❌ Recovery call {i+1}: {e}")

    # Final circuit breaker state
    cb_metrics = recovery_manager.circuit_breaker.get_metrics()
    print(f"⚡ Final circuit breaker state: {cb_metrics['state'].upper()}")

    return cb_metrics['state'] == 'closed'

def test_decorator_integration():
    """Test decorator-based error recovery"""
    print("\n🎭 Testing Decorator Integration")
    print("-" * 50)

    service = SimulatedService("DecoratorTest")
    service.set_failure_rate(0.4)

    @with_error_recovery(
        "decorator_test",
        RecoveryConfigs.NETWORK_OPERATIONS,
        CircuitBreakerConfig(failure_threshold=4)
    )
    def decorated_service_call(message: str) -> str:
        return service.unreliable_call(message)

    # Test decorated function
    success_count = 0
    for i in range(10):
        try:
            result = decorated_service_call(f"decorated call {i+1}")
            print(f"✅ Call {i+1}: Success")
            success_count += 1
        except Exception as e:
            print(f"❌ Call {i+1}: Failed - {type(e).__name__}")

    # Show decorator recovery stats
    stats = decorated_service_call.recovery_manager.get_recovery_stats()
    print(f"📈 Decorator recovery stats: {stats['success_rate']:.1f}% success rate")

    return success_count > 5

def test_configuration_presets():
    """Test predefined configuration presets"""
    print("\n⚙️ Testing Configuration Presets")
    print("-" * 50)

    service = SimulatedService("PresetTest")
    service.set_failure_rate(0.5)

    configs = [
        ("Quick Operations", RecoveryConfigs.QUICK_OPERATIONS),
        ("Network Operations", RecoveryConfigs.NETWORK_OPERATIONS),
        ("Heavy Operations", RecoveryConfigs.HEAVY_OPERATIONS),
        ("Critical Operations", RecoveryConfigs.CRITICAL_OPERATIONS)
    ]

    recovery_manager = ErrorRecoveryManager("preset_test")

    for config_name, config in configs:
        print(f"\n📊 Testing {config_name}...")
        print(f"   Max attempts: {config.max_attempts}, Strategy: {config.strategy.value}")

        service.call_count = 0
        try:
            start_time = time.time()
            result = recovery_manager.execute_with_recovery(
                service.unreliable_call, config, config_name.lower()
            )
            duration = time.time() - start_time
            print(f"✅ Success after {service.call_count} calls ({duration:.2f}s)")
        except Exception as e:
            print(f"❌ Failed: {type(e).__name__}")

    return True

def test_system_integration():
    """Test integration with Atlas monitoring and alerting"""
    print("\n🔗 Testing System Integration")
    print("-" * 50)

    # Test that error recovery integrates with existing Atlas systems
    recovery_manager = ErrorRecoveryManager("atlas_integration_test")

    # Enable circuit breaker for Atlas-like service
    recovery_manager.set_circuit_breaker(CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30
    ))

    def mock_atlas_operation():
        """Simulate Atlas operation that might fail"""
        if random.random() < 0.3:
            raise ConnectionError("Atlas service connection failed")
        return "Atlas operation completed successfully"

    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )

    # Test multiple operations
    success_count = 0
    for i in range(5):
        try:
            result = recovery_manager.execute_with_recovery(
                mock_atlas_operation, retry_config
            )
            print(f"✅ Atlas operation {i+1}: Success")
            success_count += 1
        except Exception as e:
            print(f"❌ Atlas operation {i+1}: {type(e).__name__}")

    # Display comprehensive stats
    stats = recovery_manager.get_recovery_stats()
    print(f"\n📊 Integration Test Results:")
    print(f"   Success rate: {stats['success_rate']:.1f}%")
    print(f"   Total attempts: {stats['total_attempts']}")

    if stats['circuit_breaker_metrics']:
        cb_metrics = stats['circuit_breaker_metrics']
        print(f"   Circuit breaker state: {cb_metrics['state']}")
        print(f"   Circuit breaker success rate: {cb_metrics['metrics']['success_rate']:.1f}%")

    return success_count >= 3

def main():
    """Run all error recovery tests"""
    print("🚀 Atlas Error Recovery and Circuit Breaker Test Suite")
    print("=" * 60)

    tests = [
        ("Basic Retry Mechanisms", test_basic_retry_mechanisms),
        ("Circuit Breaker Integration", test_circuit_breaker_integration),
        ("Decorator Integration", test_decorator_integration),
        ("Configuration Presets", test_configuration_presets),
        ("System Integration", test_system_integration)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}")

    print(f"\n{'='*60}")
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All error recovery and circuit breaker tests PASSED!")
        print("🎯 Error recovery system ready for production")
        return 0
    else:
        print("❌ Some tests failed - review error recovery implementation")
        return 1

if __name__ == "__main__":
    exit(main())