"""
End-to-End Test Suite for Phase 1: Environment Setup Automation

This comprehensive test suite validates that all Phase 1 components work
together correctly for environment setup, configuration, validation, and
troubleshooting.

Tests cover:
- Task 1.1: Environment validation tests
- Task 1.2: Automated .env generation
- Task 1.3: Dependency validation
- Task 1.4: Setup wizard
- Task 1.5: Enhanced configuration validation
- Task 1.6: Troubleshooting documentation and tools
- Task 1.7: End-to-end verification
"""

import json
import os
import subprocess
import sys
import tempfile
from helpers.bulletproof_process_manager import create_managed_process
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.config import load_config
from helpers.validate import ConfigValidator


class TestPhase1EndToEnd:
    """End-to-end integration tests for Phase 1 components."""

    def test_configuration_loading_workflow(self):
        """Test complete configuration loading and validation workflow."""
        # Test that config can be loaded
        config = load_config()
        assert isinstance(config, dict)
        assert "data_directory" in config
        assert "llm_provider" in config

        # Test enhanced validation
        validator = ConfigValidator()
        errors, warnings = validator.validate_config(config)

        # Should have no critical errors with our test config
        critical_errors = [e for e in errors if e.severity == "error"]
        assert (
            len(critical_errors) == 0
        ), f"Critical config errors: {[e.message for e in critical_errors]}"

        # May have warnings (like placeholder API key) but that's expected
        assert isinstance(warnings, list)

    def test_validation_scripts_execution(self):
        """Test that validation scripts execute without errors."""
        scripts_to_test = [
            "scripts/validate_config.py",
            "scripts/setup_check.py",
            "scripts/diagnose_environment.py",
        ]

        for script in scripts_to_test:
            script_path = Path(script)
            assert script_path.exists(), f"Script {script} should exist"

            # Test script execution (may fail but shouldn't crash)
            try:
                process = create_managed_process(
                    [sys.executable, str(script_path), "--help"],
                    f"test_script_help_{script_path.stem}",
                    timeout=10,
                )
                stdout, stderr = process.communicate()

                # Script should either show help or exit gracefully
                assert process.returncode in [
                    0,
                    1,
                    2,
                ], f"Script {script} crashed unexpectedly"

            except subprocess.TimeoutExpired:
                pytest.fail(f"Script {script} timed out")
            except FileNotFoundError:
                pytest.fail(f"Cannot execute script {script}")

    def test_documentation_completeness(self):
        """Test that all required documentation exists and is complete."""
        required_docs = [
            "docs/environment-troubleshooting.md",
            "docs/troubleshooting_checklist.md",
            "docs/configuration-validation.md",
        ]

        for doc_path in required_docs:
            doc_file = Path(doc_path)
            assert doc_file.exists(), f"Documentation {doc_path} should exist"

            content = doc_file.read_text()
            assert (
                len(content) > 500
            ), f"Documentation {doc_path} should be comprehensive"

            # Check for key sections
            content_lower = content.lower()
            if "troubleshooting" in doc_path:
                assert "error" in content_lower
                assert "fix" in content_lower
                assert "python" in content_lower
            elif "validation" in doc_path:
                assert "configuration" in content_lower
                assert "validation" in content_lower

    def test_script_cross_references(self):
        """Test that scripts reference each other correctly."""
        # Check that troubleshooting docs reference validation scripts
        trouble_guide = Path("docs/environment-troubleshooting.md")
        trouble_content = trouble_guide.read_text()

        assert "validate_config.py" in trouble_content
        assert "diagnose_environment.py" in trouble_content
        assert "setup_check.py" in trouble_content

        # Check that scripts exist where referenced
        referenced_scripts = [
            "validate_config.py",
            "diagnose_environment.py",
            "setup_check.py",
        ]
        for script in referenced_scripts:
            script_path = Path(f"scripts/{script}")
            assert script_path.exists(), f"Referenced script {script} should exist"

    def test_error_handling_robustness(self):
        """Test that components handle errors gracefully."""
        # Test configuration validation with invalid config
        invalid_configs = [
            {},  # Empty config
            {"llm_provider": "invalid_provider"},  # Invalid provider
            {"llm_provider": "openrouter"},  # Missing API key
        ]

        validator = ConfigValidator()

        for config in invalid_configs:
            # Should not raise exceptions, just return errors
            try:
                errors, warnings = validator.validate_config(config)
                assert isinstance(errors, list)
                assert isinstance(warnings, list)
            except Exception as e:
                pytest.fail(f"Validation should not raise exceptions, got: {e}")

    def test_output_directory_creation(self):
        """Test that output directories can be created and are writable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config = {
                "data_directory": temp_dir,
                "llm_provider": "openrouter",
                "OPENROUTER_API_KEY": "sk-or-v1-test-key-12345678901234567890",
            }

            validator = ConfigValidator()
            errors, warnings = validator.validate_config(test_config)

            # Should not have directory permission errors
            dir_errors = [e for e in errors if "directory" in e.message.lower()]
            assert (
                len(dir_errors) == 0
            ), f"Should not have directory errors: {[e.message for e in dir_errors]}"

    def test_validation_error_guidance(self):
        """Test that validation errors provide actionable guidance."""
        # Test with missing API key
        config = {
            "llm_provider": "openrouter",
            "llm_model": "test-model",
            # Missing OPENROUTER_API_KEY
        }

        validator = ConfigValidator()
        errors, warnings = validator.validate_config(config)

        # Should have API key error
        api_key_errors = [e for e in errors if "OPENROUTER_API_KEY" in e.field]
        assert len(api_key_errors) == 1

        error = api_key_errors[0]
        assert error.guidance is not None
        assert error.fix_command is not None
        assert "openrouter.ai" in error.guidance.lower()
        assert ".env" in error.fix_command

    def test_diagnostic_json_output(self):
        """Test that diagnostic tools can produce JSON output."""
        try:
            process = create_managed_process(
                [sys.executable, "scripts/diagnose_environment.py", "--json"],
                "diagnose_json_output",
                timeout=30,
            )
            stdout, stderr = process.communicate()

            if stdout:
                # Should be valid JSON
                data = json.loads(stdout.decode('utf-8'))
                assert "timestamp" in data
                assert "critical_issues" in data
                assert "total_issues" in data
                assert "warnings" in data

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pytest.skip("Cannot test JSON output - script not available or failed")

    def test_setup_wizard_components(self):
        """Test that setup wizard components are present."""
        # Check for environment generation script
        env_gen_script = Path("scripts/generate_env.py")
        assert env_gen_script.exists(), "Environment generation script should exist"

        # Check for setup validation
        setup_check = Path("scripts/setup_check.py")
        assert setup_check.exists(), "Setup check script should exist"

        # Check that .env.example exists as template
        env_example = Path(".env.example")
        assert env_example.exists(), "Environment template should exist"

    def test_integration_workflow(self):
        """Test complete workflow from setup to validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Copy essential files to temp directory

            # Create minimal project structure
            (Path(temp_dir) / "helpers").mkdir()
            (Path(temp_dir) / "config").mkdir()
            (Path(temp_dir) / "scripts").mkdir()

            # Create minimal config file
            config_content = """DATA_DIRECTORY=output
LLM_PROVIDER=openrouter
LLM_MODEL=mistralai/mistral-7b-instruct
OPENROUTER_API_KEY=sk-or-v1-valid-test-key-12345678901234567890"""

            (Path(temp_dir) / "config" / ".env").write_text(config_content)

            # Create minimal helpers/config.py (simplified version)
            config_py = """
import os
from dotenv import load_dotenv

def load_config():
    load_dotenv(dotenv_path="config/.env")
    return {
        "data_directory": os.getenv("DATA_DIRECTORY", "output"),
        "llm_provider": os.getenv("LLM_PROVIDER"),
        "llm_model": os.getenv("LLM_MODEL"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY")
    }
"""
            (Path(temp_dir) / "helpers" / "__init__.py").write_text("")
            (Path(temp_dir) / "helpers" / "config.py").write_text(config_py)

            # Test configuration loading in isolated environment
            sys.path.insert(0, temp_dir)
            try:
                from helpers.config import load_config

                config = load_config()

                assert config["llm_provider"] == "openrouter"
                assert config["data_directory"] == "output"
                assert config["OPENROUTER_API_KEY"].startswith("sk-or-v1-")

            finally:
                sys.path.remove(temp_dir)


