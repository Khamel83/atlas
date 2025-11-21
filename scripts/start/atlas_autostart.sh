#!/bin/bash
# Atlas Auto-start Script
# Ensures Atlas processing continues running

echo "🚀 Atlas Auto-start Script - $(date)"
echo "=========================================="

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Environment variables loaded from .env"
else
    echo "❌ .env file not found"
    exit 1
fi

# Check if GitHub token is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN not set"
    exit 1
fi

# Check if Atlas unified is already running
if pgrep -f "atlas_unified.py" > /dev/null; then
    echo "✅ Atlas unified processor is already running"
    exit 0
fi

echo "🎯 Starting Atlas unified processing..."

# Start Atlas unified processor in background
cd /home/ubuntu/dev/atlas
nohup python3 src/atlas_unified.py > atlas_unified_output.log 2>&1 &
echo $! > atlas_unified.pid

echo "✅ Atlas unified started with PID: $(cat atlas_unified.pid)"
echo "📊 Monitoring logs: tail -f atlas_unified_output.log"
echo "🔍 Check status: python3 telegram_command.py status"