#!/usr/bin/env python3
"""
Simple Command Handler for OOS

Provides basic command handling functionality for slash commands.
This is a simplified version that replaces the overly complex command_generator.py.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class CommandInfo:
    """Simple command information"""
    name: str
    description: str
    script_path: str
    category: str


class SimpleCommandHandler:
    """Simple command handler for OOS slash commands"""

    def __init__(self, commands_dir: str = None):
        self.commands_dir = Path(commands_dir or ".claude/commands")
        self.commands = self._load_commands()

    def _load_commands(self) -> Dict[str, CommandInfo]:
        """Load command definitions from markdown files"""
        commands = {}

        if not self.commands_dir.exists():
            return commands

        for cmd_file in self.commands_dir.glob("*.md"):
            cmd_name = cmd_file.stem
            commands[cmd_name] = self._parse_command_file(cmd_file)

        return commands

    def _parse_command_file(self, cmd_file: Path) -> CommandInfo:
        """Parse a command markdown file"""
        content = cmd_file.read_text()

        # Extract YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                description = parts[2].strip()

                # Parse frontmatter
                import yaml
                try:
                    metadata = yaml.safe_load(frontmatter) or {}
                    return CommandInfo(
                        name=cmd_file.stem,
                        description=metadata.get('description', description.split('\n')[0]),
                        script_path=metadata.get('script_path', f'./bin/claude-{cmd_file.stem}.sh'),
                        category=metadata.get('category', 'general')
                    )
                except:
                    pass

        # Fallback
        return CommandInfo(
            name=cmd_file.stem,
            description=content.split('\n')[0] if content else cmd_file.stem,
            script_path=f'./bin/claude-{cmd_file.stem}.sh',
            category='general'
        )

    def get_command(self, name: str) -> Optional[CommandInfo]:
        """Get a command by name"""
        return self.commands.get(name)

    def list_commands(self) -> List[CommandInfo]:
        """List all available commands"""
        return list(self.commands.values())

    def execute_command(self, name: str, args: str = "") -> Dict[str, Any]:
        """Execute a command (returns info about how to execute it)"""
        cmd = self.get_command(name)
        if not cmd:
            return {"error": f"Command '{name}' not found"}

        return {
            "command": cmd.name,
            "description": cmd.description,
            "script": cmd.script_path,
            "execution": f"{cmd.script_path} {args}" if args else cmd.script_path,
            "category": cmd.category
        }


if __name__ == "__main__":
    # Test the command handler
    handler = SimpleCommandHandler()
    print("Available commands:")
    for cmd in handler.list_commands():
        print(f"  {cmd.name}: {cmd.description}")