#!/bin/bash

# Claude Code slash command bridge to OOS command system
# This connects Claude's /command slash command to OOS's internal command system

set -e

# Get the OOS project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OOS_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to OOS root directory
cd "$OOS_ROOT"

# Check if we have arguments
if [ $# -eq 0 ]; then
    echo "📋 OOS Command System Help"
    echo "========================="
    echo ""
    echo "Usage: /command <command_name> [args...]"
    echo ""
    echo "Available OOS commands:"
    echo "  capabilities <query>  - Get capability information"
    echo "  actions [domain]      - List available actions"
    echo "  act <tool> <params>   - Execute specific action"
    echo "  consultant [args]     - Strategic consultant interface"
    echo ""
    echo "Examples:"
    echo "  /command capabilities python"
    echo "  /command actions development"
    echo "  /command act create-module user-auth"
    echo "  /command consultant analyze-architecture"
    echo ""
    echo "For more details, run: /command capability-help"
    exit 0
fi

# Extract command name and arguments
COMMAND_NAME="$1"
shift
COMMAND_ARGS="$*"

# Execute the OOS command via Python
python3 -c "
import sys
import asyncio
sys.path.insert(0, 'src')
from simple_command_handler import SimpleCommandHandler

async def main():
    handler = SimpleCommandHandler()
    result = await handler.execute_command('$COMMAND_NAME', '$COMMAND_ARGS')

    if 'error' in result:
        print(f'❌ Error: {result[\"error\"]}', file=sys.stderr)
        sys.exit(1)
    elif 'output' in result:
        print(result['output'])
    else:
        # Traditional command result
        print(f'🔧 Command: {result.get(\"command\", \"$COMMAND_NAME\")}')
        print(f'📝 Description: {result.get(\"description\", \"No description\")}')
        if 'execution' in result:
            print(f'▶️  Execution: {result[\"execution\"]}')
            print('')
            print('To run this command:')
            print(f'  {result[\"execution\"]}')

asyncio.run(main())
"