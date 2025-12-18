#!/usr/bin/env bash
# ONE_SHOT Standard: start.sh
# Start Atlas processor

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Starting Atlas..."

# Check if already running
if pgrep -f "atlas_manager.py" > /dev/null 2>&1; then
    PID=$(pgrep -f "atlas_manager.py")
    echo "Atlas is already running (PID: $PID)"
    echo "Use ./scripts/status.sh to check status"
    echo "Use ./scripts/stop.sh to stop first"
    exit 0
fi

# Check for venv
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run ./scripts/setup.sh first."
    exit 1
fi

# Source environment if exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Start processor
echo "Starting Atlas processor..."
nohup ./venv/bin/python processors/atlas_manager.py > logs/atlas_manager.log 2>&1 &

sleep 2

if pgrep -f "atlas_manager.py" > /dev/null 2>&1; then
    PID=$(pgrep -f "atlas_manager.py")
    echo "Atlas started successfully (PID: $PID)"
    echo ""
    echo "Logs: tail -f logs/atlas_manager.log"
    echo "Status: ./scripts/status.sh"
    echo "Stop: ./scripts/stop.sh"
else
    echo "ERROR: Atlas failed to start"
    echo "Check logs: tail -50 logs/atlas_manager.log"
    exit 1
fi
