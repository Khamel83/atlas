#!/usr/bin/env python3
"""
Simple Command Handler for OOS

Provides basic command handling functionality for slash commands.
This is a simplified version that replaces the overly complex command_generator.py.
"""

import json
import os
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from commands.capabilities_command import CapabilitiesCommand
from commands.actions_command import ActionsCommand
from renderers import render_help


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

        # Initialize capability commands
        self.capabilities_cmd = CapabilitiesCommand()
        self.actions_cmd = ActionsCommand()

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

    async def execute_command(self, name: str, args: str = "") -> Dict[str, Any]:
        """Execute a command (returns info about how to execute it)"""

        # Handle built-in capability commands
        if name == "capabilities":
            return await self._execute_capabilities(args)
        elif name == "actions":
            return await self._execute_actions(args)
        elif name == "act":
            return await self._execute_act(args)
        elif name == "capability-help":
            return {"output": render_help()}

        # Handle traditional file-based commands
        cmd = self.get_command(name)
        if not cmd:
            return {"error": f"Command '{name}' not found. Use /capability-help to see available capability commands."}

        return {
            "command": cmd.name,
            "description": cmd.description,
            "script": cmd.script_path,
            "execution": f"{cmd.script_path} {args}" if args else cmd.script_path,
            "category": cmd.category
        }

    async def _execute_capabilities(self, args: str) -> Dict[str, Any]:
        """Execute capabilities command"""
        try:
            # Parse args
            arg_list = args.split() if args else []
            result = await self.capabilities_cmd.execute(arg_list)
            return {"output": result}
        except Exception as e:
            return {"error": f"Error executing capabilities command: {str(e)}"}

    async def _execute_actions(self, args: str) -> Dict[str, Any]:
        """Execute actions command"""
        try:
            # Parse args
            arg_list = args.split() if args else []
            result = await self.actions_cmd.execute_actions(arg_list)
            return {"output": result}
        except Exception as e:
            return {"error": f"Error executing actions command: {str(e)}"}

    async def _execute_act(self, args: str) -> Dict[str, Any]:
        """Execute act command"""
        try:
            # Parse args
            arg_list = args.split() if args else []
            result = await self.actions_cmd.execute_act(arg_list)
            return {"output": result}
        except Exception as e:
            return {"error": f"Error executing act command: {str(e)}"}


# For backward compatibility
def execute_command(name: str, args: str = "") -> Dict[str, Any]:
    """Synchronous wrapper for execute_command"""
    handler = SimpleCommandHandler()
    return asyncio.run(handler.execute_command(name, args))


if __name__ == "__main__":
    # Test the command handler
    async def test_handler():
        handler = SimpleCommandHandler()

        print("Built-in capability commands:")
        print("  /capabilities <query> - Get capability information")
        print("  /actions [domain] - List available actions")
        print("  /act <tool> <params> - Execute specific action")
        print("  /capability-help - Show help for capability commands")

        print("\nTraditional commands:")
        for cmd in handler.list_commands():
            print(f"  /{cmd.name}: {cmd.description}")

    asyncio.run(test_handler())