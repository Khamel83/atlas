#!/usr/bin/env bash
# ONE_SHOT Standard: stop.sh
# Stop Atlas processor

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Stopping Atlas..."

# Find and stop processor
if pgrep -f "atlas_manager.py" > /dev/null 2>&1; then
    PID=$(pgrep -f "atlas_manager.py")
    echo "Stopping Atlas processor (PID: $PID)..."

    # Graceful shutdown first
    kill -TERM "$PID" 2>/dev/null || true

    # Wait up to 10 seconds for graceful shutdown
    for i in {1..10}; do
        if ! pgrep -f "atlas_manager.py" > /dev/null 2>&1; then
            echo "Atlas stopped gracefully."
            exit 0
        fi
        sleep 1
    done

    # Force kill if still running
    if pgrep -f "atlas_manager.py" > /dev/null 2>&1; then
        echo "Force stopping..."
        pkill -9 -f "atlas_manager.py" 2>/dev/null || true
        echo "Atlas force stopped."
    fi
else
    echo "Atlas is not running."
fi

# Also stop API if running
if pgrep -f "uvicorn.*api" > /dev/null 2>&1; then
    echo "Stopping Atlas API..."
    pkill -f "uvicorn.*api" 2>/dev/null || true
    echo "API stopped."
fi

echo "Done."
