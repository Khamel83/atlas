#!/bin/bash
# Simple Atlas monitoring and auto-restart script

ATLAS_DIR="/home/ubuntu/dev/atlas"
LOG_FILE="$ATLAS_DIR/logs/monitor.log"
PID_FILE="$ATLAS_DIR/atlas.pid"

cd "$ATLAS_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if Atlas is running
check_atlas() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        else
            return 1  # Not running
        fi
    else
        return 1  # Not running
    fi
}

# Function to start Atlas
start_atlas() {
    log_message "Starting Atlas Manager..."
    nohup python3 atlas_manager.py > "$ATLAS_DIR/logs/atlas_output.log" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 5
    if check_atlas; then
        log_message "Atlas Manager started successfully (PID: $!)"
    else
        log_message "Failed to start Atlas Manager"
    fi
}

# Function to stop Atlas
stop_atlas() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        log_message "Stopping Atlas Manager (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 2
        kill -9 "$PID" 2>/dev/null || true
        rm -f "$PID_FILE"
        log_message "Atlas Manager stopped"
    fi
}

# Main monitoring loop
log_message "Starting Atlas monitoring service"

while true; do
    if check_atlas; then
        # Atlas is running, check if it's responsive
        log_message "Atlas is running normally"
    else
        log_message "Atlas is not running, starting it..."
        start_atlas
    fi

    # Sleep for 5 minutes
    sleep 300
done