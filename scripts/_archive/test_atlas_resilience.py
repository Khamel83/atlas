#!/usr/bin/env python3
"""
Test Atlas Resilience Integration - Phase 3.3
Tests the integrated resilience system across Atlas services
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.atlas_resilience import (
    AtlasResilienceManager,
    atlas_article_processing,
    atlas_database_operations,
    atlas_api_calls,
    atlas_llm_operations,
    execute_with_atlas_resilience,
    get_atlas_resilience_status,
    reset_atlas_resilience
)
import random
import time

def mock_article_processing_operation(url: str) -> str:
    """Mock article processing that might fail"""
    if random.random() < 0.2:  # 20% failure rate
        raise ConnectionError(f"Failed to fetch article from {url}")
    return f"Successfully processed article: {url}"

def mock_database_operation(query: str) -> str:
    """Mock database operation that might fail"""
    if random.random() < 0.1:  # 10% failure rate
        raise OSError("Database connection lost")
    return f"Query executed: {query}"

def mock_llm_operation(prompt: str) -> str:
    """Mock LLM operation that might fail"""
    if random.random() < 0.15:  # 15% failure rate
        raise TimeoutError("LLM request timed out")
    return f"LLM response to: {prompt[:50]}..."

def test_service_decorators():
    """Test Atlas service-specific decorators"""
    print("🎭 Testing Atlas Service Decorators")
    print("-" * 50)

    # Test article processing decorator
    @atlas_article_processing
    def process_article(url):
        return mock_article_processing_operation(url)

    # Test database decorator
    @atlas_database_operations
    def execute_query(query):
        return mock_database_operation(query)

    # Test LLM decorator
    @atlas_llm_operations
    def call_llm(prompt):
        return mock_llm_operation(prompt)

    # Test each service
    services = [
        ("Article Processing", process_article, "https://example.com/article1"),
        ("Database Operations", execute_query, "SELECT * FROM articles"),
        ("LLM Operations", call_llm, "Summarize this content for the user")
    ]

    success_counts = {}

    for service_name, service_func, test_input in services:
        print(f"\n📊 Testing {service_name}...")
        success_count = 0

        for i in range(10):
            try:
                result = service_func(test_input)
                print(f"✅ Call {i+1}: Success")
                success_count += 1
            except Exception as e:
                print(f"❌ Call {i+1}: {type(e).__name__}")

        success_counts[service_name] = success_count
        print(f"📈 {service_name}: {success_count}/10 successful calls")

    return all(count >= 7 for count in success_counts.values())

def test_execute_with_resilience():
    """Test direct resilience execution"""
    print("\n🔧 Testing Direct Resilience Execution")
    print("-" * 50)

    # Test different services using execute_with_atlas_resilience
    test_operations = [
        ("article_processing", mock_article_processing_operation, "https://test.com"),
        ("database_operations", mock_database_operation, "INSERT INTO test VALUES (1)"),
        ("llm_operations", mock_llm_operation, "Generate a test response"),
        ("api_calls", lambda x: f"API response for {x}", "test endpoint")
    ]

    success_count = 0

    for service_name, operation, test_input in test_operations:
        print(f"\n📊 Testing {service_name}...")

        try:
            result = execute_with_atlas_resilience(
                service_name, operation, test_input
            )
            print(f"✅ Success: {result[:80]}...")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed: {type(e).__name__}")

    print(f"📈 Direct execution: {success_count}/{len(test_operations)} successful")
    return success_count >= 3

def test_resilience_status():
    """Test system resilience status monitoring"""
    print("\n📊 Testing Resilience Status Monitoring")
    print("-" * 50)

    # Generate some activity across services
    services_to_test = [
        'article_processing',
        'database_operations',
        'api_calls',
        'search_operations'
    ]

    for service in services_to_test:
        for i in range(3):
            try:
                execute_with_atlas_resilience(
                    service,
                    lambda x: f"Test operation {x}" if random.random() > 0.3 else (_ for _ in ()).throw(ConnectionError("Test failure")),
                    f"test_{i}"
                )
            except Exception:
                pass  # Expected failures for testing

    # Get comprehensive status
    status = get_atlas_resilience_status()

    print(f"🏥 System Resilience Status:")
    print(f"   Total services: {status['summary']['total_services']}")
    print(f"   Healthy: {status['summary']['healthy_services']}")
    print(f"   Degraded: {status['summary']['degraded_services']}")
    print(f"   Failed: {status['summary']['failed_services']}")

    print(f"\n🔍 Service Details:")
    for service_name, service_status in status['services'].items():
        health = service_status.get('health', 'unknown')
        success_rate = service_status.get('success_rate', 0)
        cb_state = service_status.get('circuit_breaker_state', 'unknown')
        print(f"   {service_name}: {health} ({success_rate:.1f}% success, CB: {cb_state})")

    return len(status['services']) >= 4

def test_service_reset():
    """Test service reset functionality"""
    print("\n🔄 Testing Service Reset")
    print("-" * 50)

    # Create some failure history
    for i in range(5):
        try:
            execute_with_atlas_resilience(
                'test_service',
                lambda x: (_ for _ in ()).throw(ConnectionError("Intentional failure")),
                f"reset_test_{i}"
            )
        except Exception:
            pass

    # Check status before reset
    status_before = get_atlas_resilience_status()
    test_service_before = status_before['services'].get('test_service', {})

    print(f"📊 Before reset - Test service attempts: {test_service_before.get('total_attempts', 0)}")

    # Reset specific service
    reset_atlas_resilience('test_service')

    # Check status after reset
    status_after = get_atlas_resilience_status()
    test_service_after = status_after['services'].get('test_service', {})

    print(f"📊 After reset - Test service attempts: {test_service_after.get('total_attempts', 0)}")

    # Service should have fewer attempts after reset
    attempts_before = test_service_before.get('total_attempts', 0)
    attempts_after = test_service_after.get('total_attempts', 0)

    return attempts_after < attempts_before

def test_atlas_integration():
    """Test integration with existing Atlas components"""
    print("\n🔗 Testing Atlas Component Integration")
    print("-" * 50)

    # Simulate typical Atlas operations
    atlas_operations = [
        ("Article fetch and process", "article_processing", mock_article_processing_operation),
        ("Search index update", "search_operations", lambda x: f"Indexed: {x}"),
        ("Background content processing", "background_processing", lambda x: f"Processed: {x}"),
        ("API health check", "api_calls", lambda x: "API healthy")
    ]

    successful_integrations = 0

    for operation_name, service_name, operation_func in atlas_operations:
        print(f"\n🧪 Testing {operation_name}...")

        # Run operation multiple times to test resilience
        successes = 0
        for i in range(5):
            try:
                result = execute_with_atlas_resilience(
                    service_name,
                    operation_func,
                    f"test_data_{i}"
                )
                successes += 1
            except Exception as e:
                print(f"   Attempt {i+1}: {type(e).__name__}")

        success_rate = (successes / 5) * 100
        print(f"✅ {operation_name}: {success_rate:.0f}% success rate")

        if success_rate >= 60:  # Allow some failures for resilience testing
            successful_integrations += 1

    print(f"📈 Integration test: {successful_integrations}/{len(atlas_operations)} operations successful")
    return successful_integrations >= 3

def main():
    """Run all Atlas resilience tests"""
    print("🚀 Atlas Resilience Integration Test Suite")
    print("=" * 60)

    # Reset state before testing
    reset_atlas_resilience()

    tests = [
        ("Service Decorators", test_service_decorators),
        ("Direct Resilience Execution", test_execute_with_resilience),
        ("Resilience Status Monitoring", test_resilience_status),
        ("Service Reset", test_service_reset),
        ("Atlas Integration", test_atlas_integration)
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
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All Atlas resilience integration tests PASSED!")
        print("🎯 Atlas resilience system ready for production")

        # Show final system status
        print(f"\n🏥 Final System Status:")
        final_status = get_atlas_resilience_status()
        print(f"   Services monitored: {final_status['summary']['total_services']}")
        print(f"   Healthy services: {final_status['summary']['healthy_services']}")

        return 0
    else:
        print("❌ Some tests failed - review Atlas resilience implementation")
        return 1

if __name__ == "__main__":
    exit(main())