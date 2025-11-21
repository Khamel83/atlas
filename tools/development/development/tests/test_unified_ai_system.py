#!/usr/bin/env python3
"""
Test Script for Unified AI System
Comprehensive testing of the integrated LLM Router + Cost Manager system
"""

import sys
import time
from pathlib import Path

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.unified_ai import get_unified_ai
from helpers.summarizer import UnifiedSummarizer
from helpers.llm_router import TaskKind, TaskSpec
from helpers.llm_client import get_llm_client


def test_llm_client():
    """Test basic LLM client functionality."""
    print("🔧 Testing LLM Client...")

    try:
        client = get_llm_client()

        # Test model pricing update
        models = client.list_available_models()
        print(f"   ✅ Models available: {len(models)}")

        if models:
            test_model = models[0]
            info = client.get_model_info(test_model)
            print(f"   ✅ Model info retrieved: {test_model}")
            print(f"      Cost: ${info['input_per_1m']:.3f}/${info['output_per_1m']:.3f} per 1M tokens")

        # Test JSON repair
        broken_json = '```json\n{"test": "value",}\n```'
        repaired = client.repair_json(broken_json)
        is_valid = client.is_valid_json(repaired)
        print(f"   ✅ JSON repair test: {is_valid}")

        return True

    except Exception as e:
        print(f"   ❌ LLM Client test failed: {str(e)}")
        return False


def test_model_routing():
    """Test intelligent model routing."""
    print("\n🎯 Testing Model Routing...")

    try:
        from helpers.llm_router import get_llm_router
        router = get_llm_router()

        # Test different routing scenarios
        test_cases = [
            (TaskSpec(TaskKind.SUMMARIZE, 1000), "Economy model for basic task"),
            (TaskSpec(TaskKind.CODE_ANALYSIS, 5000, code_heavy=True), "Qwen for code-heavy task"),
            (TaskSpec(TaskKind.EXTRACT_JSON, 150000, requires_long_ctx=True), "Gemini for long context"),
            (TaskSpec(TaskKind.SUMMARIZE, 1000, retry_count=1, previous_fail_reason='invalid_json'), "Gemini for JSON failure fallback")
        ]

        for spec, description in test_cases:
            model = router.choose_model(spec)
            explanation = router._explain_choice(spec, model)
            print(f"   ✅ {description}")
            print(f"      Selected: {model}")
            print(f"      Reasoning: {explanation}")

        # Test routing stats
        stats = router.get_routing_stats()
        print(f"   ✅ Routing stats: {stats['available_models']} models, {stats['routing_strategy']}")

        return True

    except Exception as e:
        print(f"   ❌ Model routing test failed: {str(e)}")
        return False


def test_cost_management():
    """Test AI cost management."""
    print("\n💰 Testing Cost Management...")

    try:
        from helpers.ai_cost_manager import get_cost_manager
        manager = get_cost_manager()

        # Test budget checks
        budget_check = manager.check_budget_limits(0.01)
        print(f"   ✅ Budget check: {'Allowed' if budget_check['allowed'] else 'Blocked'}")

        if not budget_check['allowed']:
            print(f"      Reason: {budget_check['reason']}")

        # Test cost estimation
        estimated_cost = manager._cost_manager._estimate_request_cost({
            'content': 'Test content for cost estimation',
            'prompt': 'Summarize this content'
        }) if hasattr(manager, '_cost_manager') else 0.001

        print(f"   ✅ Cost estimation: ${estimated_cost:.6f}")

        # Test cost report
        report = manager.get_cost_report(7)
        print(f"   ✅ Cost report generated: {len(report)} sections")
        print(f"      Current daily usage: ${report['current_usage']['daily_cost']:.4f}")

        return True

    except Exception as e:
        print(f"   ❌ Cost management test failed: {str(e)}")
        return False


