#!/bin/bash
# Bridge to OOS command system from parent project
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
OOS_DIR="$PARENT_DIR/oos"

if [ ! -d "$OOS_DIR" ]; then
    echo "❌ OOS directory not found at $OOS_DIR"
    exit 1
fi

# Forward to OOS command system
cd "$OOS_DIR"
if [ -f "src/simple_command_handler.py" ]; then
    python3 -c "
import sys
sys.path.insert(0, 'src')
from simple_command_handler import SimpleCommandHandler
import asyncio

async def run_command():
    handler = SimpleCommandHandler()
    args = sys.argv[1:] if len(sys.argv) > 1 else ['help']
    command = args[0] if args else 'help'
    params = args[1:] if len(args) > 1 else []

    result = await handler.execute_command(command, ' '.join(params))
    print(result['output'])

asyncio.run(run_command())
" "$@"
else
    echo "❌ OOS command system not found"
    exit 1
fi
