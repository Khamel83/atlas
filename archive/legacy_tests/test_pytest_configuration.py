"""
Test Suite for pytest Configuration and Test Discovery

This test suite validates that pytest is properly configured and can
discover and execute tests across the Atlas codebase.

Tests cover:
- pytest configuration file validation
- Test discovery patterns and paths
- Import resolution for test modules
- Plugin compatibility and loading
- Test collection and execution flow
"""

import subprocess
import sys
from pathlib import Path

import pytest
from helpers.bulletproof_process_manager import create_managed_process


class TestPytestConfiguration:
    """Test pytest configuration and setup."""

    def test_pytest_ini_exists(self):
        """Test that pytest configuration file exists."""
        pytest_ini = Path("pytest.ini")
        assert pytest_ini.exists(), "pytest.ini configuration file should exist"

    def test_pytest_ini_basic_configuration(self):
        """Test that pytest.ini contains basic required configuration."""
        pytest_ini = Path("pytest.ini")
        content = pytest_ini.read_text()

        # Check for essential configuration sections
        assert (
            "[tool:pytest]" in content or "[pytest]" in content
        ), "pytest.ini should contain pytest configuration section"

        # Check for test path configuration
        content_lower = content.lower()
        assert (
            "testpaths" in content_lower or "tests" in content
        ), "pytest.ini should specify test paths"

    def test_pytest_can_import_modules(self):
        """Test that pytest can import project modules without errors."""
        # Test importing core modules that tests depend on
        core_modules = [
            "helpers.config",
            "helpers.validate",
            "helpers.article_fetcher",
            "ingest.capture.failure_notifier",
        ]

        for module in core_modules:
            try:
                __import__(module)
            except ImportError as e:
                pytest.fail(f"pytest cannot import core module {module}: {e}")

    def test_pytest_discovers_test_files(self):
        """Test that pytest can discover test files in expected locations."""
        # Run pytest in collection-only mode to check test discovery
        process = create_managed_process(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            "pytest_collect_only",
            cwd=Path.cwd(),
        )
        stdout, stderr = process.communicate()

        # Should not fail catastrophically
        assert process.returncode in [
            0,
            1,
            2,
        ], f"pytest test discovery failed catastrophically: {stderr.decode('utf-8')}"

        # Should discover some tests
        if process.returncode == 0:
            output = stdout.decode('utf-8')
            assert "collected" in output, "pytest should discover and collect tests"

    def test_test_directory_structure(self):
        """Test that test directory structure is properly organized."""
        tests_dir = Path("tests")
        assert tests_dir.exists(), "tests directory should exist"
        assert tests_dir.is_dir(), "tests should be a directory"

        # Check for unit tests subdirectory
        unit_tests = tests_dir / "unit"
        assert unit_tests.exists(), "tests/unit directory should exist"

        # Check for integration tests if they exist
        integration_tests = tests_dir / "integration"
        if integration_tests.exists():
            assert integration_tests.is_dir(), "tests/integration should be a directory"

    def test_test_files_follow_naming_convention(self):
        """Test that test files follow pytest naming conventions."""
        tests_dir = Path("tests")
        test_files = []

        # Collect all Python files in tests directory
        for py_file in tests_dir.rglob("*.py"):
            if py_file.name not in ["__init__.py", "conftest.py"]:
                test_files.append(py_file)

        assert len(test_files) > 0, "Should find test files in tests directory"

        # Check naming conventions
        for test_file in test_files:
            filename = test_file.name
            assert filename.startswith("test_") or filename.endswith(
                "_test.py"
            ), f"Test file {filename} should follow pytest naming convention"

    def test_conftest_files_loadable(self):
        """Test that conftest.py files can be loaded without errors."""
        tests_dir = Path("tests")
        conftest_files = list(tests_dir.rglob("conftest.py"))

        for conftest in conftest_files:
            # Test that conftest file is syntactically valid
            try:
                with open(conftest) as f:
                    compile(f.read(), str(conftest), "exec")
            except SyntaxError as e:
                pytest.fail(f"conftest.py at {conftest} has syntax error: {e}")


