#!/usr/bin/env python3
"""
Simplified End-to-End Integration Test for OOS System
Tests the simple command handler functionality in realistic scenarios
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


class TestSimplifiedEndToEndIntegration:
    """Simplified end-to-end integration test suite"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        # Create temporary commands directory
        self.commands_dir = Path(self.temp_dir) / ".claude" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.test_results = []

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)


    def test_complete_command_workflow(self):
        """Test complete workflow from command definition to execution"""
        print("\n🧪 Testing Complete Command Workflow...")

        # Step 1: Create realistic command definitions
        help_me_content = """---
description: Get AI-optimized processing for any request
script_path: ./bin/claude-help-me.sh
category: optimization
---

Provides automatic context optimization and intelligent processing for any request.
"""

        brain_dump_content = """---
description: Transform messy thoughts into clear structure
script_path: ./bin/claude-brain-dump.sh
category: optimization
---

Turns rambling thoughts into organized, actionable plans with context optimization.
"""

        meta_ai_content = """---
description: Generate prompts for external AI assistance
script_path: ./bin/claude-meta-ai.sh
category: assistance
---

Creates structured prompts for getting better answers from external AI systems.
"""

        # Write command files
        (self.commands_dir / "help-me.md").write_text(help_me_content)
        (self.commands_dir / "brain-dump.md").write_text(brain_dump_content)
        (self.commands_dir / "meta-ai.md").write_text(meta_ai_content)

        # Step 2: Initialize command handler
        handler = SimpleCommandHandler(str(self.commands_dir))

        # Step 3: Verify all commands loaded
        commands = handler.list_commands()
        assert len(commands) == 3

        command_names = [cmd.name for cmd in commands]
        expected_commands = ["help-me", "brain-dump", "meta-ai"]
        for expected in expected_commands:
            assert expected in command_names, f"Command {expected} not found"

        # Step 4: Test command information retrieval
        for cmd_name in expected_commands:
            cmd = handler.get_command(cmd_name)
            assert cmd is not None, f"Command {cmd_name} should exist"
            assert cmd.description is not None
            assert cmd.script_path is not None
            assert cmd.category in ["optimization", "assistance"]

        # Step 5: Test command execution info generation
        for cmd_name in expected_commands:
            result = handler.execute_command(cmd_name, "test args")
            assert result["command"] == cmd_name
            assert result["execution"] == f"{handler.get_command(cmd_name).script_path} test args"

        print("✅ Complete command workflow test successful")

    def test_integration_with_real_config(self):
        """Test integration with realistic configuration"""
        print("\n🧪 Testing Integration with Real Configuration...")

        # Create realistic OOS configuration
        config_content = {
            "debug": True,
            "workspace_root": "/workspace/projects",
            "commands_dir": str(self.commands_dir.parent),
            "optimization": {
                "enabled": True,
                "aggressive_mode": False
            }
        }

        config_file = os.path.join(self.temp_dir, "oos_config.json")
        with open(config_file, 'w') as f:
            json.dump(config_content, f, indent=2)

        # Create test commands
        test_cmd_content = """---
description: Test configuration integration
script_path: ./bin/test-config.sh
category: testing
---
Tests configuration loading and integration."""
        (self.commands_dir / "test-config.md").write_text(test_cmd_content)

        # Initialize integration with config
        integration = ClaudeCodeIntegration(config_file)
        integration.command_handler = SimpleCommandHandler(str(self.commands_dir))

        # Verify configuration loaded
        assert integration.config["debug"] is True
        assert integration.config["workspace_root"] == "/workspace/projects"
        assert integration.config["optimization"]["enabled"] is True

        # Test command functionality with loaded config
        commands = integration.list_commands()
        assert len(commands) == 1
        assert commands[0]["name"] == "test-config"

        # Test command execution
        result = integration.execute_command("test-config", "--verbose")
        assert result["command"] == "test-config"
        assert "test-config.sh --verbose" in result["execution"]

        print("✅ Integration with real configuration test successful")

    def test_error_handling_scenarios(self):
        """Test realistic error handling scenarios"""
        print("\n🧪 Testing Error Handling Scenarios...")

        handler = SimpleCommandHandler(str(self.commands_dir))

        # Test 1: Non-existent command
        result = handler.execute_command("non-existent-command")
        assert "error" in result
        assert "not found" in result["error"]

        # Test 2: Get info for non-existent command
        cmd_info = handler.get_command("non-existent")
        assert cmd_info is None

        # Test 3: Integration with non-existent command
        integration = ClaudeCodeIntegration()
        result = integration.execute_command("non-existent")
        assert "error" in result

        # Test 4: Invalid configuration file
        integration = ClaudeCodeIntegration("/nonexistent/config.json")
        # Should use defaults without crashing
        assert integration.config["debug"] is False

        print("✅ Error handling scenarios test successful")

    def test_realistic_command_structure(self):
        """Test with realistic command structures matching actual OOS commands"""
        print("\n🧪 Testing Realistic Command Structure...")

        # Create commands that match the actual OOS slash command structure
        commands_config = [
            {
                "name": "help-me",
                "description": "Get AI-optimized processing for any request",
                "script": "./bin/claude-help-me.sh",
                "category": "optimization",
                "content": "Automatic context optimization and intelligent processing"
            },
            {
                "name": "brain-dump",
                "description": "Transform messy thoughts into clear structure",
                "script": "./bin/claude-brain-dump.sh",
                "category": "optimization",
                "content": "Turns rambling thoughts into organized plans"
            },
            {
                "name": "meta-ai",
                "description": "Generate prompts for external AI assistance",
                "script": "./bin/claude-meta-ai.sh",
                "category": "assistance",
                "content": "Creates structured prompts for external AI"
            },
            {
                "name": "smart-commit",
                "description": "Generate AI-powered commit messages",
                "script": "./bin/claude-smart-commit.sh",
                "category": "development",
                "content": "Automated commit message generation"
            }
        ]

        # Create command files
        for cmd_config in commands_config:
            content = f"""---
description: {cmd_config["description"]}
script_path: {cmd_config["script"]}
category: {cmd_config["category"]}
---

{cmd_config["content"]}
"""
            cmd_file = self.commands_dir / f"{cmd_config['name']}.md"
            cmd_file.write_text(content)

        # Test loading all commands
        handler = SimpleCommandHandler(str(self.commands_dir))
        commands = handler.list_commands()
        assert len(commands) == len(commands_config)

        # Test command categorization
        optimization_commands = [cmd for cmd in commands if cmd.category == "optimization"]
        development_commands = [cmd for cmd in commands if cmd.category == "development"]
        assistance_commands = [cmd for cmd in commands if cmd.category == "assistance"]

        assert len(optimization_commands) == 2
        assert len(development_commands) == 1
        assert len(assistance_commands) == 1

        # Test integration-level functionality
        integration = ClaudeCodeIntegration()
        integration.command_handler = handler

        # Test listing commands through integration
        integration_commands = integration.list_commands()
        assert len(integration_commands) == len(commands_config)

        # Test command execution through integration
        for cmd_name in ["help-me", "brain-dump", "smart-commit"]:
            result = integration.execute_command(cmd_name, "--test")
            assert result["command"] == cmd_name
            assert "error" not in result

        print("✅ Realistic command structure test successful")

    def test_yaml_vs_non_yaml_parsing(self):
        """Test both YAML frontmatter and simple description parsing"""
        print("\n🧪 Testing YAML vs Non-YAML Parsing...")

        # Command with YAML frontmatter
        yaml_cmd_content = """---
description: Command with YAML frontmatter
script_path: ./bin/yaml-cmd.sh
category: testing
---

This command has proper YAML frontmatter with metadata.
"""
        (self.commands_dir / "yaml-cmd.md").write_text(yaml_cmd_content)

        # Command without YAML frontmatter (simple format)
        simple_cmd_content = """Simple command without YAML

This is a simple command description without YAML frontmatter.
It should still parse correctly using fallback logic.
"""
        (self.commands_dir / "simple-cmd.md").write_text(simple_cmd_content)

        handler = SimpleCommandHandler(str(self.commands_dir))

        # Test YAML command
        yaml_cmd = handler.get_command("yaml-cmd")
        assert yaml_cmd is not None
        assert yaml_cmd.description == "Command with YAML frontmatter"
        assert yaml_cmd.script_path == "./bin/yaml-cmd.sh"
        assert yaml_cmd.category == "testing"

        # Test simple command
        simple_cmd = handler.get_command("simple-cmd")
        assert simple_cmd is not None
        assert simple_cmd.description == "Simple command without YAML"  # First line
        assert simple_cmd.script_path == "./bin/claude-simple-cmd.sh"  # Default pattern
        assert simple_cmd.category == "general"  # Default category

        print("✅ YAML vs non-YAML parsing test successful")


    def test_filesystem_isolation(self):
        """Test that different command directories work independently"""
        print("\n🧪 Testing Filesystem Isolation...")

        # Create two separate command directories
        commands_dir1 = Path(self.temp_dir) / "commands1" / ".claude" / "commands"
        commands_dir2 = Path(self.temp_dir) / "commands2" / ".claude" / "commands"
        commands_dir1.mkdir(parents=True, exist_ok=True)
        commands_dir2.mkdir(parents=True, exist_ok=True)

        # Create different commands in each directory
        (commands_dir1 / "cmd1.md").write_text("""---
description: Command from dir 1
script_path: ./bin/cmd1.sh
category: dir1
---
Command 1""")
        (commands_dir2 / "cmd2.md").write_text("""---
description: Command from dir 2
script_path: ./bin/cmd2.sh
category: dir2
---
Command 2""")

        # Test handlers are isolated
        handler1 = SimpleCommandHandler(str(commands_dir1))
        handler2 = SimpleCommandHandler(str(commands_dir2))

        # Each handler should only see its own commands
        commands1 = handler1.list_commands()
        commands2 = handler2.list_commands()

        assert len(commands1) == 1
        assert len(commands2) == 1
        assert commands1[0].name == "cmd1"
        assert commands2[0].name == "cmd2"
        assert commands1[0].category == "dir1"
        assert commands2[0].category == "dir2"

        # Cross-verification
        assert handler1.get_command("cmd2") is None
        assert handler2.get_command("cmd1") is None

        print("✅ Filesystem isolation test successful")



if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])