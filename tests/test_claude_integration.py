#!/usr/bin/env python3
"""
Test script for Simplified Claude Code Integration System
Validates the simple command handler functionality
"""

import json
import tempfile
import os
import sys
from pathlib import Path
import unittest.mock as mock
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.claude_integration import ClaudeCodeIntegration
from src.simple_command_handler import SimpleCommandHandler, CommandInfo


class TestSimplifiedClaudeIntegration:
    """Test suite for Simplified Claude Code Integration System"""

    def setup_method(self):
        """Setup test environment"""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        # Create temporary commands directory
        self.commands_dir = Path(self.temp_dir) / ".claude" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up test environment"""
        # Clean up temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)


    def test_command_loading(self):
        """Test loading commands from markdown files"""
        # Create a test command file
        test_command_file = self.commands_dir / "test-cmd.md"
        test_command_content = """---
description: Test command for validation
script_path: ./bin/test-cmd.sh
category: testing
---

This is a test command for validation purposes.
"""
        test_command_file.write_text(test_command_content)

        # Test loading the command
        handler = SimpleCommandHandler(str(self.commands_dir))
        assert "test-cmd" in handler.commands

        cmd = handler.get_command("test-cmd")
        assert isinstance(cmd, CommandInfo)
        assert cmd.name == "test-cmd"
        assert cmd.description == "Test command for validation"
        assert cmd.script_path == "./bin/test-cmd.sh"
        assert cmd.category == "testing"


    def test_list_commands(self):
        """Test listing all available commands"""
        # Create test command files
        cmd1_content = """---
description: First test command
script_path: ./bin/cmd1.sh
category: testing
---
First command"""

        cmd2_content = """---
description: Second test command
script_path: ./bin/cmd2.sh
category: general
---
Second command"""

        (self.commands_dir / "cmd1.md").write_text(cmd1_content)
        (self.commands_dir / "cmd2.md").write_text(cmd2_content)

        handler = SimpleCommandHandler(str(self.commands_dir))
        commands = handler.list_commands()

        assert len(commands) == 2
        command_names = [cmd.name for cmd in commands]
        assert "cmd1" in command_names
        assert "cmd2" in command_names

    def test_get_command(self):
        """Test getting a specific command"""
        test_content = """---
description: Test command
script_path: ./bin/test.sh
category: testing
---
Test command"""
        (self.commands_dir / "test.md").write_text(test_content)

        handler = SimpleCommandHandler(str(self.commands_dir))

        # Test getting existing command
        cmd = handler.get_command("test")
        assert cmd is not None
        assert cmd.name == "test"

        # Test getting non-existing command
        cmd = handler.get_command("nonexistent")
        assert cmd is None

    def test_execute_command(self):
        """Test command execution info"""
        test_content = """---
description: Test command
script_path: ./bin/test.sh
category: testing
---
Test command"""
        (self.commands_dir / "test.md").write_text(test_content)

        handler = SimpleCommandHandler(str(self.commands_dir))

        # Test executing command without args
        result = handler.execute_command("test")
        assert result["command"] == "test"
        assert result["description"] == "Test command"
        assert result["script"] == "./bin/test.sh"
        assert result["execution"] == "./bin/test.sh"
        assert result["category"] == "testing"

        # Test executing command with args
        result = handler.execute_command("test", "--force --verbose")
        assert result["execution"] == "./bin/test.sh --force --verbose"

    def test_execute_nonexistent_command(self):
        """Test executing non-existent command"""
        handler = SimpleCommandHandler(str(self.commands_dir))
        result = handler.execute_command("nonexistent")

        assert "error" in result
        assert "not found" in result["error"]

    def test_integration_list_commands(self):
        """Test integration list commands method"""
        test_content = """---
description: Test command
script_path: ./bin/test.sh
category: testing
---
Test command"""
        (self.commands_dir / "test.md").write_text(test_content)

        integration = ClaudeCodeIntegration()
        # Override commands dir for testing
        integration.command_handler = SimpleCommandHandler(str(self.commands_dir))

        commands = integration.list_commands()
        assert len(commands) == 1
        assert commands[0]["name"] == "test"
        assert commands[0]["description"] == "Test command"
        assert commands[0]["category"] == "testing"

    def test_integration_execute_command(self):
        """Test integration execute command method"""
        test_content = """---
description: Test command
script_path: ./bin/test.sh
category: testing
---
Test command"""
        (self.commands_dir / "test.md").write_text(test_content)

        integration = ClaudeCodeIntegration()
        # Override commands dir for testing
        integration.command_handler = SimpleCommandHandler(str(self.commands_dir))

        result = integration.execute_command("test", "--verbose")
        assert result["command"] == "test"
        assert result["execution"] == "./bin/test.sh --verbose"

    def test_integration_get_command_info(self):
        """Test integration get command info method"""
        test_content = """---
description: Test command
script_path: ./bin/test.sh
category: testing
---
Test command"""
        (self.commands_dir / "test.md").write_text(test_content)

        integration = ClaudeCodeIntegration()
        # Override commands dir for testing
        integration.command_handler = SimpleCommandHandler(str(self.commands_dir))

        info = integration.get_command_info("test")
        assert info is not None
        assert info["name"] == "test"
        assert info["script"] == "./bin/test.sh"
        assert info["category"] == "testing"

        # Test non-existent command
        info = integration.get_command_info("nonexistent")
        assert info is None

    def test_config_loading(self):
        """Test configuration loading from file"""
        # Create temporary config file
        config_file = os.path.join(self.temp_dir, "config.json")
        config_data = {
            "debug": True,
            "workspace_root": "/custom/workspace"
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load integration with config
        integration = ClaudeCodeIntegration(config_file)

        assert integration.config["debug"] is True
        assert integration.config["workspace_root"] == "/custom/workspace"

    def test_config_loading_invalid_file(self):
        """Test configuration loading with invalid file"""
        # Test with non-existent file
        integration = ClaudeCodeIntegration("/nonexistent/config.json")
        assert integration.config["debug"] is False  # Should use defaults

    def test_yaml_parsing_fallback(self):
        """Test YAML parsing fallback"""
        # Create command file without YAML frontmatter
        test_command_file = self.commands_dir / "simple-cmd.md"
        simple_content = "Simple command description\n\nThis is a simple command."
        test_command_file.write_text(simple_content)

        handler = SimpleCommandHandler(str(self.commands_dir))
        cmd = handler.get_command("simple-cmd")

        assert cmd is not None
        assert cmd.name == "simple-cmd"
        assert cmd.description == "Simple command description"  # First line
        assert cmd.script_path == "./bin/claude-simple-cmd.sh"  # Default pattern
        assert cmd.category == "general"  # Default category


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])