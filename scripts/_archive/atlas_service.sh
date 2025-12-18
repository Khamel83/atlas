#!/bin/bash
# Atlas Service Manager
# Ensures Atlas runs 100% of the time with auto-restart
# Usage: ./atlas_service.sh {start|stop|status|restart}

ATLAS_DIR="/home/ubuntu/dev/atlas"
ATLAS_SCRIPT="atlas_v3_dual_ingestion.py"
ATLAS_PORT="8001"
PID_FILE="$ATLAS_DIR/.atlas.pid"
LOG_FILE="$ATLAS_DIR/atlas_service.log"

start_atlas() {
    cd "$ATLAS_DIR"

    # Check if already running
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "✅ Atlas is already running (PID: $(cat $PID_FILE))"
        return 0
    fi

    echo "🚀 Starting Atlas on port $ATLAS_PORT..."

    # Start Atlas with proper logging
    nohup python3 "$ATLAS_SCRIPT" > "$LOG_FILE" 2>&1 &
    ATLAS_PID=$!

    # Save PID
    echo "$ATLAS_PID" > "$PID_FILE"

    # Wait for startup
    sleep 3

    # Verify it's running
    if kill -0 "$ATLAS_PID" 2>/dev/null; then
        echo "✅ Atlas started successfully (PID: $ATLAS_PID)"
        echo "🌐 Local: http://localhost:$ATLAS_PORT"
        echo "🔍 Check: curl http://localhost:$ATLAS_PORT/status"
    else
        echo "❌ Atlas failed to start"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_atlas() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "🛑 Stopping Atlas (PID: $PID)..."
            kill "$PID"

            # Wait for graceful shutdown
            sleep 2

            # Force kill if still running
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID"
            fi

            echo "✅ Atlas stopped"
        else
            echo "⚠️  Atlas was not running"
        fi
        rm -f "$PID_FILE"
    else
        echo "⚠️  No PID file found"
    fi

    # Kill any remaining Atlas processes
    pkill -f "$ATLAS_SCRIPT" 2>/dev/null
}

status_atlas() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        PID=$(cat "$PID_FILE")
        echo "✅ Atlas is running (PID: $PID)"
        echo "🌐 http://localhost:$ATLAS_PORT"

        # Test the service
        response=$(curl -s "http://localhost:$ATLAS_PORT/status" 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "🔍 Service responding: $response"
        else
            echo "⚠️  Service not responding"
        fi
    else
        echo "❌ Atlas is not running"
    fi
}

restart_atlas() {
    echo "🔄 Restarting Atlas..."
    stop_atlas
    sleep 1
    start_atlas
}

# Auto-restart monitor (runs in background)
monitor_atlas() {
    echo "👁️  Starting Atlas monitor (auto-restart)..."
    while true; do
        if ! [ -f "$PID_FILE" ] || ! kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "⚠️  Atlas died, restarting..."
            start_atlas
        fi
        sleep 30  # Check every 30 seconds
    done
}

case "$1" in
    start)
        start_atlas
        ;;
    stop)
        stop_atlas
        ;;
    status)
        status_atlas
        ;;
    restart)
        restart_atlas
        ;;
    monitor)
        monitor_atlas
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart|monitor}"
        echo ""
        echo "Examples:"
        echo "  $0 start      # Start Atlas"
        echo "  $0 monitor   # Start auto-restart monitor"
        echo "  $0 status    # Check status"
        exit 1
        ;;
esac