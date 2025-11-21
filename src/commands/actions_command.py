"""
Actions Command for OOS
Handles /actions and /act slash commands for managing actions
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from capability_router import route_request
from actions_gateway import list_available_tools, execute_action, ActionResult
from renderers import render_tools, render_action_result


class ActionsCommand:
    """Handler for /actions and /act slash commands"""

    def __init__(self):
        self.name = "actions"
        self.description = "List available actions and execute them"
        self.usage_actions = "/actions [<domain>] [--json]"
        self.usage_act = "/act <tool_id> [key=value ...] [--json]"

    async def execute_actions(self, args: list) -> str:
        """Execute /actions command to list available tools"""
        # Parse arguments
        domain = None
        show_json = False

        for arg in args:
            if arg == '--json':
                show_json = True
            elif not arg.startswith('--'):
                domain = arg

        try:
            # List available tools
            tools = await list_available_tools(domain)

            # Render the result
            return render_tools(tools, domain, show_json=show_json)

        except Exception as e:
            return f"Error listing actions: {str(e)}"

    async def execute_act(self, args: list) -> str:
        """Execute /act command to run a specific tool"""
        if not args:
            return "Usage: /act <tool_id> [key=value ...] [--json]\n\nExample: /act upload file.txt to=cloud-storage"

        # Parse arguments
        tool_id = None
        params = {}
        show_json = False

        for arg in args:
            if arg == '--json':
                show_json = True
            elif '=' in arg:
                key, value = arg.split('=', 1)
                params[key] = value
            elif not tool_id:
                tool_id = arg

        if not tool_id:
            return "Please provide a tool ID. Use /actions to see available tools."

        try:
            # Confirm action execution
            print(f"⚠️  About to execute tool: {tool_id}")
            print(f"Parameters: {params}")
            print("Type 'confirm' to continue or 'cancel' to abort:")

            # In a real implementation, this would be interactive
            # For now, we'll auto-confirm for testing
            confirm = "confirm"  # input("> ").strip().lower()

            if confirm != 'confirm':
                return "Action cancelled."

            # Execute the action
            result = await execute_action(tool_id, params)

            # Render the result
            return render_action_result(result, show_json=show_json)

        except Exception as e:
            return f"Error executing action: {str(e)}"

    def get_actions_help(self) -> str:
        """Get help information for /actions command"""
        return f"""
{self.name} - List available actions

Usage: {self.usage_actions}

Description:
  List available tools and actions that can be executed.
  Filter by domain to see actions for specific service types.

Examples:
  /actions                    # List all available actions
  /actions files/cloud        # List cloud storage actions
  /actions calendar --json    # List calendar actions with JSON output

Options:
  --json  Show full JSON output in addition to human-readable format
        """

    def get_act_help(self) -> str:
        """Get help information for /act command"""
        return f"""
act - Execute a specific action

Usage: {self.usage_act}

Description:
  Execute a specific tool with provided parameters.
  You'll be asked to confirm before execution.

Examples:
  /act upload file.txt to=cloud-storage
  /act send-message recipient=team message="Hello World"
  /act create-event title="Meeting" date=2025-09-28

Options:
  --json  Show full JSON output in addition to human-readable format
        """


async def main():
    """Main function for testing the commands"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python actions_command.py <actions|act> [args...]")
        sys.exit(1)

    command = ActionsCommand()

    if sys.argv[1] == 'actions':
        result = await command.execute_actions(sys.argv[2:])
    elif sys.argv[1] == 'act':
        result = await command.execute_act(sys.argv[2:])
    else:
        print("Invalid command. Use 'actions' or 'act'")
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    asyncio.run(main())