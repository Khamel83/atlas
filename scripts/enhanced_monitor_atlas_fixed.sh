#!/bin/bash
# Enhanced Atlas monitoring and auto-restart service with comprehensive health checks

ATLAS_DIR="/home/ubuntu/dev/atlas"
LOG_FILE="$ATLAS_DIR/logs/monitor.log"
PID_FILE="$ATLAS_DIR/atlas.pid"
MONITORING_PID_FILE="$ATLAS_DIR/monitoring.pid"
ALERT_LOG="$ATLAS_DIR/logs/alerts.log"

cd "$ATLAS_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to log alerts
log_alert() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ALERT: $1" | tee -a "$ALERT_LOG"
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

# Function to check if monitoring is running
check_monitoring() {
    if [ -f "$MONITORING_PID_FILE" ]; then
        PID=$(cat "$MONITORING_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        else
            return 1  # Not running
        fi
    else
        return 1  # Not running
    fi
}

# Function to check Atlas health
check_atlas_health() {
    if ! check_atlas; then
        return 1
    fi

    # Check if process is responsive (not stuck)
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" -o pid,pcpu,pmem,time,cmd | grep -q "python3 atlas_manager.py"; then
        return 0
    else
        return 1
    fi
}

# Function to check monitoring health
check_monitoring_health() {
    if ! check_monitoring; then
        return 1
    fi

    # Check if monitoring service responds
    if curl -s http://localhost:7445/health > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start Atlas
start_atlas() {
    log_message "Starting Atlas Manager..."
    cd "$ATLAS_DIR"
    nohup python3 atlas_manager.py > "$ATLAS_DIR/logs/atlas_output.log" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    sleep 10
    if check_atlas_health; then
        log_message "Atlas Manager started successfully (PID: $PID)"
    else
        log_alert "Failed to start Atlas Manager"
        return 1
    fi
}

# Function to start monitoring
start_monitoring() {
    log_message "Starting Monitoring Service..."
    cd "$ATLAS_DIR"
    nohup python3 monitoring_service.py > "$ATLAS_DIR/logs/monitoring_output.log" 2>&1 &
    PID=$!
    echo $PID > "$MONITORING_PID_FILE"
    sleep 10
    if check_monitoring_health; then
        log_message "Monitoring Service started successfully (PID: $PID)"
    else
        log_alert "Failed to start Monitoring Service"
        return 1
    fi
}

# Function to stop Atlas
stop_atlas() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        log_message "Stopping Atlas Manager (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 5
        kill -9 "$PID" 2>/dev/null || true
        rm -f "$PID_FILE"
        log_message "Atlas Manager stopped"
    fi
}

# Function to stop monitoring
stop_monitoring() {
    if [ -f "$MONITORING_PID_FILE" ]; then
        PID=$(cat "$MONITORING_PID_FILE")
        log_message "Stopping Monitoring Service (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 5
        kill -9 "$PID" 2>/dev/null || true
        rm -f "$MONITORING_PID_FILE"
        log_message "Monitoring Service stopped"
    fi
}

# Function to restart Atlas
restart_atlas() {
    log_message "Restarting Atlas Manager..."
    stop_atlas
    sleep 2
    start_atlas
}

# Function to restart monitoring
restart_monitoring() {
    log_message "Restarting Monitoring Service..."
    stop_monitoring
    sleep 2
    start_monitoring
}

# Function to check system resources
check_system_resources() {
    # Check disk space
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 95 ]; then
        log_alert "Disk space critical: ${DISK_USAGE}% used"
    fi

    # Check memory usage
    MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$MEM_USAGE" -gt 90 ]; then
        log_alert "Memory usage critical: ${MEM_USAGE}% used"
    fi

    # Check CPU usage
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'.' '{print $1}')
    if [ "$CPU_USAGE" -gt 90 ]; then
        log_alert "CPU usage critical: ${CPU_USAGE}% used"
    fi
}

# Function to check Atlas progress
check_atlas_progress() {
    if check_atlas_health; then
        # Check if Atlas is making progress
        LOG_ENTRY=$(tail -1 "$ATLAS_DIR/logs/atlas_output.log")
        LOG_TIME=$(echo "$LOG_ENTRY" | awk '{print $1" "$2}')
        if [ -n "$LOG_TIME" ]; then
            # Convert log time to timestamp
            LOG_TIMESTAMP=$(date -d "$LOG_TIME" +%s 2>/dev/null || echo 0)
            CURRENT_TIMESTAMP=$(date +%s)
            TIME_DIFF=$((CURRENT_TIMESTAMP - LOG_TIMESTAMP))

            # If no new log entries for 2 hours, might be stuck
            if [ "$TIME_DIFF" -gt 7200 ]; then
                log_alert "Atlas Manager may be stuck - no new log entries for 2 hours"
                return 1
            fi
        fi
    fi
    return 0
}

# Main monitoring loop
log_message "Starting enhanced Atlas monitoring service"

while true; do
    # Check system resources
    check_system_resources

    # Check Atlas status
    if check_atlas_health; then
        if check_atlas_progress; then
            log_message "Atlas Manager is running normally"
        else
            log_alert "Atlas Manager appears stuck, restarting..."
            restart_atlas
        fi
    else
        log_alert "Atlas Manager is not running, starting it..."
        start_atlas
    fi

    # Check monitoring status
    if check_monitoring_health; then
        log_message "Monitoring Service is running normally"
    else
        log_alert "Monitoring Service is not running, starting it..."
        start_monitoring
    fi

    # Check queue progress
    if [ -f "$ATLAS_DIR/data/atlas.db" ]; then
        QUEUE_PENDING=$(sqlite3 "$ATLAS_DIR/data/atlas.db" "SELECT COUNT(*) FROM episode_queue WHERE status = 'pending'")
        if [ "$QUEUE_PENDING" -gt 0 ]; then
            log_message "Queue progress: $QUEUE_PENDING episodes pending"
        fi
    fi

    # Sleep for 2 minutes between checks
    sleep 120
done