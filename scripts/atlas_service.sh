#!/bin/bash
#
# Atlas Service Control Script
#
# This script manages the Atlas background service, ensuring that it is
# started and stopped correctly.

# Get the absolute path of the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/atlas_service.pid"
SERVICE_SCRIPT="$PROJECT_ROOT/atlas_service_manager.py"
PYTHON_EXEC="$PROJECT_ROOT/atlas_venv/bin/python3"

# Ensure the logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Function to start the service
start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null; then
            echo "Service is already running (PID: $PID)."
            exit 1
        else
            echo "Stale PID file found. Removing."
            rm "$PID_FILE"
        fi
    fi

    echo "Starting Atlas service..."
    nohup "$PYTHON_EXEC" "$SERVICE_SCRIPT" start --daemon > "$PROJECT_ROOT/logs/atlas_service.log" 2>&1 &
    echo "Service started. Check logs/atlas_service.log for details."
}

# Function to stop the service
stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Service is not running (no PID file)."
        exit 1
    fi

    PID=$(cat "$PID_FILE")
    if ! ps -p $PID > /dev/null; then
        echo "Service is not running (process not found)."
        rm "$PID_FILE"
        exit 1
    fi

    echo "Stopping Atlas service (PID: $PID)..."
    kill $PID
    # Wait for the process to terminate
    while ps -p $PID > /dev/null; do
        sleep 1
    done
    rm "$PID_FILE"
    echo "Service stopped."
}

# Function to check the status of the service
status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null; then
            echo "Service is running (PID: $PID)."
        else
            echo "Service is not running (stale PID file)."
        fi
    else
        echo "Service is not running."
    fi
    echo "---"
    echo "Checking python processes for atlas_background_service.py:"
    pgrep -af "python.*atlas_service_manager.py"

}

# Main command logic
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
esac

exit 0
