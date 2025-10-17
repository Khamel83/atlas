#!/bin/bash
# Simple OOS Integration - Just copy the working files out
# 5 lines that actually work instead of 500 lines of overcomplicated BS

set -e

echo "🔧 Simple OOS Integration - Copy files out and be done"

# Step 1: Update OOS folder (if we're in parent project)
PARENT_DIR="$(dirname "$(pwd)")"
if [ "$(basename "$(pwd)")" = "oos" ] && [ -d "$PARENT_DIR/.git" ]; then
    echo "📁 In OOS subdirectory - updating and copying out..."

    # Update OOS
    git pull origin master

    # Copy slash commands out of OOS to parent
    mkdir -p "../.claude"
    cp .claude/slash_commands.json ../.claude/

    # Copy scripts out of OOS to parent
    mkdir -p "../bin"
    cp bin/claude-*.sh ../bin/ 2>/dev/null || true

    # Make scripts executable
    chmod +x ../bin/claude-*.sh 2>/dev/null || true

    echo "✅ Done! /consultant should work after Claude Code restart"

else
    echo "ℹ️  Not in OOS subdirectory - nothing to copy out"
fi