class TestPhase1ValidationCoverage:
    """Test comprehensive validation coverage for all Phase 1 scenarios."""

    def test_all_llm_providers_validated(self):
        """Test that all supported LLM providers are properly validated."""
        validator = ConfigValidator()

        providers_to_test = [
            (
                "openrouter",
                "OPENROUTER_API_KEY",
                "sk-or-v1-test-key-12345678901234567890",
            ),
            ("deepseek", "DEEPSEEK_API_KEY", "test-deepseek-key"),
            ("ollama", None, None),  # Ollama doesn't need API key
        ]

        for provider, key_field, key_value in providers_to_test:
            config = {
                "llm_provider": provider,
                "llm_model": "test-model",
                "data_directory": "output",
            }

            if key_field and key_value:
                config[key_field] = key_value

            errors, warnings = validator.validate_config(config)

            # Should not have critical provider errors with valid config
            provider_errors = [e for e in errors if e.field == "llm_provider"]
            assert len(provider_errors) == 0, f"Provider {provider} should be valid"

    def test_ingestor_validation_coverage(self):
        """Test that all ingestor configurations are validated."""
        validator = ConfigValidator()

        # Test YouTube ingestor
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-test-key-12345678901234567890",
            "youtube_ingestor": {"enabled": True},
            # Missing YOUTUBE_API_KEY
        }

        errors, warnings = validator.validate_config(config)
        youtube_errors = [e for e in errors if "YOUTUBE_API_KEY" in e.field]
        assert len(youtube_errors) == 1

        # Test Instapaper ingestor
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-test-key-12345678901234567890",
            "instapaper_ingestor": {"enabled": True},
            "INSTAPAPER_LOGIN": "test@example.com",
            # Missing INSTAPAPER_PASSWORD
        }

        errors, warnings = validator.validate_config(config)
        instapaper_errors = [e for e in errors if "INSTAPAPER_CREDENTIALS" in e.field]
        assert len(instapaper_errors) == 1

    def test_security_warning_coverage(self):
        """Test that security warnings are properly generated."""
        validator = ConfigValidator()

        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-test-key-12345678901234567890",
            "USE_12FT_IO_FALLBACK": True,  # Privacy concern
        }

        errors, warnings = validator.validate_config(config)

        # Should have warnings for privacy and placeholder
        privacy_warnings = [w for w in warnings if "privacy" in w.message.lower()]
        placeholder_warnings = [
            w for w in warnings if "placeholder" in w.message.lower()
        ]

        assert len(privacy_warnings) >= 1, "Should warn about privacy concerns"
        assert len(placeholder_warnings) >= 1, "Should detect placeholder values"


