#!/bin/bash
# Script to start the Atlas monitoring service

ATLAS_DIR="/home/ubuntu/dev/atlas"
LOG_FILE="$ATLAS_DIR/logs/monitoring_service.log"
PID_FILE="$ATLAS_DIR/monitoring.pid"

cd "$ATLAS_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if monitoring service is running
check_monitoring() {
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

# Function to start monitoring service
start_monitoring() {
    log_message "Starting Atlas Monitoring Service..."
    nohup python3 monitoring_service.py > "$ATLAS_DIR/logs/monitoring_output.log" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 5
    if check_monitoring; then
        log_message "Atlas Monitoring Service started successfully (PID: $!)"
        log_message "Dashboard available at: http://localhost:7445/monitoring/"
    else
        log_message "Failed to start Atlas Monitoring Service"
    fi
}

# Function to stop monitoring service
stop_monitoring() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        log_message "Stopping Atlas Monitoring Service (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 2
        kill -9 "$PID" 2>/dev/null || true
        rm -f "$PID_FILE"
        log_message "Atlas Monitoring Service stopped"
    fi
}

# Main logic
case "$1" in
    start)
        if check_monitoring; then
            log_message "Atlas Monitoring Service is already running"
        else
            start_monitoring
        fi
        ;;
    stop)
        stop_monitoring
        ;;
    restart)
        stop_monitoring
        sleep 2
        start_monitoring
        ;;
    status)
        if check_monitoring; then
            PID=$(cat "$PID_FILE")
            log_message "Atlas Monitoring Service is running (PID: $PID)"
        else
            log_message "Atlas Monitoring Service is not running"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
