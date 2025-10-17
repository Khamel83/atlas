"""
Capabilities Command for OOS
Handles /capabilities slash command for getting capability information
"""

import asyncio
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from capability_router import route_request
from knowledge_resolver import resolve_knowledge
from renderers import render_knowledge


class CapabilitiesCommand:
    """Handler for /capabilities slash command"""

    def __init__(self):
        self.name = "capabilities"
        self.description = "Get capability information about services and tools"
        self.usage = "/capabilities <query> [--json]"

    async def execute(self, args: list) -> str:
        """
        Execute the capabilities command
        Args: list of command line arguments
        """
        if not args:
            return "Usage: /capabilities <query> [--json]\n\nExample: /capabilities \"What does ChatGPT Plus offer?\""

        # Parse arguments
        query = []
        show_json = False

        for arg in args:
            if arg == '--json':
                show_json = True
            else:
                query.append(arg)

        query_text = ' '.join(query)
        if not query_text:
            return "Please provide a query. Example: /capabilities \"What does ChatGPT Plus offer?\""

        try:
            # Route the request
            routing_result = route_request(query_text)

            # Resolve knowledge
            knowledge_result = await resolve_knowledge(query_text, routing_result.domain)

            # Add domain to result for rendering
            knowledge_result.domain = routing_result.domain

            # Render the result
            return render_knowledge(knowledge_result, show_json=show_json)

        except Exception as e:
            return f"Error resolving capabilities: {str(e)}"

    def get_help(self) -> str:
        """Get help information for this command"""
        return f"""
{self.name} - {self.description}

Usage: {self.usage}

Description:
  Get detailed information about what services can do, including:
  • Available capabilities and features
  • API access and authentication methods
  • Usage limits and quotas
  • Pricing information
  • Current documentation with sources

Examples:
  /capabilities "What does ChatGPT Plus offer?"
  /capabilities "Google Drive API limits"
  /capabilities "AWS S3 pricing" --json

Options:
  --json  Show full JSON output in addition to human-readable format
        """


async def main():
    """Main function for testing the command"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python capabilities_command.py <query> [--json]")
        sys.exit(1)

    command = CapabilitiesCommand()
    result = await command.execute(sys.argv[1:])
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