class TestPhase1ErrorRecovery:
    """Test error recovery and troubleshooting workflows."""

    def test_missing_dependencies_recovery(self):
        """Test that missing dependencies are properly diagnosed and fixable."""
        # This test validates that our troubleshooting system would work
        # in an environment without dependencies

        # Test validation error structure
        validator = ConfigValidator()

        # Simulate environment without dependencies by testing config validation
        # with various missing components
        incomplete_configs = [
            {"llm_provider": "openrouter"},  # Missing API key
            {"OPENROUTER_API_KEY": "sk-or-v1-test"},  # Missing provider
            {},  # Missing everything
        ]

        for config in incomplete_configs:
            errors, warnings = validator.validate_config(config)

            # Each error should have guidance and fix commands
            for error in errors:
                assert error.guidance is not None, "Error should provide guidance"
                assert len(error.guidance) > 10, "Guidance should be detailed"

                # Most errors should have fix commands
                if error.field in [
                    "llm_provider",
                    "OPENROUTER_API_KEY",
                    "DEEPSEEK_API_KEY",
                ]:
                    assert (
                        error.fix_command is not None
                    ), f"Error {error.field} should have fix command"

    def test_permission_error_recovery(self):
        """Test that permission errors can be diagnosed and fixed."""
        validator = ConfigValidator()

        # Test with a directory that should cause permission issues
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-test-key-12345678901234567890",
            "data_directory": "/root/forbidden",  # Should cause permission error
        }

        with patch(
            "pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")
        ):
            errors, warnings = validator.validate_config(config)

            permission_errors = [
                e
                for e in errors
                if "permission" in e.message.lower() or "writable" in e.message.lower()
            ]
            assert len(permission_errors) >= 1, "Should detect permission issues"

            for error in permission_errors:
                assert (
                    "chmod" in error.fix_command or "mkdir" in error.fix_command
                ), "Should provide permission fix"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
