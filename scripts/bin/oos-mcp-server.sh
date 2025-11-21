#!/bin/bash
# OOS MCP Server Launcher
# Activates virtual environment and starts the MCP server

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"

# Activate the virtual environment
source "$SCRIPT_DIR/oos-env/bin/activate"

# Set Python path to include src
export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"

# Start the MCP server
echo "Starting OOS MCP Server..."
echo "Available slash commands:"
echo "  /help-me - AI-optimized processing"
echo "  /brain-dump - Turn messy thoughts into structure"
echo "  /meta-ai - Generate prompts for external AI"
echo "  /smart-commit - AI-powered commit messages"
echo "  /optimize - Token optimization"
echo "  /clarify - Clarification workflow"
echo "  /context-stats - Context statistics"
echo "  /doc-check - Documentation consistency"
echo "  /auto-fix - Automatic code fixes"
echo "  /workflow - Structured workflows"
echo ""
python3 "$SCRIPT_DIR/mcp_server.py" "$@"