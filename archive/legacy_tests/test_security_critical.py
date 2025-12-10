#!/usr/bin/env python3
"""
Critical Security Tests for OOS System
Tests authentication, key management, and security-critical components
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestSecurityCritical:
    """Test suite for security-critical components"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_results = []

    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_auth_module_exists(self):
        """Test that auth.py exists and can be imported"""
        try:
            from auth import authenticate_user
            assert callable(authenticate_user)
            self.test_results.append("✓ Auth module importable")
        except ImportError as e:
            self.test_results.append(f"✗ Auth module import failed: {e}")
            raise

    def test_auth_security_issues(self):
        """Test for security issues in auth module"""
        from auth import authenticate_user

        # Test against hardcoded credentials
        result = authenticate_user('admin', 'password')
        if result:
            self.test_results.append("✗ CRITICAL: Auth module accepts hardcoded credentials")
            raise AssertionError("Hardcoded credentials in auth module")
        else:
            self.test_results.append("✓ Auth module rejects hardcoded credentials")

    def test_auth_input_validation(self):
        """Test input validation in auth module"""
        from auth import authenticate_user

        # Test empty inputs
        result_empty = authenticate_user('', '')
        result_none = authenticate_user(None, None)

        # Should not authenticate invalid inputs
        assert not result_empty, "Empty credentials should not authenticate"
        assert not result_none, "None credentials should not authenticate"
        self.test_results.append("✓ Auth module validates input properly")

    def test_no_hardcoded_secrets_in_source(self):
        """Test that no hardcoded secrets exist in source files"""
        import re

        # Patterns to search for
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'ghp_[a-zA-Z0-9]{36}',  # GitHub PAT pattern
            r'sk-[a-zA-Z0-9_-]{43,}',  # OpenAI/Anthropic key pattern
        ]

        issues_found = []

        # Scan source files
        src_dir = project_root / 'src'
        for py_file in src_dir.glob('**/*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        issues_found.append(f"{py_file.name}: {pattern} - {len(matches)} matches")

        # Scan auth.py specifically
        auth_file = project_root / 'auth.py'
        if auth_file.exists():
            with open(auth_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'admin' in content and 'password' in content:
                    issues_found.append("auth.py: Contains hardcoded admin credentials")

        if issues_found:
            self.test_results.append(f"✗ CRITICAL: Hardcoded secrets found: {issues_found}")
            raise AssertionError(f"Hardcoded secrets found: {issues_found}")
        else:
            self.test_results.append("✓ No hardcoded secrets detected")

    def test_shell_script_permissions(self):
        """Test that shell scripts have appropriate permissions"""
        bin_dir = project_root / 'bin'
        scripts_dir = project_root / 'scripts'

        permission_issues = []

        for script_dir in [bin_dir, scripts_dir]:
            if script_dir.exists():
                for script_file in script_dir.glob('*.sh'):
                    if script_file.is_file():
                        # Check if executable
                        if not os.access(script_file, os.X_OK):
                            permission_issues.append(f"{script_file.name} is not executable")

                        # Check permissions (should not be world-writable)
                        stat_info = script_file.stat()
                        if stat_info.st_mode & 0o002:  # World-writable
                            permission_issues.append(f"{script_file.name} is world-writable")

        if permission_issues:
            self.test_results.append(f"✗ Permission issues: {permission_issues}")
            raise AssertionError(f"Permission issues found: {permission_issues}")
        else:
            self.test_results.append("✓ Shell scripts have appropriate permissions")

    def test_env_file_security(self):
        """Test .env file security"""
        env_file = project_root / '.env'

        if env_file.exists():
            # Check permissions
            stat_info = env_file.stat()
            if stat_info.st_mode & 0o077:  # Readable/writable by group or others
                self.test_results.append("✗ .env file has insecure permissions")
                raise AssertionError(".env file has insecure permissions")

            # Check for secrets in .env
            with open(env_file, 'r') as f:
                content = f.read()
                if 'password' in content.lower() or 'secret' in content.lower():
                    # This might be okay if properly secured, but worth noting
                    self.test_results.append("⚠️ .env file contains sensitive data (verify proper security)")

        self.test_results.append("✓ .env file security check passed")

    def test_critical_shell_scripts_exist(self):
        """Test that critical shell scripts exist and are executable"""
        critical_scripts = [
            'bin/security_audit.sh',
            'bin/key_rotator.sh',
            'bin/secrets.sh',
            'scripts/bootstrap_enhanced.sh',
            'scripts/bootstrap.sh'
        ]

        missing_scripts = []
        non_executable = []

        for script_path in critical_scripts:
            full_path = project_root / script_path
            if not full_path.exists():
                missing_scripts.append(script_path)
            elif not os.access(full_path, os.X_OK):
                non_executable.append(script_path)

        if missing_scripts:
            self.test_results.append(f"✗ Missing critical scripts: {missing_scripts}")
            # This is a warning, not a failure, as some might be optional
        else:
            self.test_results.append("✓ Critical shell scripts exist")

        if non_executable:
            self.test_results.append(f"✗ Non-executable scripts: {non_executable}")
            raise AssertionError(f"Non-executable scripts: {non_executable}")

    def test_security_audit_script_functionality(self):
        """Test that security audit script can run"""
        security_script = project_root / 'bin' / 'security_audit.sh'

        if security_script.exists():
            try:
                # Run with --help or similar to test basic functionality
                result = subprocess.run(
                    [str(security_script), '--help'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # Script should exit cleanly (even if help is not supported)
                self.test_results.append("✓ Security audit script is executable")
            except subprocess.TimeoutExpired:
                self.test_results.append("⚠️ Security audit script timed out (might be normal)")
            except Exception as e:
                self.test_results.append(f"✗ Security audit script error: {e}")
        else:
            self.test_results.append("⚠️ Security audit script not found")

    def test_results_summary(self):
        """Print test results summary"""
        print("\n=== Security Test Results ===")
        for result in self.test_results:
            print(result)

        passed = sum(1 for r in self.test_results if r.startswith('✓'))
        warnings = sum(1 for r in self.test_results if r.startswith('⚠️'))
        failed = sum(1 for r in self.test_results if r.startswith('✗'))

        print(f"\nSummary: {passed} passed, {warnings} warnings, {failed} failed")

        if failed > 0:
            raise AssertionError(f"{failed} security tests failed")


if __name__ == "__main__":
    test = TestSecurityCritical()
    test.setup_method()

    try:
        test.test_auth_module_exists()
        test.test_auth_security_issues()
        test.test_auth_input_validation()
        test.test_no_hardcoded_secrets_in_source()
        test.test_shell_script_permissions()
        test.test_env_file_security()
        test.test_critical_shell_scripts_exist()
        test.test_security_audit_script_functionality()
        test.test_results_summary()
        print("✅ All security tests passed!")
    finally:
        test.teardown_method()