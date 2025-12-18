#!/bin/bash
# Downie Diagnostic Script
# Run this on Mac Mini to find all Downie-related files and logs

echo "🔍 DOWNIE DIAGNOSTIC SCRIPT"
echo "=========================="

# Find all Downie-related directories
echo "📁 Searching for Downie directories..."
find ~ -name "*downie*" -type d 2>/dev/null | head -10

echo ""
echo "📄 Searching for Downie log files..."
find ~ -name "*downie*" -type f 2>/dev/null | grep -i log | head -10

echo ""
echo "📄 Searching for any Downie files..."
find ~ -name "*downie*" -type f 2>/dev/null | head -20

echo ""
echo "🍎 Checking Application Support..."
ls -la "$HOME/Library/Application Support/" | grep -i downie

echo ""
echo "📊 Checking Logs directory..."
ls -la "$HOME/Library/Logs/" | grep -i downie

echo ""
echo "📦 Checking Containers..."
ls -la "$HOME/Library/Containers/" | grep -i downie

echo ""
echo "🔧 Checking Preferences..."
ls -la "$HOME/Library/Preferences/" | grep -i downie

echo ""
echo "💾 Checking if Downie is running..."
ps aux | grep -i downie

echo ""
echo "🎯 If you see any log files above, check their contents with:"
echo "   tail -f [log_file_path]"
echo ""
echo "💡 Try triggering a Downie failure, then immediately run:"
echo "   find ~ -name '*.log' -newer /tmp/timestamp 2>/dev/null"
echo "   (after creating: touch /tmp/timestamp)"