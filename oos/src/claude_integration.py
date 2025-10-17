#!/usr/bin/env python3
"""
Simple Claude Code Integration for OOS

Provides basic integration functionality for OOS slash commands.
This replaces the overly complex version with a simple implementation.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from simple_command_handler import SimpleCommandHandler


class ClaudeCodeIntegration:
    """Simple integration for Claude Code slash commands"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.command_handler = SimpleCommandHandler()

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            "debug": False,
            "workspace_root": os.getcwd()
        }

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception:
                pass  # Use defaults

        return default_config

    def list_commands(self) -> List[Dict[str, Any]]:
        """List all available commands"""
        commands = []
        for cmd in self.command_handler.list_commands():
            commands.append({
                "name": cmd.name,
                "description": cmd.description,
                "category": cmd.category
            })
        return commands

    def execute_command(self, command_name: str, args: str = "") -> Dict[str, Any]:
        """Execute a command by name"""
        return self.command_handler.execute_command(command_name, args)

    def get_command_info(self, command_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific command"""
        cmd = self.command_handler.get_command(command_name)
        if not cmd:
            return None

        return {
            "name": cmd.name,
            "description": cmd.description,
            "script": cmd.script_path,
            "category": cmd.category
        }


if __name__ == "__main__":
    # Test the integration
    integration = ClaudeCodeIntegration()
    print("Available commands:")
    for cmd in integration.list_commands():
        print(f"  {cmd['name']}: {cmd['description']}")