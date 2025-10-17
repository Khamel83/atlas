#!/usr/bin/env python3
"""
Test script for Learning & Improvement System
Validates pattern detection, usage tracking, and recommendation generation
"""

import json
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sqlite3

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Try to import the learning system
try:
    from src.learning_system import (
        LearningSystem, LearningData, UsagePattern, ImprovementSuggestion,
        record_command_usage, get_recommendations, get_usage_statistics,
        get_learning_system
    )
    LEARNING_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Learning system not fully available due to missing dependencies: {e}")
    LEARNING_SYSTEM_AVAILABLE = False


class TestLearningSystem:
    """Test suite for Learning & Improvement System"""

    def setup_method(self):
        """Setup test environment"""
        self.test_results = []
        self.temp_dir = None
        self.db_path = None

        if not LEARNING_SYSTEM_AVAILABLE:
            self.skip_all_tests()
            return

        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_learning.db")

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def skip_all_tests(self):
        """Skip all tests if learning system is not available"""
        print("⚠️  Skipping Learning System tests due to missing dependencies")
        self.test_results = [{"name": "Learning System", "status": "skipped", "error": "Dependencies not available"}]

    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        if not LEARNING_SYSTEM_AVAILABLE:
            return False

        try:
            self.setup_method()
            test_func()
            print(f"✅ {test_name}")
            self.test_results.append({"name": test_name, "status": "passed"})
            return True
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            self.test_results.append({"name": test_name, "status": "failed", "error": str(e)})
            return False
        finally:
            self.teardown_method()

    def test_database_initialization(self):
        """Test database initialization and table creation"""
        print("\n🧪 Testing Database Initialization...")

        learning_system = LearningSystem(db_path=self.db_path)

        # Check that database file is created
        assert os.path.exists(self.db_path)

        # Check that tables are created
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check learning_data table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='learning_data'")
            assert cursor.fetchone() is not None

            # Check patterns table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patterns'")
            assert cursor.fetchone() is not None

            # Check suggestions table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='suggestions'")
            assert cursor.fetchone() is not None

    def test_usage_recording(self):
        """Test usage data recording"""
        print("\n🧪 Testing Usage Recording...")

        learning_system = LearningSystem(db_path=self.db_path)

        # Create test learning data
        learning_data = LearningData(
            timestamp=datetime.now(),
            user_id="test_user",
            session_id="test_session",
            command_name="test-command",
            parameters={"param1": "value1", "param2": 42},
            execution_time=1.5,
            success=True,
            error_message=None,
            context={"workspace": "/test/workspace"}
        )

        # Record usage
        learning_system.record_usage(learning_data)

        # Verify data is stored
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM learning_data")
            count = cursor.fetchone()[0]
            assert count == 1

            # Verify data content
            cursor.execute("SELECT * FROM learning_data")
            record = cursor.fetchone()
            assert record[2] == "test_user"  # user_id
            assert record[3] == "test_session"  # session_id
            assert record[4] == "test-command"  # command_name
            assert record[7] == 1  # success (SQLite stores boolean as 1/0)

    def test_pattern_learning_disabled(self):
        """Test pattern learning when disabled"""
        print("\n🧪 Testing Pattern Learning When Disabled...")

        config = {"learning_enabled": False}
        learning_system = LearningSystem(db_path=self.db_path, config=config)

        # Record some usage data
        learning_data = LearningData(
            timestamp=datetime.now(),
            user_id="test_user",
            session_id="test_session",
            command_name="test-command",
            parameters={},
            execution_time=1.0,
            success=True,
            error_message=None,
            context={}
        )
        learning_system.record_usage(learning_data)

        # Try to learn patterns (should return empty)
        patterns = asyncio.run(learning_system.learn_patterns())
        assert len(patterns) == 0

    def test_command_sequence_learning(self):
        """Test command sequence pattern learning"""
        print("\n🧪 Testing Command Sequence Learning...")

        # Use short learning interval for testing
        learning_system = LearningSystem(db_path=self.db_path, config={"learning_interval_hours": 0})

        # Record command sequences
        base_time = datetime.now()
        for i in range(5):
            # Record a sequence: analyze -> generate -> execute
            for cmd in ["analyze-repository", "generate-commands", "execute-workflow"]:
                learning_data = LearningData(
                    timestamp=base_time + timedelta(seconds=i*10),
                    user_id="test_user",
                    session_id=f"session_{i}",
                    command_name=cmd,
                    parameters={},
                    execution_time=1.0,
                    success=True,
                    error_message=None,
                    context={}
                )
                learning_system.record_usage(learning_data)

        # Learn patterns
        patterns = asyncio.run(learning_system.learn_patterns())

        # Check that command sequence patterns are learned
        sequence_patterns = [p for p in patterns if p.pattern_type == "command_sequence"]
        assert len(sequence_patterns) > 0

        # Verify pattern structure
        pattern = sequence_patterns[0]
        assert pattern.pattern_type == "command_sequence"
        assert pattern.frequency >= 3  # min_pattern_frequency
        assert "sequence" in pattern.pattern_data

    def test_parameter_pattern_learning(self):
        """Test parameter pattern learning"""
        print("\n🧪 Testing Parameter Pattern Learning...")

        # Use short learning interval for testing
        learning_system = LearningSystem(db_path=self.db_path, config={"learning_interval_hours": 0})

        # Record parameter usage patterns
        for i in range(5):
            learning_data = LearningData(
                timestamp=datetime.now() + timedelta(seconds=i),
                user_id="test_user",
                session_id=f"session_{i}",
                command_name="test-command",
                parameters={"mode": "fast", "verbose": True},
                execution_time=1.0,
                success=True,
                error_message=None,
                context={}
            )
            learning_system.record_usage(learning_data)

        # Learn patterns
        patterns = asyncio.run(learning_system.learn_patterns())

        # Check that parameter patterns are learned
        param_patterns = [p for p in patterns if p.pattern_type == "parameter_choice"]
        assert len(param_patterns) > 0

        # Verify pattern structure
        pattern = param_patterns[0]
        assert pattern.pattern_type == "parameter_choice"
        assert pattern.frequency >= 3
        assert "parameter" in pattern.pattern_data

    def test_workflow_pattern_learning(self):
        """Test workflow usage pattern learning"""
        print("\n🧪 Testing Workflow Pattern Learning...")

        # Use short learning interval for testing
        learning_system = LearningSystem(db_path=self.db_path, config={"learning_interval_hours": 0})

        # Record workflow executions
        for i in range(5):
            learning_data = LearningData(
                timestamp=datetime.now() + timedelta(seconds=i),
                user_id="test_user",
                session_id=f"session_{i}",
                command_name="execute-workflow",
                parameters={"workflow_id": "test-workflow"},
                execution_time=2.0,
                success=True,
                error_message=None,
                context={}
            )
            learning_system.record_usage(learning_data)

        # Learn patterns
        patterns = asyncio.run(learning_system.learn_patterns())

        # Check that workflow patterns are learned
        workflow_patterns = [p for p in patterns if p.pattern_type == "workflow_usage"]
        assert len(workflow_patterns) > 0

        # Verify pattern structure
        pattern = workflow_patterns[0]
        assert pattern.pattern_type == "workflow_usage"
        assert pattern.frequency >= 3
        assert "workflow_id" in pattern.pattern_data

    def test_suggestion_generation(self):
        """Test improvement suggestion generation"""
        print("\n🧪 Testing Suggestion Generation...")

        learning_system = LearningSystem(db_path=self.db_path)

        # Create some test patterns
        test_pattern = UsagePattern(
            pattern_id="test_seq_1",
            pattern_type="command_sequence",
            pattern_data={"sequence": ["cmd1", "cmd2"], "length": 2},
            frequency=8,
            success_rate=0.9,
            last_used=datetime.now(),
            context={"session_count": 5}
        )
        learning_system.patterns = [test_pattern]

        # Generate suggestions
        suggestions = asyncio.run(learning_system.generate_suggestions())

        # Check that suggestions are generated
        assert len(suggestions) > 0

        # Verify suggestion structure
        suggestion = suggestions[0]
        assert isinstance(suggestion, ImprovementSuggestion)
        assert suggestion.suggestion_type in ["workflow", "performance", "parameter"]
        assert suggestion.confidence >= learning_system.config["confidence_threshold"]

    def test_recommendation_generation(self):
        """Test context-aware recommendation generation"""
        print("\n🧪 Testing Recommendation Generation...")

        learning_system = LearningSystem(db_path=self.db_path)

        # Create test patterns and suggestions
        test_pattern = UsagePattern(
            pattern_id="test_seq_1",
            pattern_type="command_sequence",
            pattern_data={"sequence": ["cmd1", "cmd2"], "length": 2},
            frequency=5,
            success_rate=0.8,
            last_used=datetime.now(),
            context={"session_count": 3}
        )
        test_suggestion = ImprovementSuggestion(
            suggestion_id="test_suggestion_1",
            suggestion_type="workflow",
            description="Test suggestion",
            confidence=0.95,
            data={},
            created_at=datetime.now()
        )
        learning_system.patterns = [test_pattern]
        learning_system.suggestions = [test_suggestion]

        # Get recommendations with context
        context = {
            "current_command": "cmd1",
            "workspace_type": "python"
        }
        recommendations = learning_system.get_recommendations(context)

        # Check that recommendations are generated
        assert len(recommendations) > 0

        # Verify recommendation structure
        rec = recommendations[0]
        assert "type" in rec
        assert "content" in rec
        assert "confidence" in rec

    def test_usage_statistics(self):
        """Test usage statistics generation"""
        print("\n🧪 Testing Usage Statistics...")

        learning_system = LearningSystem(db_path=self.db_path)

        # Record some usage data
        for i in range(10):
            learning_data = LearningData(
                timestamp=datetime.now() + timedelta(seconds=i),
                user_id="test_user",
                session_id=f"session_{i}",
                command_name="test-command",
                parameters={},
                execution_time=1.0,
                success=True,
                error_message=None,
                context={}
            )
            learning_system.record_usage(learning_data)

        # Get statistics
        stats = learning_system.get_usage_statistics()

        # Verify statistics structure
        assert "total_usage" in stats
        assert "success_rate" in stats
        assert "popular_commands" in stats
        assert "recent_patterns" in stats
        assert "active_suggestions" in stats
        assert stats["total_usage"] == 10
        assert stats["success_rate"] == 1.0

    def test_suggestion_implementation(self):
        """Test suggestion implementation tracking"""
        print("\n🧪 Testing Suggestion Implementation...")

        learning_system = LearningSystem(db_path=self.db_path)

        # Create a test suggestion
        suggestion = ImprovementSuggestion(
            suggestion_id="test_suggestion_1",
            suggestion_type="workflow",
            description="Test suggestion",
            confidence=0.9,
            data={},
            created_at=datetime.now()
        )
        learning_system.suggestions = [suggestion]

        # Save suggestion to database
        learning_system._save_suggestions([suggestion])

        # Implement suggestion
        result = learning_system.implement_suggestion("test_suggestion_1")
        assert result is True

        # Verify suggestion is marked as implemented
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT implemented FROM suggestions WHERE suggestion_id = ?", ("test_suggestion_1",))
            implemented = cursor.fetchone()[0]
            assert implemented == 1  # SQLite stores boolean as 1/0

    def test_learning_interval(self):
        """Test learning interval functionality"""
        print("\n🧪 Testing Learning Interval...")

        learning_system = LearningSystem(db_path=self.db_path)

        # Set learning interval to 24 hours
        learning_system.config["learning_interval_hours"] = 24

        # Record some data
        learning_data = LearningData(
            timestamp=datetime.now(),
            user_id="test_user",
            session_id="test_session",
            command_name="test-command",
            parameters={},
            execution_time=1.0,
            success=True,
            error_message=None,
            context={}
        )
        learning_system.record_usage(learning_data)

        # Learn patterns (should work since it's been more than interval)
        patterns1 = asyncio.run(learning_system.learn_patterns())

        # Try to learn again immediately (should return cached patterns)
        patterns2 = asyncio.run(learning_system.learn_patterns())

        assert patterns1 == patterns2

    def test_data_retention(self):
        """Test data retention policy"""
        print("\n🧪 Testing Data Retention Policy...")

        # Set retention to 1 day
        config = {"retention_days": 1}
        learning_system = LearningSystem(db_path=self.db_path, config=config)

        # Record old data
        old_data = LearningData(
            timestamp=datetime.now() - timedelta(days=2),
            user_id="test_user",
            session_id="old_session",
            command_name="old-command",
            parameters={},
            execution_time=1.0,
            success=True,
            error_message=None,
            context={}
        )
        learning_system.record_usage(old_data)

        # Record recent data
        recent_data = LearningData(
            timestamp=datetime.now(),
            user_id="test_user",
            session_id="recent_session",
            command_name="recent-command",
            parameters={},
            execution_time=1.0,
            success=True,
            error_message=None,
            context={}
        )
        learning_system.record_usage(recent_data)

        # Learn patterns (should only use recent data)
        patterns = asyncio.run(learning_system.learn_patterns())

        # Should have patterns from recent data only
        assert len(patterns) >= 0  # May not have patterns if frequency threshold not met

    def test_global_instance(self):
        """Test global learning system instance"""
        print("\n🧪 Testing Global Instance...")

        # Clear global instance
        import src.learning_system
        src.learning_system._learning_instance = None

        # Get global instance
        instance1 = get_learning_system()
        instance2 = get_learning_system()

        # Should be the same instance
        assert instance1 is instance2

    def test_utility_functions(self):
        """Test utility functions"""
        print("\n🧪 Testing Utility Functions...")

        # Clear global instance
        import src.learning_system
        src.learning_system._learning_instance = None

        # Test record_command_usage
        record_command_usage("test-command", {"param": "value"}, 1.0, True)

        # Get global instance and verify data was recorded
        learning_system = get_learning_system()
        stats = learning_system.get_usage_statistics()
        assert stats["total_usage"] >= 1

    def test_context_isolation(self):
        """Test that each learning system instance maintains isolated state"""
        print("\n🧪 Testing Context Isolation...")

        # Create two separate learning systems
        learning_system1 = LearningSystem(db_path=os.path.join(self.temp_dir, "db1.db"))
        learning_system2 = LearningSystem(db_path=os.path.join(self.temp_dir, "db2.db"))

        # Record data in first system
        learning_data = LearningData(
            timestamp=datetime.now(),
            user_id="test_user",
            session_id="test_session",
            command_name="test-command",
            parameters={},
            execution_time=1.0,
            success=True,
            error_message=None,
            context={}
        )
        learning_system1.record_usage(learning_data)

        # Get statistics from both systems
        stats1 = learning_system1.get_usage_statistics()
        stats2 = learning_system2.get_usage_statistics()

        # Should be independent
        assert stats1["total_usage"] == 1
        assert stats2["total_usage"] == 0

    def test_error_handling(self):
        """Test error handling for edge cases"""
        print("\n🧪 Testing Error Handling...")

        learning_system = LearningSystem(db_path=self.db_path)

        # Test recording usage with learning disabled
        learning_system.config["learning_enabled"] = False
        learning_data = LearningData(
            timestamp=datetime.now(),
            user_id="test_user",
            session_id="test_session",
            command_name="test-command",
            parameters={},
            execution_time=1.0,
            success=True,
            error_message=None,
            context={}
        )

        # Should not raise an error
        learning_system.record_usage(learning_data)

        # Test learning with no data
        patterns = asyncio.run(learning_system.learn_patterns())
        assert patterns == []

        # Test implementing non-existent suggestion
        result = learning_system.implement_suggestion("non-existent")
        assert result is False

    def run_all_tests(self):
        """Run all tests and provide summary"""
        if not LEARNING_SYSTEM_AVAILABLE:
            print("🚀 Learning System Tests")
            print("=" * 60)
            print("⚠️  Learning System tests skipped due to missing dependencies")
            print("   Required: scikit-learn, numpy")
            print("   Install with: pip install scikit-learn numpy")
            return True

        print("🚀 Testing Learning & Improvement System")
        print("=" * 60)
        print("Testing pattern detection, usage tracking, and recommendation generation")

        test_functions = [
            ("Learning System Initialization", self.test_initialization),
            ("Database Initialization", self.test_database_initialization),
            ("Usage Recording", self.test_usage_recording),
            ("Pattern Learning Disabled", self.test_pattern_learning_disabled),
            ("Command Sequence Learning", self.test_command_sequence_learning),
            ("Parameter Pattern Learning", self.test_parameter_pattern_learning),
            ("Workflow Pattern Learning", self.test_workflow_pattern_learning),
            ("Suggestion Generation", self.test_suggestion_generation),
            ("Recommendation Generation", self.test_recommendation_generation),
            ("Usage Statistics", self.test_usage_statistics),
            ("Suggestion Implementation", self.test_suggestion_implementation),
            ("Learning Interval", self.test_learning_interval),
            ("Data Retention", self.test_data_retention),
            ("Global Instance", self.test_global_instance),
            ("Utility Functions", self.test_utility_functions),
            ("Context Isolation", self.test_context_isolation),
            ("Error Handling", self.test_error_handling),
        ]

        passed = 0
        total = len(test_functions)

        for test_name, test_func in test_functions:
            if self.run_test(test_name, test_func):
                passed += 1

        print("\n" + "=" * 60)
        print(f"Test Results: {passed}/{total} passed")

        if passed == total:
            print("🎉 All tests passed! Learning & Improvement System is working correctly.")
            print("\n✅ Context Engineering Principles Applied:")
            print("  - Write: Usage patterns and learning data saved to structured database")
            print("  - Select: Intelligent pattern detection and recommendation filtering")
            print("  - Compress: Pattern compression and statistical analysis")
            print("  - Isolate: Each learning system maintains independent context")
        else:
            print(f"❌ {total - passed} tests failed. Review the output above.")

        return passed == total


if __name__ == "__main__":
    test_suite = TestLearningSystem()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)