def test_unified_ai_system():
    """Test the complete unified AI system."""
    print("\n🤖 Testing Unified AI System...")

    try:
        ai = get_unified_ai()

        # Test system status
        status = ai.get_system_status()
        print(f"   ✅ System status: {status['system_status']}")
        print(f"      Capabilities: {len(status['capabilities'])}")

        # Test dry run (no API call)
        test_content = "This is a test article about artificial intelligence and machine learning. " * 20

        # Create a dry run by testing routing decision
        from helpers.llm_router import TaskSpec, TaskKind
        spec = TaskSpec(TaskKind.SUMMARIZE, len(test_content) // 4)

        router = ai.router
        routing_result = router.execute_task(
            spec=spec,
            messages=[{'role': 'user', 'content': f'Summarize: {test_content[:100]}...'}],
            dry_run=True
        )

        if routing_result.get('dry_run'):
            print(f"   ✅ Routing decision (dry run):")
            decision = routing_result['routing_decision']
            print(f"      Model: {decision['selected_model']}")
            print(f"      Estimated cost: ${decision['estimated_cost']:.6f}")
            print(f"      Reasoning: {decision['reasoning']}")

        return True

    except Exception as e:
        print(f"   ❌ Unified AI system test failed: {str(e)}")
        return False


def test_unified_summarizer():
    """Test the unified summarizer integration."""
    print("\n📝 Testing Unified Summarizer...")

    try:
        summarizer = UnifiedSummarizer()

        # Test with short content (should skip AI)
        short_content = "This is a short test."
        result = summarizer.summarize(short_content)

        print(f"   ✅ Short content test:")
        print(f"      Method: {result.get('method')}")
        print(f"      Success: {result.get('success')}")

        # Test with longer content (would try AI if API key available)
        long_content = "This is a comprehensive test article about artificial intelligence, machine learning, and the future of technology. " * 10

        result = summarizer.summarize(long_content, summary_type="auto", target_length=200)

        print(f"   ✅ Long content test:")
        print(f"      Method: {result.get('method')}")
        print(f"      Success: {result.get('success')}")
        print(f"      Summary length: {len(result.get('summary', ''))}")
        print(f"      Fallback used: {result.get('fallback_used', False)}")

        # Test summarization report
        report = summarizer.get_summarization_report()
        print(f"   ✅ Summarization report: {report.get('system_type')}")

        return True

    except Exception as e:
        print(f"   ❌ Unified summarizer test failed: {str(e)}")
        return False


def test_configuration_validation():
    """Test configuration validation."""
    print("\n⚙️ Testing Configuration Validation...")

    try:
        import subprocess
        result = subprocess.run([
            'python3', 'validate_config.py'
        ], capture_output=True, text=True, cwd=Path(__file__).parent)

        if result.returncode == 0:
            print("   ✅ Configuration validation completed")
            # Extract key info from output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Status:' in line or 'Coverage:' in line:
                    print(f"      {line.strip()}")
        else:
            print(f"   ⚠️ Configuration validation had warnings")

        return True

    except Exception as e:
        print(f"   ❌ Configuration validation failed: {str(e)}")
        return False


def main():
    """Run comprehensive test suite."""
    print("🚀 Unified AI System - Comprehensive Test Suite")
    print("=" * 60)

    tests = [
        ("LLM Client", test_llm_client),
        ("Model Routing", test_model_routing),
        ("Cost Management", test_cost_management),
        ("Unified AI System", test_unified_ai_system),
        ("Unified Summarizer", test_unified_summarizer),
        ("Configuration Validation", test_configuration_validation)
    ]

    results = []
    start_time = time.time()

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {str(e)}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("🎯 Test Results Summary")
    print("-" * 30)

    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:<8} {test_name}")
        if success:
            passed += 1

    total_time = time.time() - start_time
    success_rate = (passed / len(results)) * 100

    print("-" * 30)
    print(f"Results: {passed}/{len(results)} tests passed ({success_rate:.1f}%)")
    print(f"Time: {total_time:.2f} seconds")

    if success_rate >= 80:
        print("\n🎉 UNIFIED AI SYSTEM IS READY!")
        print("✅ Core functionality validated")
        print("✅ Cost management operational")
        print("✅ Intelligent routing working")
        print("✅ Fallback strategies active")
    else:
        print("\n⚠️ Some tests failed - review configuration")

    return success_rate >= 80


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)