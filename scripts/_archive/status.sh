#!/usr/bin/env bash
# ONE_SHOT Standard: status.sh
# Check Atlas system status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Use existing status script if available
if [ -f "atlas_status.sh" ]; then
    ./atlas_status.sh
    exit 0
fi

# Fallback: basic status check
echo "=========================================="
echo "  Atlas Status"
echo "=========================================="
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# Process status
echo "PROCESS STATUS:"
if pgrep -f "atlas_manager.py" > /dev/null 2>&1; then
    PID=$(pgrep -f "atlas_manager.py")
    UPTIME=$(ps -o etime= -p "$PID" 2>/dev/null | tr -d ' ')
    echo "  Atlas Processor: RUNNING (PID: $PID, Uptime: $UPTIME)"
else
    echo "  Atlas Processor: STOPPED"
fi

if pgrep -f "uvicorn.*api" > /dev/null 2>&1; then
    PID=$(pgrep -f "uvicorn.*api")
    echo "  Atlas API: RUNNING (PID: $PID)"
else
    echo "  Atlas API: STOPPED"
fi
echo ""

# Database status
echo "DATABASE STATUS:"
DB_PATH=""
if [ -f "podcast_processing.db" ]; then
    DB_PATH="podcast_processing.db"
elif [ -f "data/databases/podcast_processing.db" ]; then
    DB_PATH="data/databases/podcast_processing.db"
fi

if [ -n "$DB_PATH" ]; then
    EPISODE_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM episodes" 2>/dev/null || echo "?")
    TRANSCRIPT_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM episodes WHERE transcript_status='found'" 2>/dev/null || echo "?")
    echo "  Database: $DB_PATH"
    echo "  Episodes: $EPISODE_COUNT"
    echo "  Transcripts: $TRANSCRIPT_COUNT"
else
    echo "  Database: NOT FOUND"
fi
echo ""

# API health check
echo "API HEALTH:"
if curl -s --max-time 2 http://localhost:7444/health > /dev/null 2>&1; then
    echo "  http://localhost:7444/health - OK"
else
    echo "  http://localhost:7444/health - UNAVAILABLE"
fi
echo ""

echo "=========================================="
echo "Commands:"
echo "  Start:  ./scripts/start.sh"
echo "  Stop:   ./scripts/stop.sh"
echo "  Logs:   tail -f logs/atlas_manager.log"
echo "=========================================="
