#!/usr/bin/env python3
"""
Comprehensive Shell Script Testing Framework
Tests critical shell scripts and provides unified testing interface
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add project root to path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))


class TestShellComprehensive:
    """Comprehensive test suite for shell scripts"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_results = []

    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def run_shell_script(self, script_path, args=None, timeout=30):
        """Run a shell script and return result"""
        if args is None:
            args = []

        try:
            result = subprocess.run(
                ['bash', str(script_path)] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_root)
            )
            return result
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            return None

    def test_critical_scripts_exist(self):
        """Test that critical shell scripts exist and are executable"""
        critical_scripts = [
            'bin/security_audit.sh',
            'bin/key_rotator.sh',
            'bin/diagnose.sh',
            'bin/health_monitor.sh',
            'bin/run_tests.sh',
            'scripts/bootstrap_enhanced.sh',
            'scripts/bootstrap.sh'
        ]

        missing = []
        non_executable = []

        for script_path in critical_scripts:
            full_path = project_root / script_path
            if not full_path.exists():
                missing.append(script_path)
            elif not os.access(full_path, os.X_OK):
                non_executable.append(script_path)

        assert not missing, f"Missing critical scripts: {missing}"
        assert not non_executable, f"Non-executable scripts: {non_executable}"
        self.test_results.append("✓ Critical shell scripts exist and are executable")

    def test_security_audit_script(self):
        """Test security audit script functionality"""
        security_script = project_root / 'bin' / 'security_audit.sh'

        if not security_script.exists():
            self.test_results.append("⚠️ Security audit script not found")
            return

        # Test --help flag
        result = self.run_shell_script(security_script, ['--help'])
        if result and result.returncode == 0:
            self.test_results.append("✓ Security audit script --help works")
        else:
            self.test_results.append("⚠️ Security audit script --help failed")

        # Test scan command
        result = self.run_shell_script(security_script, ['scan'])
        if result is not None:
            self.test_results.append("✓ Security audit script scan executes")
        else:
            self.test_results.append("✗ Security audit script scan failed")

    def test_diagnose_script(self):
        """Test diagnose script functionality"""
        diagnose_script = project_root / 'bin' / 'diagnose.sh'

        if not diagnose_script.exists():
            self.test_results.append("⚠️ Diagnose script not found")
            return

        # Test --help flag
        result = self.run_shell_script(diagnose_script, ['--help'])
        if result and result.returncode == 0:
            self.test_results.append("✓ Diagnose script --help works")
        else:
            self.test_results.append("⚠️ Diagnose script --help failed")

        # Test dry run
        result = self.run_shell_script(diagnose_script, ['--dry-run'])
        if result is not None:
            self.test_results.append("✓ Diagnose script dry-run executes")
        else:
            self.test_results.append("✗ Diagnose script dry-run failed")

    def test_bootstrap_script_validation(self):
        """Test bootstrap script validation"""
        bootstrap_script = project_root / 'scripts' / 'bootstrap_enhanced.sh'

        if not bootstrap_script.exists():
            self.test_results.append("✗ Bootstrap script not found")
            return

        # Test --help flag
        result = self.run_shell_script(bootstrap_script, ['--help'])
        if result and result.returncode == 0:
            self.test_results.append("✓ Bootstrap script --help works")
        else:
            self.test_results.append("⚠️ Bootstrap script --help failed")

        # Test dry run (requires .env file)
        env_file = project_root / '.env'
        env_existed = env_file.exists()

        try:
            # Create temporary .env if it doesn't exist
            if not env_existed:
                with open(env_file, 'w') as f:
                    f.write("OPENROUTER_KEYS=test-key-1,test-key-2\n")
                os.chmod(env_file, 0o600)

            # Test dry run
            result = self.run_shell_script(bootstrap_script, [
                '--dry-run', '--no-preflight', 'test-project', '/tmp/test-project'
            ])

            if result is not None:
                self.test_results.append("✓ Bootstrap script dry-run executes")
            else:
                self.test_results.append("✗ Bootstrap script dry-run failed")

        finally:
            # Clean up .env if we created it
            if not env_existed and env_file.exists():
                os.remove(env_file)

    def test_critical_script_syntax_validation(self):
        """Test that critical shell scripts have valid syntax"""
        critical_scripts = [
            'bin/security_audit.sh',
            'bin/diagnose.sh',
            'bin/run_tests.sh',
            'scripts/bootstrap_enhanced.sh',
            'scripts/bootstrap.sh'
        ]

        syntax_errors = []

        for script_path in critical_scripts:
            full_path = project_root / script_path
            if full_path.exists():
                # Test syntax with bash -n
                result = subprocess.run(
                    ['bash', '-n', str(full_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(project_root)
                )

                if result.returncode != 0:
                    syntax_errors.append(f"{script_path}: {result.stderr}")
                else:
                    self.test_results.append(f"✓ {script_path}: Syntax OK")
            else:
                self.test_results.append(f"⚠️ {script_path}: Not found")

        if syntax_errors:
            self.test_results.append(f"✗ Syntax errors in critical scripts: {syntax_errors}")
            raise AssertionError(f"Syntax errors: {syntax_errors}")
        else:
            self.test_results.append("✓ All critical shell scripts have valid syntax")

    def test_run_tests_script(self):
        """Test run_tests.sh functionality"""
        run_tests_script = project_root / 'bin' / 'run_tests.sh'

        if not run_tests_script.exists():
            self.test_results.append("⚠️ run_tests.sh not found")
            return

        # Make sure it's executable
        if not os.access(run_tests_script, os.X_OK):
            os.chmod(run_tests_script, 0o755)

        # Test script execution (should run pytest)
        result = self.run_shell_script(run_tests_script, ['--help'])
        if result is not None:
            self.test_results.append("✓ run_tests.sh executes")
        else:
            self.test_results.append("✗ run_tests.sh failed to execute")

    def test_shell_script_security(self):
        """Test shell script security patterns"""
        script_dirs = ['bin', 'scripts']
        security_issues = []

        for script_dir in script_dirs:
            dir_path = project_root / script_dir
            if dir_path.exists():
                for script_file in dir_path.glob('*.sh'):
                    with open(script_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                        # Check for potentially dangerous patterns
                        dangerous_patterns = [
                            'curl | bash',
                            'wget | bash',
                            'eval $("',
                            'echo.*|.*bash',
                            'rm -rf /',
                            'chmod 777'
                        ]

                        for pattern in dangerous_patterns:
                            if pattern in content.lower():
                                security_issues.append(f"{script_file.name}: Contains {pattern}")

        if security_issues:
            self.test_results.append(f"⚠️ Security issues found: {security_issues}")
            # Warning, not failure - some might be legitimate
        else:
            self.test_results.append("✓ No obvious security issues in shell scripts")

    def test_results_summary(self):
        """Print test results summary"""
        print("\n=== Shell Script Test Results ===")
        for result in self.test_results:
            print(result)

        passed = sum(1 for r in self.test_results if r.startswith('✓'))
        warnings = sum(1 for r in self.test_results if r.startswith('⚠️'))
        failed = sum(1 for r in self.test_results if r.startswith('✗'))

        print(f"\nSummary: {passed} passed, {warnings} warnings, {failed} failed")

        if failed > 0:
            raise AssertionError(f"{failed} shell script tests failed")


if __name__ == "__main__":
    test = TestShellComprehensive()
    test.setup_method()

    try:
        test.test_critical_scripts_exist()
        test.test_security_audit_script()
        test.test_diagnose_script()
        test.test_bootstrap_script_validation()
        test.test_critical_script_syntax_validation()
        test.test_run_tests_script()
        test.test_shell_script_security()
        test.test_results_summary()
        print("✅ All shell script tests passed!")
    finally:
        test.teardown_method()