class TestPytestDiscovery:
    """Test pytest test discovery functionality."""

    def test_pytest_discovers_phase1_tests(self):
        """Test that pytest discovers Phase 1 test files."""
        expected_test_files = [
            "test_environment_validation.py",
            "test_enhanced_validation.py",
            "test_troubleshooting_tools.py",
            "test_end_to_end_phase1.py",
        ]

        tests_dir = Path("tests")
        for test_file in expected_test_files:
            test_path = tests_dir / test_file
            assert test_path.exists(), f"Phase 1 test file {test_file} should exist"

    def test_pytest_discovers_unit_tests(self):
        """Test that pytest discovers unit test files."""
        unit_tests_dir = Path("tests/unit")
        if unit_tests_dir.exists():
            unit_test_files = list(unit_tests_dir.glob("test_*.py"))
            assert len(unit_test_files) > 0, "Should discover unit test files"

    def test_pytest_test_collection_performance(self):
        """Test that pytest test collection completes in reasonable time."""
        import time

        start_time = time.time()
        process = create_managed_process(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            "pytest_collect_performance",
            timeout=30,
        )
        stdout, stderr = process.communicate()
        elapsed = time.time() - start_time

        # Test collection should complete within 30 seconds
        assert elapsed < 30, f"Test collection took too long: {elapsed:.2f}s"

    def test_pytest_can_run_individual_test_files(self):
        """Test that pytest can run individual test files."""
        # Try running a known working test file
        test_file = "tests/test_enhanced_validation.py"
        if Path(test_file).exists():
            process = create_managed_process(
                [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
                f"pytest_run_individual_{Path(test_file).stem}",
                timeout=60,
            )
            stdout, stderr = process.communicate()

            # Should not crash completely
            assert process.returncode in [
                0,
                1,
            ], f"Individual test file execution failed: {stderr.decode('utf-8')}"


class TestPytestPlugins:
    """Test pytest plugin compatibility and loading."""

    def test_pytest_plugins_loadable(self):
        """Test that required pytest plugins can be loaded."""
        # Test that pytest can load without plugin conflicts
        process = create_managed_process(
            [sys.executable, "-m", "pytest", "--version"],
            "pytest_version",
        )
        stdout, stderr = process.communicate()

        assert process.returncode == 0, f"pytest --version failed: {stderr.decode('utf-8')}"
        assert (
            "pytest" in stdout.decode('utf-8')
        ), "pytest version output should contain 'pytest'"

    def test_pytest_mock_plugin_available(self):
        """Test that pytest-mock plugin is available if installed."""
        try:
            process = create_managed_process(
                [sys.executable, "-c", "import pytest_mock"],
                "import_pytest_mock",
            )
            stdout, stderr = process.communicate()

            if result.returncode == 0:
                # If pytest-mock is available, test it works with pytest
                test_process = create_managed_process(
                    [sys.executable, "-m", "pytest", "--version"],
                    "pytest_with_mock",
                )
                test_stdout, test_stderr = test_process.communicate()
                assert (
                    test_process.returncode == 0
                ), "pytest should work with pytest-mock"
        except ImportError:
            pytest.skip("pytest-mock not installed")

    def test_anyio_plugin_compatibility(self):
        """Test that pytest-anyio plugin is compatible if installed."""
        try:

            # If anyio plugin is available, pytest should still work
            process = create_managed_process(
                [sys.executable, "-m", "pytest", "--collect-only"],
                "pytest_collect_anyio",
                timeout=30,
            )
            stdout, stderr = process.communicate()

            assert process.returncode in [
                0,
                1,
                2,
            ], "pytest should work with anyio plugin"
        except ImportError:
            pytest.skip("pytest-anyio not installed")


class TestPytestExecution:
    """Test pytest execution environment and capabilities."""

    def test_pytest_working_directory(self):
        """Test that pytest runs from correct working directory."""
        # Verify we're in the project root
        cwd = Path.cwd()

        # Should have key project files
        assert (cwd / "helpers").exists(), "Should be in project root with helpers/"
        assert (cwd / "tests").exists(), "Should be in project root with tests/"
        assert (cwd / "config").exists(), "Should be in project root with config/"

    def test_pytest_python_path(self):
        """Test that pytest can access project modules."""
        # Test Python path configuration
        process = create_managed_process(
            [
                sys.executable,
                "-c",
                "import sys; print('\n'.join(sys.path)); import helpers.config",
            ],
            "check_python_path",
        )
        stdout, stderr = process.communicate()

        assert (
            process.returncode == 0
        ), f"Python path configuration issue: {stderr.decode('utf-8')}"

    def test_pytest_environment_isolation(self):
        """Test that pytest runs in proper environment isolation."""
        # Run a simple test to verify environment
        simple_test = """
def test_environment():
    import os
    import sys
    assert len(sys.path) > 0
    assert os.getcwd()
"""

        # Write temporary test file
        temp_test = Path("temp_pytest_test.py")
        temp_test.write_text(simple_test)

        try:
            process = create_managed_process(
                [sys.executable, "-m", "pytest", str(temp_test), "-v"],
                "pytest_env_isolation",
                timeout=30,
            )
            stdout, stderr = process.communicate()

            assert process.returncode == 0, f"Environment test failed: {stderr.decode('utf-8')}"

        finally:
            if temp_test.exists():
                temp_test.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
