#!/bin/bash
"""
Cleanup old JSON-based slash commands configuration
"""

echo "Cleaning up old JSON slash commands configuration..."

# Remove old JSON files
if [[ -f ".claude/slash_commands.json" ]]; then
    echo "Removing .claude/slash_commands.json"
    rm .claude/slash_commands.json
fi

if [[ -f ".claude/slash-commands.json" ]]; then
    echo "Removing .claude/slash-commands.json"
    rm .claude/slash-commands.json
fi

echo "Old slash commands configuration cleaned up."
echo "Claude Code now uses markdown files in .claude/commands/"