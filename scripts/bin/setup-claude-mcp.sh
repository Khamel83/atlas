#!/bin/bash
# Setup OOS MCP Server for Claude Code

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Setting up OOS MCP Server for Claude Code..."
echo ""

# Check if Claude Code CLI is available
if ! command -v claude &> /dev/null; then
    echo "❌ Claude Code CLI not found. Please install it first."
    echo "   Visit: https://docs.anthropic.com/en/docs/claude-code/getting-started"
    exit 1
fi

echo "✅ Claude Code CLI found"

# Add OOS MCP server to Claude Code
echo "📡 Adding OOS MCP server to Claude Code..."
claude mcp add-json oos "$(cat << 'EOF'
{
  "type": "stdio",
  "command": "$SCRIPT_DIR/bin/oos-mcp-server.sh",
  "args": []
}
EOF
)" 2>/dev/null || {
    echo "ℹ️  Trying alternative method..."
    claude mcp add oos stdio "$SCRIPT_DIR/bin/oos-mcp-server.sh"
}

echo ""
echo "✅ OOS MCP Server added to Claude Code!"
echo ""
echo "🎯 Now you can use OOS slash commands directly in Claude Code:"
echo "   /help-me - AI-optimized processing"
echo "   /brain-dump - Turn messy thoughts into structure"
echo "   /meta-ai - Generate prompts for external AI"
echo "   /smart-commit - AI-powered commit messages"
echo "   /optimize - Token optimization"
echo "   /clarify - Clarification workflow"
echo "   /context-stats - Context statistics"
echo "   /doc-check - Documentation consistency"
echo "   /auto-fix - Automatic code fixes"
echo "   /workflow - Structured workflows"
echo ""
echo "📋 To verify: claude mcp list"
echo "🔄 To remove: claude mcp remove oos"
echo ""
echo "🚀 Start a new Claude Code session and try: /help-me test request"